#!/usr/bin/env python3
"""Разрушительная команда в строке: печатает причину, если есть.

Раньше это были шаблоны подстроки по всей команде. Они срабатывали на
УПОМИНАНИИ: `echo "не делай git reset --hard"` блокировался наравне с самим
сбросом, а совет в сообщении об ошибке нельзя было даже процитировать.

Здесь команда разбирается на простые и смотрится argv: имя команды и её
аргументы, а не текст целиком.
"""

from __future__ import annotations

import shlex
import sys


def segments(command: str) -> list[list[str]]:
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


def reason(parts: list[str]) -> tuple[str, str] | None:
    if not parts:
        return None
    cmd = parts[0].rsplit("/", 1)[-1]
    args = parts[1:]

    if cmd == "chmod":
        if any(a in ("-R", "--recursive") for a in args) and "777" in args:
            return ("выдача прав 777 рекурсивно", "укажи минимально необходимые права.")
        return None

    if cmd != "git":
        return None
    sub = next((a for a in args if not a.startswith("-")), None)

    if sub == "push":
        # --force-with-lease не затирает чужую работу: он проверяет, что
        # удалённая ветка не двигалась с последнего fetch.
        if any(a.startswith("--force-with-lease") for a in args):
            return None
        if "--force" in args or "-f" in args:
            return ("принудительный пуш",
                    "используй 'git push --force-with-lease' и только после "
                    "согласования с человеком.")
    if sub == "reset" and "--hard" in args:
        return ("жёсткий сброс дерева",
                "сохрани работу через 'git stash' или коммит. Незакоммиченные "
                "правки могут принадлежать другому агенту.")
    if sub == "clean":
        flags = "".join(a.lstrip("-") for a in args if a.startswith("-") and not a.startswith("--"))
        if ("f" in flags and "d" in flags) or "--force" in args:
            return ("удаление неотслеживаемых файлов",
                    "проверь 'git clean -n' и удаляй точечно: в дереве могут "
                    "лежать файлы окружения.")
    return None


def main() -> int:
    command = sys.stdin.read()
    for parts in segments(command):
        got = reason(parts)
        if got:
            print(got[0])
            print(got[1])
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
