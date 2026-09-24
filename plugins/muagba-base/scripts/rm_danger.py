#!/usr/bin/env python3
"""Опасен ли `rm` в команде: печатает цель, если да, иначе молчит.

`rm -rf /tmp/build` — обычная команда. Ловить её шаблоном «rm -rf /» значит
блокировать любой абсолютный путь и врать в объяснении. Опасно другое:
корень, домашний каталог и каталоги первого уровня (`/usr`, `/etc`), где
рекурсивное удаление сносит систему целиком, а не результат сборки.

Разбор через shlex: кавычки и экранирование учитываются, `rm -rf "/"` не
проедет мимо.
"""

from __future__ import annotations

import os
import shlex
import sys

from shell_split import segments  # общий разбор: см. shell_split.py

RECURSIVE = {"r", "R"}
FORCE = {"f"}

# Цели, для которых рекурсивное удаление почти наверняка катастрофа.
FATAL_EXACT = {"/", "/*", "~", "~/", "$HOME", "${HOME}", "."}


def fatal_target(parts: list[str]) -> str | None:
    if not parts:
        return None
    name = os.path.basename(parts[0])
    if name != "rm":
        return None

    recursive = force = False
    targets: list[str] = []
    only_operands = False
    for arg in parts[1:]:
        if only_operands:
            targets.append(arg)
        elif arg == "--":
            only_operands = True
        elif arg.startswith("--"):
            if arg == "--recursive":
                recursive = True
            elif arg == "--force":
                force = True
        elif arg.startswith("-") and len(arg) > 1:
            recursive |= bool(RECURSIVE & set(arg[1:]))
            force |= bool(FORCE & set(arg[1:]))
        else:
            targets.append(arg)

    if not recursive:
        return None  # без -r рекурсивного сноса не будет

    for t in targets:
        clean = t.rstrip("/") + "/" if t.endswith("/") and t != "/" else t
        if t in FATAL_EXACT or clean in FATAL_EXACT:
            return t
        expanded = os.path.expandvars(t)
        if expanded in FATAL_EXACT:
            return t
        # Каталог первого уровня: /usr, /etc, /home — но не /home/user/build
        if t.startswith("/"):
            depth = [p for p in t.strip("/").split("/") if p not in ("", ".")]
            if len(depth) <= 1:
                return t
        # ~/ без вложенности: ~/ или ~/*
        if t in ("~/*", "~/."):
            return t
    _ = force  # -f не делает команду опаснее, только тише
    return None


def main() -> int:
    command = sys.stdin.read()
    for parts in segments(command):
        t = fatal_target(parts)
        if t:
            print(t)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
