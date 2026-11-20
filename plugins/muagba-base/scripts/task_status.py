#!/usr/bin/env python3
"""Сегмент строки состояния: сколько задач текущей спеки сделано, в работе, осталось.

Строку состояния задаёт пользователь или проект (`statusLine` в settings.json),
плагин её не ставит. Скрипт печатает один сегмент — его дописывают в свою
строку состояния:

    seg=$(printf '%s' "$input" | python3 <плагин>/scripts/task_status.py)

На входе — JSON строки состояния (stdin). На выходе — `033 ✓14 ⏵2 ○3` или
пустая строка, если в проекте нет `specs/*/tasks.md`. С `--json` — то же
подробно, для панели мода `tasks`: открытые задачи и исполнители в работе: как любой хук базы,
без своего файла скрипт ничего не делает.

- **спека** — по ветке (`033-…`, `033/…`), иначе последняя с открытыми
  задачами;
- **сделано** — строки `- [x]` в её tasks.md;
- **в работе** — исполнители, запущенные и не остановленные, по журналу
  агентов `.claude/logs/agents.jsonl` (log-agent.sh). Без сети: строка
  обновляется часто, и запрос к трекеру её бы тормозил;
- **осталось** — открытые `- [ ]` за вычетом тех, что в работе.

Строка состояния вызывается после каждого ответа, поэтому скрипт не
читает журнал целиком (хвост) и ничего не пишет.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BOX = re.compile(r"^\s*[-*] \[([ xX])\]", re.M)
ITEM = re.compile(r"^\s*[-*] \[([ xX])\]\s*(.*)$")
SPEC = re.compile(r"^(\d{3})-")
BRANCH_SPEC = re.compile(r"(?:^|/)(\d{3})(?:[-/]|$)")
TAIL = 512 * 1024
STALE = timedelta(hours=6)  # оборванный исполнитель не висит «в работе» вечно


def git_top_and_branch(cwd: str) -> tuple[Path, str]:
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2,
        ).stdout.split("\n")
        return Path(out[0]), out[1]
    except Exception:
        return Path(cwd), ""


def count(tasks: Path) -> tuple[int, int]:
    marks = BOX.findall(tasks.read_text(encoding="utf-8", errors="replace"))
    done = sum(1 for m in marks if m in "xX")
    return done, len(marks) - done


def pick_spec(top: Path, branch: str):
    specs = sorted(p for p in (top / "specs").glob("*/tasks.md") if SPEC.match(p.parent.name))
    if not specs:
        return None
    m = BRANCH_SPEC.search(branch or "")
    if m:
        for p in specs:
            if p.parent.name.startswith(m.group(1) + "-"):
                return p
    for p in reversed(specs):
        if count(p)[1]:
            return p
    return None


def items(tasks: Path) -> list[dict]:
    out = []
    for line in tasks.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ITEM.match(line)
        if m:
            out.append({"done": m.group(1) in "xX", "text": m.group(2).strip()})
    return out


def running(log: Path, now: datetime) -> list[dict]:
    try:
        with log.open("rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - TAIL))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    live: dict[str, tuple[datetime, str]] = {}
    for line in lines:
        try:
            r = json.loads(line)
            ts = datetime.fromisoformat(r["ts"])
        except Exception:
            continue
        aid = r.get("agent_id")
        if not aid:
            continue
        if r.get("event") == "SubagentStart" and "implementer" in (r.get("agent_type") or ""):
            live[aid] = (ts, r.get("agent_type") or "")
        elif r.get("event") == "SubagentStop":
            live.pop(aid, None)
    return [{"agent_id": aid, "type": t, "minutes": int((now - ts).total_seconds() // 60)}
            for aid, (ts, t) in live.items() if now - ts < STALE]


def main() -> int:
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    ws = d.get("workspace") or {}
    cwd = ws.get("current_dir") or d.get("cwd") or "."
    top, branch = git_top_and_branch(cwd)
    spec = pick_spec(top, branch)
    as_json = "--json" in sys.argv[1:]
    if spec is None:
        if as_json:
            print("null")
        return 0
    done, open_ = count(spec)
    # Журнал агентов пишет сессия, а не дерево (log-agent.sh, project_dir).
    proj = Path(ws.get("project_dir") or top)
    agents = running(proj / ".claude" / "logs" / "agents.jsonl", datetime.now())
    busy = min(len(agents), open_)
    num = SPEC.match(spec.parent.name).group(1)
    if as_json:
        print(json.dumps({
            "spec": spec.parent.name, "num": num, "path": str(spec),
            "done": done, "busy": busy, "left": open_ - busy,
            "agents": agents, "open": [i["text"] for i in items(spec) if not i["done"]],
        }, ensure_ascii=False))
        return 0
    print(f"{num} ✓{done} ⏵{busy} ○{open_ - busy}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # строка состояния важнее сегмента: сбой — пустой вывод
