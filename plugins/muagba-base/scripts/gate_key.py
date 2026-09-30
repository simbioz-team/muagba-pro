#!/usr/bin/env python3
"""Отпечаток рабочего дерева для гейта хода: `key <каталог>` печатает его.

Гейт хода гонял полный check.sh на каждом закрытии хода, а у координатора
ход кончается постоянно — отдал задачу и ждёт, прочитал файл, ответил
человеку. У narta за этап 1.4 это 131 прогон и 651 минута, зелёных 130, и
в сотне случаев код перед этим не менялся. Отпечаток позволяет не
проверять заново то, что уже проверено зелёным.

В отпечаток входит всё, что видит git: HEAD, изменения отслеживаемых
файлов (индекс и рабочее дерево) и содержимое неотслеживаемых, кроме
игнорируемых. Чего в нём нет — база данных, окружение, файлы из
.gitignore: если check.sh зависит от них, их изменение гейт не заметит.

Не git-репозиторий или git сломан — пустой вывод: отпечатка нет, гейт
проверяет всегда.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def git(cwd: str, *args: str) -> bytes | None:
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True)
    return r.stdout if r.returncode == 0 else None


# Журнал агентов и выжимки сжатия пишут сами хуки базы, в том числе этот
# гейт перед проверкой. В каркасе .claude/logs/ в .gitignore, но проект без
# этой строки иначе получал бы новый отпечаток на каждом ходе.
SKIP = ":(exclude).claude/logs"


def key(cwd: str) -> str:
    head = git(cwd, "rev-parse", "-q", "--verify", "HEAD")
    diff = (git(cwd, "diff", "HEAD", "--binary", "--", ".", SKIP) if head
            else git(cwd, "diff", "--cached", "--binary", "--", ".", SKIP))
    others = git(cwd, "ls-files", "--others", "--exclude-standard", "-z", "--", ".", SKIP)
    if diff is None or others is None:
        return ""
    h = hashlib.sha256()
    h.update(head or b"no-head")
    h.update(b"\0diff\0" + diff)
    for rel in sorted(p for p in others.split(b"\0") if p):
        h.update(b"\0file\0" + rel + b"\0")
        try:
            h.update(Path(cwd, rel.decode("utf-8", "surrogateescape")).read_bytes())
        except OSError:
            h.update(b"<unreadable>")
    return h.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "key":
        print(key(sys.argv[2]))
