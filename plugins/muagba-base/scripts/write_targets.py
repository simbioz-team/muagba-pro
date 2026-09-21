#!/usr/bin/env python3
"""Во что команда пишет: печатает пути-кандидаты, по одному на строку.

Нужен `guard-bash.sh`, чтобы запрет на правку защищённого файла нельзя было
обойти через оболочку. `protect-paths.sh` смотрит на инструменты правки, и
`cat > docs/constitution.md` мимо него проходит.

**Границы честно.** Это не песочница и не полный разбор shell. Ловятся
очевидные формы записи, которыми обходят запрет не думая: перенаправление,
tee, sed -i, cp/mv, dd of=, truncate, а также запись из `python3 -c` и
heredoc'а — на Python-проекте это не хитрость, а основная идиома правки
файла. Подстановка переменной (`f=docs/constitution.md; echo x > $f`) и
запись из другого языка проходят: полный разбор произвольной оболочки
средствами регулярных выражений — обещание, которое нельзя сдержать.

Относительные цели достраиваются от `cd`, пройденного в той же команде:
без этого `cd <проект> && echo x >> uv.lock` обходил запрет, хотя тот же
файл абсолютным путём блокировался.
"""

from __future__ import annotations

import os
import re
import shlex
import sys

REDIRECTS = {">", ">>", "1>", "2>", "&>", ">|"}
# Перенаправления ввода тоже съедают следующий токен: без этого `tee .env
# < /dev/null` отдавал в цели и `<`, и `/dev/null`.
INPUTS = {"<", "<<", "<<<", "0<"}
LAST_ARG_CMDS = {"cp", "mv", "install", "rsync"}

# Запуск интерпретатора: сам по себе или через обёртку. Обёртки перечислены
# поимённо, а не «любой токен», иначе `echo python3` снова блокировался бы
# за упоминание — ту же ошибку уже чинили в cmd_danger.py.
PY_EXE = re.compile(r"^(python|python[23](\.\d+)?|py)$")
PY_WRAPPERS = {"uv", "uvx", "poetry", "pipenv", "env", "nohup", "time", "sudo"}

# Запись из Python. Кавычки необязательны: shlex в posix-режиме их снимает,
# и до нас `open('x','w')` доезжает как `open(x,w)`.
Q = r"""["']?"""
PY_OPEN = re.compile(rf"""\bopen\s*\(\s*{Q}([^"',)\s]+){Q}\s*,\s*{Q}([rwax+bt]+){Q}""")
PY_PATH = re.compile(
    rf"""\bPath\s*\(\s*{Q}([^"',)\s]+){Q}\s*\)\s*\.\s*"""
    r"""(write_text|write_bytes|unlink|touch|rename|replace)\b""")
PY_OS = re.compile(rf"""\bos\s*\.\s*(remove|unlink)\s*\(\s*{Q}([^"',)\s]+){Q}""")

# Запись, у которой цель — не литерал: `p.write_text(...)`, где `p` собрано в
# цикле. Разобрать такое статически нельзя и никогда будет нельзя: это не
# пробел в регулярке, а предел подхода. Поэтому вместо пути выдаётся маркер, а
# решение принимает вызывающая сторона — она знает список защищённых путей и
# проверит их по тексту самой команды.
#
# Дыру нашли на себе: правка защищённого docs/workflow.md через heredoc, где
# путь собирался как Path(name)/"docs"/"workflow.md", прошла мимо хука.
UNRESOLVED = "?"
PY_WRITE_ANY = re.compile(
    r"""\.\s*(write_text|write_bytes|writelines|touch|unlink|rename|replace)\s*\("""
    r"""|\bopen\s*\([^)]*,\s*["']?[wax]"""
    r"""|\bos\s*\.\s*(replace|rename|remove|unlink|makedirs)\s*\("""
    r"""|\bshutil\s*\.\s*(copy\w*|move|rmtree)\s*\(""")


def segments(command: str) -> list[list[str]]:
    """Команда разбивается на простые по ; && || |."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    out, cur = [], []
    for t in tokens:
        if t in (";", "&&", "||", "|", "&"):
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        out.append(cur)
    return out


def argv_of(parts: list[str]) -> list[str]:
    """Токены без перенаправлений: собственно команда и её аргументы."""
    argv, skip = [], False
    for tok in parts:
        if skip:
            skip = False
            continue
        if tok in REDIRECTS or tok in INPUTS:
            skip = True
            continue
        if tok.startswith((">", "<")) or tok in ("2>&1", "&>>"):
            continue
        argv.append(tok)
    return argv


def python_targets(argv: list[str]) -> list[str]:
    """Пути, в которые пишет код Python, переданный через -c или heredoc.

    Тело heredoc'а доезжает сюда отдельными токенами: `<<` съедает только
    метку, остальное остаётся в argv. Поэтому склеиваем и ищем по тексту —
    но лишь в сегменте, который и правда запускает интерпретатор.
    """
    head = argv[0].rsplit("/", 1)[-1]
    if not PY_EXE.match(head):
        if head not in PY_WRAPPERS:
            return []
        if not any(PY_EXE.match(a.rsplit("/", 1)[-1]) for a in argv[1:]):
            return []
    text = " ".join(argv[1:])
    found = [m.group(1) for m in PY_OPEN.finditer(text)
             if set(m.group(2)) & set("wax+")]
    found += [m.group(1) for m in PY_PATH.finditer(text)]
    found += [m.group(2) for m in PY_OS.finditer(text)]
    # Запись есть, а цель могла быть вычислена — пусть вызывающая сторона
    # сверит защищённые пути по тексту команды. Лишний маркер безвреден:
    # если в тексте ни одного защищённого пути нет, он ничего не запретит.
    if PY_WRITE_ANY.search(text):
        found.append(UNRESOLVED)
    return found


def targets(parts: list[str]) -> list[str]:
    if not parts:
        return []
    found: list[str] = []

    # Перенаправления: `> файл`, `cmd >>файл`.
    i = 0
    while i < len(parts):
        tok = parts[i]
        if tok in REDIRECTS:
            if i + 1 < len(parts):
                found.append(parts[i + 1])
            i += 2
            continue
        for r in (">>", ">"):
            if tok.startswith(r) and len(tok) > len(r):
                found.append(tok[len(r):])
                break
        i += 1

    argv = argv_of(parts)
    if not argv:
        return found
    cmd = argv[0].rsplit("/", 1)[-1]
    args = argv[1:]

    found += python_targets(argv)

    if cmd == "tee":
        found += [a for a in args if not a.startswith("-")]
    elif cmd == "sed":
        # -i правит файл на месте; у GNU sed суффикс может прилипнуть: -i.bak
        if any(a == "-i" or a.startswith("-i") and not a.startswith("--") for a in args):
            found += [a for a in args if not a.startswith("-")][1:]  # первый — выражение
    elif cmd == "dd":
        found += [a[3:] for a in args if a.startswith("of=")]
    elif cmd in ("truncate", "touch", "chmod", "chown"):
        found += [a for a in args if not a.startswith("-")]
    elif cmd in LAST_ARG_CMDS:
        plain = [a for a in args if not a.startswith("-")]
        if len(plain) >= 2:
            found.append(plain[-1])
    return found


def main() -> int:
    command = sys.stdin.read()
    seen: list[str] = []
    cwd = ""  # куда увёл `cd`, пройденный раньше в этой же команде
    for parts in segments(command):
        argv = argv_of(parts)
        if argv and argv[0].rsplit("/", 1)[-1] == "cd":
            rest = [a for a in argv[1:] if not a.startswith("-")]
            if len(rest) == 1 and rest[0] != "-":
                cwd = (rest[0] if rest[0].startswith("/")
                       else os.path.normpath(os.path.join(cwd, rest[0])))
            else:
                # `cd` без аргумента уводит домой, `cd -` — в прошлый
                # каталог: откуда именно, отсюда не видно.
                cwd = ""
            continue
        for t in targets(parts):
            # Обрывки перенаправлений (`&`, `1`, `2`) — не пути. Разбор
            # оболочки регулярками неизбежно оставляет такой мусор.
            if t == UNRESOLVED:
                if t not in seen:
                    seen.append(t)
                continue
            if not t or re.fullmatch(r"[&|;<>\d]+", t):
                continue
            if cwd and not t.startswith("/"):
                t = os.path.normpath(os.path.join(cwd, t))
            if t not in seen:
                seen.append(t)
    for t in seen:
        print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
