#!/usr/bin/env python3
"""Во что команда пишет: печатает пути-кандидаты, по одному на строку.

Нужен `guard-bash.sh`, чтобы запрет на правку защищённого файла нельзя было
обойти через оболочку. `protect-paths.sh` смотрит на инструменты правки, и
`cat > docs/constitution.md` мимо него проходит.

**Границы честно.** Это не песочница и не полный разбор shell. Ловятся
очевидные формы записи, которыми обходят запрет не думая: перенаправление,
tee, sed -i, cp/mv, dd of=, truncate. Через `python3 -c` или подстановку
переменной обойти можно, и это осознанно: полный разбор произвольной оболочки
средствами регулярных выражений — обещание, которое нельзя сдержать.
"""

from __future__ import annotations

import re
import shlex
import sys

REDIRECTS = {">", ">>", "1>", "2>", "&>", ">|"}
# Перенаправления ввода тоже съедают следующий токен: без этого `tee .env
# < /dev/null` отдавал в цели и `<`, и `/dev/null`.
INPUTS = {"<", "<<", "<<<", "0<"}
LAST_ARG_CMDS = {"cp", "mv", "install", "rsync"}


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
    if not argv:
        return found
    cmd = argv[0].rsplit("/", 1)[-1]
    args = argv[1:]

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
    seen = []
    for parts in segments(command):
        for t in targets(parts):
            # Обрывки перенаправлений (`&`, `1`, `2`) — не пути. Разбор
            # оболочки регулярками неизбежно оставляет такой мусор.
            if t and not re.fullmatch(r"[&|;<>\d]+", t) and t not in seen:
                seen.append(t)
    for t in seen:
        print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
