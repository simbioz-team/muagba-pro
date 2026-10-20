#!/usr/bin/env python3
"""Отпечаток рабочего дерева для гейта хода.

    gate_key.py key <каталог>                 — отпечаток: хеш дерева git
    gate_key.py changed <каталог> <было> <стало> — пути, разные в двух деревьях
    gate_key.py waiting < вход хука            — живые фоновые задачи агента

Гейт хода гонял check.sh на каждом закрытии хода, а у координатора ход
кончается постоянно — отдал задачу и ждёт, прочитал файл, ответил
человеку. У narta за этап 1.4 это 131 прогон и 651 минута, зелёных 130.
Отпечаток позволяет не проверять заново то, что уже проверено зелёным.

Отпечаток — хеш дерева git из рабочих файлов: отслеживаемых с правками и
неотслеживаемых, кроме игнорируемых (`git write-tree` во временном
индексе). До 0.21.1 в нём был HEAD, и коммит без правок считался новым
деревом: у narta на спеке 022 это 22 повторных прогона, ~105 мин на
критическом пути. Содержимое то же — проверять нечего. Хеш дерева к тому
же одинаков в разных рабочих деревьях: ff-слияние приносит координатору
дерево, уже проверенное гейтом исполнителя.

Чего в отпечатке нет — база данных, окружение, файлы из .gitignore: если
check.sh зависит от них, их изменение гейт не заметит.

Побочный эффект: содержимое новых и изменённых файлов ложится в базу
объектов git как объекты без ссылок — их убирает обычный `git gc`.

Не git-репозиторий или git сломан — пустой вывод: отпечатка нет, гейт
проверяет всегда.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


def git(cwd: str, *args: str, env: dict | None = None) -> bytes | None:
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, env=env)
    return r.stdout if r.returncode == 0 else None


# Журнал агентов и выжимки сжатия пишут сами хуки базы, в том числе этот
# гейт перед проверкой. В каркасе .claude/logs/ в .gitignore, но проект без
# этой строки иначе получал бы новый отпечаток на каждом ходе.
SKIP = ".claude/logs"


def key(cwd: str) -> str:
    top = git(cwd, "rev-parse", "--show-toplevel")
    index = git(cwd, "rev-parse", "--path-format=absolute", "--git-path", "index")
    if not top or not index:
        return ""
    top_s = top.decode().strip()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_index = os.path.join(tmp, "index")
        # Копия настоящего индекса: в ней сведения о файлах, и git add
        # перечитывает только изменённое. Копия — с временем изменения
        # оригинала (copy2): по нему git узнаёт файлы, правленные в ту же
        # секунду, что записан индекс, и перечитывает их. С новым временем
        # такая правка выглядела бы чистой, и отпечаток не менялся бы.
        # Индекса нет (пустой репозиторий) — начинаем с пустого.
        if os.path.exists(index.decode().strip()):
            shutil.copy2(index.decode().strip(), tmp_index)
        env = {**os.environ, "GIT_INDEX_FILE": tmp_index}
        if git(top_s, "add", "-A", "--", ".", f":(exclude){SKIP}", env=env) is None:
            return ""
        if git(top_s, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", SKIP, env=env) is None:
            return ""
        tree = git(top_s, "write-tree", env=env)
    return tree.decode().strip() if tree else ""


def changed(cwd: str, old: str, new: str) -> list[str]:
    out = git(cwd, "diff-tree", "-r", "--name-only", "--no-renames", "-z", old, new)
    if out is None:
        raise RuntimeError("git diff-tree")
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def waiting(hook_input: str) -> list[str]:
    """Живые фоновые задачи самого агента: остановка «жду свой фоновый
    прогон» — не сдача, агент проснётся по уведомлению и остановится снова.

    Claude Code (2.1.3xx) кладёт во вход Stop и SubagentStop
    `background_tasks` — фоновые задачи всей сессии. На Stop они все свои.
    На SubagentStop там и сам сабагент, и чужое: задачи координатора и
    соседних исполнителей. Своё — то, чей номер есть в стенограмме агента
    (результат запуска: «running in background with ID: …»). Без этой
    сверки исполнитель уходил бы без гейта, пока у соседа идёт прогон.
    """
    try:
        d = json.loads(hook_input)
    except ValueError:
        return []
    tasks = [t for t in d.get("background_tasks") or []
             if isinstance(t, dict) and t.get("status") == "running" and t.get("id")]
    if d.get("hook_event_name") == "Stop":
        return [str(t["id"]) for t in tasks]
    if d.get("hook_event_name") != "SubagentStop":
        return []
    me = d.get("agent_id")
    path = d.get("agent_transcript_path")
    if not path:
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    own = []
    for t in tasks:
        tid = str(t["id"])
        if tid == me:
            continue
        if re.search(r"(?<![\w-])" + re.escape(tid) + r"(?![\w-])", text):
            own.append(tid)
    return own


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "key":
        print(key(a[1]))
    elif len(a) == 4 and a[0] == "changed":
        try:
            sys.stdout.write("".join(p + "\n" for p in changed(a[1], a[2], a[3])))
        except RuntimeError:
            sys.exit(1)
    elif len(a) == 1 and a[0] == "waiting":
        print(" ".join(waiting(sys.stdin.read())))
    else:
        sys.exit(2)
