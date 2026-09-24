#!/usr/bin/env python3
"""Что команда удаляет: печатает пути-операнды, по одному на строку.

Отдельно от `write_targets.py` намеренно. Тот отвечает на вопрос «во что
команда пишет», и удаление туда не входило: `rm docs/constitution.md`
проходил мимо защиты путей целиком — запрет на правку стоял, а на снос нет.
Нашёл сосед, доводивший проект на базе.

Разделение нужно и дальше: по записи хук решает одно, по удалению — другое.
Удаление файла, которого нет в гите и который не пересобирается, вернуть
неоткуда, и на него хук спрашивает человека; на запись — нет.

Границы те же, что у разбора записи: shlex снимает кавычки, но подстановка
переменной (`f=data.db; rm $f`) и маска (`rm *.db`) остаются словом, а не
путём. Полного разбора оболочки здесь нет и быть не может.
"""

from __future__ import annotations

import os
import shlex
import sys

from shell_split import segments  # общий разбор: см. shell_split.py

# Команды, стирающие файл. `shred` сюда же: он делает то же самое, только
# необратимее. `git rm` не разбираем — первый токен `git`, и одноимённых
# подкоманд у него хватает.
DELETERS = {"rm", "rmdir", "unlink", "shred"}


def operands(parts: list[str]) -> list[str]:
    if not parts:
        return []
    if os.path.basename(parts[0]) not in DELETERS:
        return []
    found: list[str] = []
    only_operands = False
    for arg in parts[1:]:
        if only_operands:
            found.append(arg)
        elif arg == "--":
            only_operands = True
        elif arg.startswith("-") and len(arg) > 1:
            continue
        else:
            found.append(arg)
    return found


def main() -> int:
    command = sys.stdin.read()
    seen: list[str] = []
    cwd = ""  # куда увёл `cd`, пройденный раньше в этой же команде
    for parts in segments(command):
        if parts and os.path.basename(parts[0]) == "cd":
            rest = [a for a in parts[1:] if not a.startswith("-")]
            if len(rest) == 1 and rest[0] != "-":
                cwd = (rest[0] if rest[0].startswith("/")
                       else os.path.normpath(os.path.join(cwd, rest[0])))
            else:
                cwd = ""
            continue
        for t in operands(parts):
            if not t:
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
