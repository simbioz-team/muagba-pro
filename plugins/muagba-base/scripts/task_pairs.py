#!/usr/bin/env python3
"""Можно ли вести две задачи tasks.md параллельно.

    task_pairs.py <tasks.md> <T1> <T2> [--root <каталог проекта>]
    task_pairs.py merge <ветка1> <ветка2> [--root <каталог>]

Выход 0 — пара допустима (слияние чистое), 1 — нет (причины или
конфликтующие файлы в выводе), 2 — задача не найдена или вызов неверен.

`merge` — пробное слияние двух сданных веток пары без рабочего дерева
(`git merge-tree --write-tree`, git ≥ 2.38), за секунды. Ставится после
сдачи обеих и до ревью: заранее видно, кто вливается первым и что второй
перерешать. У narta первая пара 023 (T019 ∥ T020) по строкам «Файлы:»
делила три файла, а обеим понадобилось новое поле одной сущности —
пробное слияние нашло 4 конфликта, о которых списки молчали.

Правило пар — в блоке правил базы AGENTS.md. Здесь механическая часть:
связь в графе, пересечение объявленных файлов, миграции, общие меры. То,
чего граф не видит (смысловая зависимость), — на координаторе.

Что читается из tasks.md. Задача — пункт или заголовок с номером `T\\d+`,
до следующего такого. Внутри неё:
- `Файлы:` / `Files:` — пути через запятую или в обратных кавычках; нет
  строки — пути из текста задачи (в кавычках или с `/`), как пишет speckit
  («… in src/models/user.py»);
- `Миграция:` — непусто и не «нет» — у задачи миграция;
- `Мера:` / `Measure:` — общие меры, которые задача растит; `Сущность:` /
  `Порт:` / `Entity:` / `Port:` — общие сущности и порты, которые задача
  меняет (новое поле, метод, хранилище); через запятую;
- «зависит от T…», «после T…», «depends on T…» — зависимость. Просто
  упоминание номера — нет: заметки исполнителей («для T013, T016») у narta
  называли полграфа.
Абзацы со стрелками вне задач («T019, T020 → T021», диапазон «T023–T026» —
один уровень) — рёбра графа, связь ищется с транзитивностью.

`.claude/pair-rules.txt` проекта, по строке:
    shared <путь или префикс>   пересечение допустимо: регистрация, генерируемое
    serial <путь или префикс>   у обеих задач — не пара (миграции, общие меры)
Без файла `serial` — обычные каталоги миграций.

У narta на спеке 023 пары, которые граф разрешал, шли «строго по номерам»,
а единственный ночной блокер по общей мере (бюджет каталога MCP) стоил бы
двум задачам сразу — отсюда `serial` и `Мера:`.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TASK = re.compile(r"^\s*(?:[-*]\s*(?:\[[ xX]\]\s*)?|#{2,6}\s*)\**(T\d+)\b")
FILES = re.compile(r"^\s*[-*]?\s*\**(?:Файлы|Files)\**\s*:\s*(.*)$", re.I)
MIGR = re.compile(r"^\s*[-*]?\s*\**(?:Миграция|Migration)\**\s*:\s*(.*)$", re.I)
MEASURE = re.compile(r"^\s*[-*]?\s*\**(?:Мера|Measure|Сущность|Сущности|Порт|Порты|Entity|Entities|Port|Ports)\**\s*:\s*(.*)$", re.I)
ARROW = re.compile(r"→|->")
DEPENDS = re.compile(r"(?:зависит от|после|depends on|after|requires)\s+((?:T\d+(?:\s*[–-]\s*T\d+)?[\s,и]*(?:and\s+)?)+)", re.I)


def ids(text: str) -> list[str]:
    """Номера задач, диапазон «T023–T026» раскрыт."""
    out = []
    for a, b in re.findall(r"\b(T\d+)(?:\s*[–-]\s*(T\d+))?", text):
        if b and int(b[1:]) > int(a[1:]):
            w = len(a) - 1
            out += [f"T{n:0{w}d}" for n in range(int(a[1:]), int(b[1:]) + 1)]
        else:
            out.append(a)
    return out
SERIAL_DEFAULT = ["migrations/", "alembic/versions/", "db/migrate/"]


def paths_in(text: str) -> list[str]:
    quoted = re.findall(r"`([^`]+)`", text)
    if quoted:
        return [q.strip() for q in quoted if q.strip()]
    return [p.strip(" .;") for p in re.split(r"[,\s]+", text) if "/" in p or re.search(r"\.\w+$", p.strip(" .;"))]


def parse(text: str) -> tuple[dict, set]:
    tasks: dict[str, dict] = {}
    edges: set[tuple[str, str]] = set()
    for para in re.split(r"\n\s*\n", text):
        # Граф — абзац вне задач: без отступа и не пункт задачи. Стрелки в
        # тексте задач и заметках («видимость → архив → роль») — не рёбра.
        first = para.lstrip("\n").split("\n", 1)[0]
        if ARROW.search(para) and first[:1] not in (" ", "\t") and not TASK.match(first):
            parts = [ids(p) for p in ARROW.split(para)]
            for a, b in zip(parts, parts[1:]):
                edges |= {(x, y) for x in a for y in b}
    cur = None
    for line in text.splitlines():
        m = TASK.match(line)
        if m:
            cur = tasks.setdefault(m.group(1), {"files": [], "inline": [], "migration": False,
                                                "measures": set(), "refs": set()})
            cur["inline"] += paths_in(line[m.end():])
            for d in DEPENDS.findall(line[m.end():]):
                cur["refs"] |= set(ids(d))
            continue
        if cur is None:
            continue
        if f := FILES.match(line):
            cur["files"] += paths_in(f.group(1))
        elif g := MIGR.match(line):
            v = g.group(1).strip().strip("`*").lower()
            cur["migration"] = bool(v) and v not in ("нет", "no", "none", "—", "-")
        elif h := MEASURE.match(line):
            cur["measures"] |= {x.strip().strip("`").lower() for x in h.group(1).split(",") if x.strip()}
        for d in DEPENDS.findall(line):
            cur["refs"] |= set(ids(d))
    for t in tasks.values():
        if not t["files"]:
            t["files"] = t["inline"]
    return tasks, edges


def reach(a: str, b: str, edges: set) -> bool:
    seen, todo = {a}, [a]
    while todo:
        x = todo.pop()
        for p, q in edges:
            if p == x and q not in seen:
                if q == b:
                    return True
                seen.add(q)
                todo.append(q)
    return False


def rules(root: Path) -> tuple[list[str], list[str]]:
    shared, serial = [], []
    try:
        lines = (root / ".claude" / "pair-rules.txt").read_text(encoding="utf-8").splitlines()
    except OSError:
        return shared, list(SERIAL_DEFAULT)
    for line in lines:
        kind, _, path = line.strip().partition(" ")
        if kind == "shared" and path.strip():
            shared.append(path.strip())
        elif kind == "serial" and path.strip():
            serial.append(path.strip())
    return shared, serial or list(SERIAL_DEFAULT)


def under(path: str, prefixes: list[str]) -> bool:
    return any(path == p or path.startswith(p.rstrip("/") + "/") or (p.endswith("/") and f"/{p}" in f"/{path}")
               for p in prefixes)


def check(text: str, a: str, b: str, root: Path) -> tuple[int, list[str]]:
    tasks, edges = parse(text)
    missing = [t for t in (a, b) if t not in tasks]
    if missing:
        return 2, [f"нет задачи {', '.join(missing)} в tasks.md"]
    ta, tb = tasks[a], tasks[b]
    why = []
    if b in ta["refs"] or a in tb["refs"] or reach(a, b, edges) or reach(b, a, edges):
        why.append(f"{a} и {b} связаны в графе")
    for t in (a, b):
        if not tasks[t]["files"]:
            why.append(f"у {t} не объявлены файлы — пересечение не проверить (строка «Файлы:»)")
    shared, serial = rules(root)
    common = sorted(set(ta["files"]) & set(tb["files"]))
    logic = [p for p in common if not under(p, shared)]
    if logic:
        why.append("общие файлы: " + ", ".join(logic))
    if (ta["migration"] or any(under(p, serial) for p in ta["files"])) and \
       (tb["migration"] or any(under(p, serial) for p in tb["files"])):
        why.append("у обеих миграция или путь из serial — цепочка одна")
    if ta["measures"] & tb["measures"]:
        why.append("обе растят общую меру или меняют одну сущность: " + ", ".join(sorted(ta["measures"] & tb["measures"])))
    if why:
        return 1, why
    note = f" (общее допустимое: {', '.join(common)})" if common else ""
    return 0, [f"{a} ∥ {b}: пара допустима{note}. Смысловую зависимость граф не видит — она на координаторе."]


def merge(root: Path, a: str, b: str) -> tuple[int, list[str]]:
    r = subprocess.run(["git", "-C", str(root), "merge-tree", "--write-tree", "--name-only", a, b],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return 0, [f"{a} + {b}: сливаются без конфликтов."]
    if r.returncode != 1:
        return 2, [r.stderr.strip() or "git merge-tree не сработал (нужен git ≥ 2.38)"]
    files = []
    for line in r.stdout.splitlines()[1:]:
        if not line.strip():
            break
        files.append(line.strip())
    return 1, [f"{a} + {b}: конфликт в " + ", ".join(files or ["(список пуст)"])]


def main() -> int:
    if sys.argv[1:2] == ["merge"]:
        ap = argparse.ArgumentParser(prog="task_pairs.py merge")
        ap.add_argument("a")
        ap.add_argument("b")
        ap.add_argument("--root", default=".")
        o = ap.parse_args(sys.argv[2:])
        code, lines = merge(Path(o.root), o.a, o.b)
        print("\n".join(lines))
        return code
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--root")
    o = ap.parse_args()
    try:
        text = Path(o.tasks).read_text(encoding="utf-8")
    except OSError as e:
        print(f"task_pairs: {e}")
        return 2
    root = Path(o.root) if o.root else Path.cwd()
    code, lines = check(text, o.a.upper(), o.b.upper(), root)
    for line in lines:
        print(("" if code == 0 else "не пара: ") + line if code != 2 else f"task_pairs: {line}")
    return code


if __name__ == "__main__":
    sys.exit(main())
