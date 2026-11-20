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

- **спека** — по ветке (`033-…`, `033/…`). Нет номера в ветке — спеки нет,
  выводится только «в работе»: угадывать нельзя. Две сессии на одной ветке
  без номера получали одну «последнюю открытую» спеку, которую не вела ни
  одна из них (наставник, 20.11);
- **сделано** — строки `- [x]` в её tasks.md;
- **в работе** — исполнители **этой сессии** (`session_id` входа),
  запущенные и не остановленные, по журналу агентов `.claude/logs/agents.jsonl` (log-agent.sh). Без сети: строка
  обновляется часто, и запрос к трекеру её бы тормозил;
- **осталось** — открытые `- [ ]` за вычетом тех, что в работе.

**Задачи трекера (Narta).** Если ветка не называет спеку, а сессия ведёт
задачи в Narta, счёт берётся оттуда. Делят работу так:

- `--narta-keys` — номера задач сессии из её стенограммы: созданные
  (`create_tasks`), взятые (`take_task`), переведённые (`transition_task`).
  Стенограмма читается с места, где кончилось прошлое чтение, позиция — в
  `.claude/logs/progress/<сессия>.scan.json`;
- статусы спрашивает мод `hooks/tasks.tsx` — у Narta через подключение самой
  сессии, без своих ключей, — и пишет итог в
  `.claude/logs/progress/<сессия>.json`;
- строка состояния читает этот итог, если он свежий: `N ✓12 ⏵2 ○5`.

Сессия без инструментов Narta ничего этого не делает.

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
FRESH = timedelta(minutes=20)  # итог Narta старше — мод не работает, не показываем
NARTA = re.compile(r"^mcp__(narta[\w-]*)__(create_tasks|take_task|transition_task)$")
KEY = re.compile(r"^T-\d+$")


def git_top_and_branch(cwd: str) -> tuple[Path, str]:
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", "-C", cwd, *args], capture_output=True,
                                  text=True, timeout=2).stdout.strip()
        except Exception:
            return ""
    # symbolic-ref, а не rev-parse --abbrev-ref: у ветки без коммитов второй даёт «HEAD».
    return Path(git("rev-parse", "--show-toplevel") or cwd), git("symbolic-ref", "--short", "-q", "HEAD")


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
    return None


def items(tasks: Path) -> list[dict]:
    out = []
    for line in tasks.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ITEM.match(line)
        if m:
            out.append({"done": m.group(1) in "xX", "text": m.group(2).strip()})
    return out


def running(log: Path, now: datetime, sid: str = "") -> list[dict]:
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
        if not aid or (sid and r.get("session_id") != sid):
            continue
        if r.get("event") == "SubagentStart" and "implementer" in (r.get("agent_type") or ""):
            live[aid] = (ts, r.get("agent_type") or "")
        elif r.get("event") == "SubagentStop":
            live.pop(aid, None)
    return [{"agent_id": aid, "type": t, "minutes": int((now - ts).total_seconds() // 60)}
            for aid, (ts, t) in live.items() if now - ts < STALE]


def progress_dir(proj: Path) -> Path:
    return proj / ".claude" / "logs" / "progress"


def narta_keys(transcript: str, cache: Path) -> dict:
    """Номера задач Narta, которые сессия создала, взяла или перевела."""
    try:
        st = json.loads(cache.read_text(encoding="utf-8"))
    except Exception:
        st = {}
    st.setdefault("offset", 0)
    st.setdefault("keys", [])
    st.setdefault("ids", {})        # UUID → номер, из ответов create_tasks
    st.setdefault("pending", {})    # tool_use_id create_tasks → ждёт ответа
    st.setdefault("server", "")
    keys = dict.fromkeys(st["keys"])
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size < st["offset"]:
                st["offset"] = 0
            f.seek(st["offset"])
            data = f.read()
    except OSError:
        return {"server": st["server"], "keys": list(keys)}
    end = data.rfind(b"\n") + 1  # недописанную строку дочитаем в следующий раз
    for line in data[:end].decode("utf-8", "replace").splitlines():
        # Ответ create_tasks слова «narta» не содержит: его строку берём, пока ждём ответа.
        if "narta" not in line and not (st["pending"] and "tool_result" in line):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        content = (o.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                m = NARTA.match(b.get("name") or "")
                if not m:
                    continue
                st["server"] = m.group(1)
                tid = str((b.get("input") or {}).get("task_id") or "")
                tid = st["ids"].get(tid, tid)
                if KEY.match(tid):
                    keys[tid] = None
                if m.group(2) == "create_tasks":
                    st["pending"][b.get("id")] = 1
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in st["pending"]:
                st["pending"].pop(b["tool_use_id"], None)
                text = b.get("content")
                if isinstance(text, list):
                    text = "".join(x.get("text", "") for x in text if isinstance(x, dict))
                try:
                    created = json.loads(text or "")["data"]["tasks"]
                except Exception:
                    continue
                for t in created:
                    if isinstance(t, dict) and KEY.match(str(t.get("key"))):
                        keys[t["key"]] = None
                        if t.get("id"):
                            st["ids"][t["id"]] = t["key"]
    st["offset"] += end
    st["keys"] = list(keys)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return {"server": st["server"], "keys": st["keys"]}


def narta_summary(proj: Path, sid: str, now: datetime):
    if not sid:
        return None
    try:
        p = progress_dir(proj) / f"{sid}.json"
        if datetime.fromtimestamp(p.stat().st_mtime) < now - FRESH:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    ws = d.get("workspace") or {}
    cwd = ws.get("current_dir") or d.get("cwd") or "."
    top, branch = git_top_and_branch(cwd)
    as_json = "--json" in sys.argv[1:]
    sid = str(d.get("session_id") or "")
    proj = Path(ws.get("project_dir") or top)
    if "--narta-keys" in sys.argv[1:]:
        tr = str(d.get("transcript_path") or "")
        out = narta_keys(tr, progress_dir(proj) / f"{sid}.scan.json") if tr and sid else {"server": "", "keys": []}
        print(json.dumps(out, ensure_ascii=False))
        return 0
    has_specs = any((top / "specs").glob("*/tasks.md"))
    spec = pick_spec(top, branch) if has_specs else None
    if spec is None:
        n = narta_summary(proj, sid, datetime.now())
        if n is not None:
            if as_json:
                print(json.dumps({"spec": None, "branch": branch, "narta": n,
                                  "busy": n.get("busy", 0), "agents": []}, ensure_ascii=False))
            else:
                print(f"N ✓{n.get('done', 0)} ⏵{n.get('busy', 0)} ○{n.get('left', 0)}")
            return 0
    if not has_specs:
        if as_json:
            print("null")
        return 0
    # Журнал агентов пишет сессия, а не дерево (log-agent.sh, project_dir).
    agents = running(proj / ".claude" / "logs" / "agents.jsonl", datetime.now(), sid)
    if spec is None:
        if as_json:
            print(json.dumps({"spec": None, "branch": branch, "busy": len(agents),
                              "agents": agents}, ensure_ascii=False))
        elif agents:
            print(f"⏵{len(agents)}")
        return 0
    done, open_ = count(spec)
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
