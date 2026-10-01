#!/usr/bin/env python3
"""Очереди конвейера: где агенты стоят, ожидая координатора, и сколько.

Нужда — проект narta: координатор один на этап, исполнитель и ревьюер
свои на задачу, общие ресурсы — координатор, один раннер CI, владелец.
Время уходит не только на работу, но и на ожидание: агент закончил, а
следующее звено задачи стартовало через четверть часа. Журнал агентов
этого не показывал.

Новых хуков не нужно: всё уже есть в стенограмме координатора.
- Поручение — вызов инструмента Agent: описание, текст, время; результат
  несёт agentId.
- «Готово» — уведомление <task-notification> с task-id = agentId, при
  каждой остановке агента. Если координатор занят, уведомление встаёт в
  очередь (`queue-operation` enqueue — момент, когда агент закончил) и
  попадает к координатору позже (`queued_command`). Разница — сколько
  агент ждал, пока координатор освободится.
- Продолжение — SendMessage агенту: круг правок или повторное ревью.
- Слияние — Bash `gh pr merge N`; номер PR связан с задачей по выводу
  `gh pr create`, где задача названа в заголовке или ветке.

Задача — ключ в описании или тексте поручения, по умолчанию `T\\d{3}`
(`--task-re` — свой шаблон).

Что считается:
- работа — от поручения или продолжения до остановки агента;
- очередь — от остановки агента до следующего действия координатора по
  той же задаче: новое поручение, продолжение, слияние. Подпись звена —
  «после <роль>»;
- простой — отрезки, когда не работал ни один агент, длиннее минуты;
- чем был занят координатор в очередях — его вызовы инструментов в эти
  отрезки, по классам;
- CI (`--ci`) — от создания сборки до старта первой её задачи (очередь к
  раннеру) и до конца сборки. Данные — `gh run list` и `gh run view`.

Запуск:
  python3 pipeline_queues.py [--cwd КАТАЛОГ] [--since ISO] [--until ISO]
                             [--task-re RE] [--ci] [--csv КАТАЛОГ]
Стенограммы — ~/.claude/projects/<проект>/*.jsonl, основные сессии.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_split import command_class  # noqa: E402

UTC = dt.timezone.utc


def ts(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def slug(root: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", root)


def blocks(e: dict) -> list[dict]:
    c = (e.get("message") or {}).get("content")
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def text_of(e: dict) -> str:
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    return " ".join(b.get("text", "") for b in blocks(e) if b.get("type") == "text")


NOTIF = re.compile(r"<task-notification>.*?<task-id>([^<]+)</task-id>.*?</task-notification>", re.S)
PR_URL = re.compile(r"/pull/(\d+)")


def read_events(files: list[str], task_re: re.Pattern) -> tuple[list[dict], list[tuple]]:
    """Поток событий координатора и его вызовы инструментов (время, класс)."""
    ev: list[dict] = []
    calls: list[tuple] = []
    pending: dict[str, dict] = {}       # tool_use_id → поручение, ждёт agentId
    agents: dict[str, dict] = {}        # agentId → {task, role}
    pr_task: dict[str, str] = {}
    pending_pr: dict[str, str] = {}     # tool_use_id `gh pr create` → задача
    for f in files:
        try:
            lines = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in lines:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("isSidechain"):
                continue
            t = ts(e.get("timestamp"))
            if not t:
                continue
            for b in blocks(e):
                if b.get("type") == "tool_use":
                    name, inp = b.get("name"), b.get("input") or {}
                    calls.append((t, name if name != "Bash" else
                                  (command_class(str(inp.get("command") or "")) or "Bash")))
                    if name in ("Agent", "Task"):
                        m = task_re.search(f"{inp.get('description', '')} {inp.get('prompt', '')}")
                        pending[b.get("id")] = {"task": m.group(0) if m else "",
                                                "role": inp.get("subagent_type") or "general-purpose",
                                                "desc": str(inp.get("description") or "")[:80]}
                    elif name == "SendMessage":
                        a = agents.get(str(inp.get("to") or ""))
                        if a:
                            ev.append({"t": t, "kind": "resume", "agent": inp["to"], **a})
                    elif name == "Bash":
                        cmd = str(inp.get("command") or "")
                        if re.search(r"\bgh\b.*\bpr\s+create\b", cmd):
                            m = task_re.search(cmd)
                            if m:
                                pending_pr[b.get("id")] = m.group(0)
                        m = re.search(r"\bgh\b.*\bpr\s+merge\s+(\d+)", cmd)
                        if m and m.group(1) in pr_task:
                            ev.append({"t": t, "kind": "merge", "task": pr_task[m.group(1)],
                                       "role": "слияние", "agent": ""})
                elif b.get("type") == "tool_result":
                    tid = b.get("tool_use_id")
                    if tid in pending_pr:
                        m = PR_URL.search(json.dumps(b.get("content"), ensure_ascii=False))
                        if m:
                            pr_task[m.group(1)] = pending_pr.pop(tid)
            r = e.get("toolUseResult")
            if isinstance(r, dict) and r.get("agentId"):
                tid = next((b.get("tool_use_id") for b in blocks(e) if b.get("type") == "tool_result"), None)
                p = pending.pop(tid, None)
                if p:
                    agents[r["agentId"]] = {"task": p["task"], "role": p["role"]}
                    ev.append({"t": t, "kind": "dispatch", "agent": r["agentId"], **p})
                    if not r.get("isAsync") and r.get("status") == "completed":
                        ev.append({"t": t, "kind": "done", "agent": r["agentId"], **agents[r["agentId"]]})
            # Уведомление о завершении: в очереди (агент закончил) и доставка
            # координатору — отдельными записями. Первая после работы — «готово»,
            # следующая — «увидел».
            note = ""
            if e.get("type") == "queue-operation" and e.get("operation") == "enqueue":
                note = str(e.get("content") or "")
            elif isinstance(e.get("attachment"), dict) and e["attachment"].get("type") == "queued_command":
                note = str(e["attachment"].get("prompt") or "")
            elif e.get("type") == "user":
                note = text_of(e) or json.dumps((e.get("message") or {}).get("content"), ensure_ascii=False)
            for aid in NOTIF.findall(note):
                a = agents.get(aid.strip())
                if a:
                    ev.append({"t": t, "kind": "done", "agent": aid.strip(), **a})
    ev.sort(key=lambda x: x["t"])
    calls.sort()
    return ev, calls


def analyse(ev: list[dict], calls: list[tuple]) -> dict:
    work, queue, idle = [], [], []
    running: dict[str, dt.datetime] = {}
    last_done: dict[str, dict] = {}     # задача → последняя остановка
    stopped: dict[str, dict] = {}       # агент → его последняя остановка (ждёт доставки)
    idle_from: dt.datetime | None = None
    for x in ev:
        if x["kind"] in ("dispatch", "resume"):
            if not running and idle_from and (x["t"] - idle_from).total_seconds() >= 60:
                idle.append((idle_from, x["t"]))
            running[x["agent"]] = x["t"]
        if x["kind"] in ("dispatch", "resume", "merge") and x["task"] in last_done:
            d = last_done.pop(x["task"])
            seen = d.get("seen")
            queue.append({"task": x["task"], "after": d["role"],
                          "next": x["role"] if x["kind"] != "resume" else f"правки: {x['role']}",
                          "from": d["t"], "to": x["t"], "min": (x["t"] - d["t"]).total_seconds() / 60,
                          # Доставка не найдена — неизвестно, а не «вся очередь».
                          "unseen_min": (min(seen, x["t"]) - d["t"]).total_seconds() / 60 if seen else None})
        if x["kind"] == "done":
            start = running.pop(x["agent"], None)
            if start:
                work.append({"task": x["task"], "role": x["role"], "from": start, "to": x["t"],
                             "min": (x["t"] - start).total_seconds() / 60})
                rec = {**x, "seen": None}
                stopped[x["agent"]] = rec
                if x["task"]:
                    last_done[x["task"]] = rec
                if not running:
                    idle_from = x["t"]
            elif x["agent"] in stopped and stopped[x["agent"]]["seen"] is None \
                    and x["t"] > stopped[x["agent"]]["t"]:
                # Повтор того же уведомления — доставка координатору.
                stopped[x["agent"]]["seen"] = x["t"]
    for q in queue:
        busy = defaultdict(int)
        for t, cls in calls:
            if q["from"] <= t < q["to"]:
                busy[cls] += 1
        q["busy"] = dict(sorted(busy.items(), key=lambda kv: -kv[1])[:4])
    return {"work": work, "queue": queue, "idle": idle,
            "waiting": [{"task": t, "role": d["role"], "since": d["t"]} for t, d in last_done.items()]}


def ci_runs(root: str, since: dt.datetime | None) -> list[dict]:
    out = subprocess.run(["gh", "run", "list", "--limit", "200", "--json",
                          "databaseId,createdAt,updatedAt,headBranch,event,conclusion"],
                         cwd=root, capture_output=True, text=True)
    try:
        runs = json.loads(out.stdout or "[]")
    except ValueError:
        return []
    res = []
    for r in runs:
        c = ts(r.get("createdAt"))
        if since and c and c < since:
            continue
        v = subprocess.run(["gh", "run", "view", str(r["databaseId"]), "--json", "jobs"],
                           cwd=root, capture_output=True, text=True)
        try:
            jobs = json.loads(v.stdout or "{}").get("jobs") or []
        except ValueError:
            jobs = []
        starts = [ts(j.get("startedAt")) for j in jobs if j.get("startedAt")]
        ends = [ts(j.get("completedAt")) for j in jobs if j.get("completedAt")]
        if c and starts:
            res.append({"run": r["databaseId"], "branch": r.get("headBranch"), "event": r.get("event"),
                        "queue_min": (min(starts) - c).total_seconds() / 60,
                        "total_min": ((max(ends) if ends else ts(r.get("updatedAt"))) - c).total_seconds() / 60})
    return res


def stats(xs: list[float]) -> str:
    if not xs:
        return "— | — | — | 0"
    s = sorted(xs)
    med = s[len(s) // 2]
    p90 = s[min(len(s) - 1, int(len(s) * 0.9))]
    return f"{med:.1f} | {p90:.1f} | {sum(s):.0f} | {len(s)}"


def report(a: dict, ci: list[dict] | None) -> str:
    L = ["# Очереди конвейера", "",
         "Минуты. Работа — от поручения до остановки агента; очередь — от остановки до "
         "следующего действия координатора по той же задаче. В очередь входит и "
         "намеренное ожидание — порядок задач, ответ владельца (`AskUserQuestion` в "
         "колонке занятости): это не всегда медлительность координатора.", "",
         "## Работа по ролям", "", "| Роль | Медиана | 90% | Сумма | n |", "|---|---|---|---|---|"]
    by = defaultdict(list)
    for w in a["work"]:
        by[w["role"]].append(w["min"])
    for r, xs in sorted(by.items(), key=lambda kv: -sum(kv[1])):
        L.append(f"| {r} | {stats(xs)} |")
    known = [q for q in a["queue"] if q["unseen_min"] is not None]
    un = [q["unseen_min"] for q in known]
    L += ["", "## Очереди по звеньям", "",
          f"Уведомление «готово» ждало, пока координатор освободится: медиана "
          f"{stats(un).split(' | ')[0]} мин, сумма {sum(un):.0f} мин из "
          f"{sum(q['min'] for q in known):.0f} мин этих очередей ({len(known)} из "
          f"{len(a['queue'])}; у остальных доставка в стенограмме не найдена).", "",
          "| После | Дальше | Медиана | 90% | Сумма | n |", "|---|---|---|---|---|---|"]
    by = defaultdict(list)
    for q in a["queue"]:
        by[(q["after"], q["next"])].append(q["min"])
    for (af, nx), xs in sorted(by.items(), key=lambda kv: -sum(kv[1])):
        L.append(f"| {af} | {nx} | {stats(xs)} |")
    L += ["", "## Самые долгие очереди", "",
          "| Задача | После | Дальше | Мин | Из них не доставлено | Чем был занят координатор |",
          "|---|---|---|---|---|---|"]
    for q in sorted(a["queue"], key=lambda q: -q["min"])[:10]:
        busy = ", ".join(f"{k} ×{v}" for k, v in q["busy"].items()) or "—"
        un1 = "?" if q["unseen_min"] is None else f"{q['unseen_min']:.1f}"
        L.append(f"| {q['task']} | {q['after']} | {q['next']} | {q['min']:.1f} | {un1} | {busy} |")
    tot = sum((b - f).total_seconds() / 60 for f, b in a["idle"])
    L += ["", f"## Простой: ни один агент не работал", "",
          f"{len(a['idle'])} отрезков от минуты, всего {tot:.0f} мин."]
    for f, b in sorted(a["idle"], key=lambda x: x[0] - x[1])[:5]:
        L.append(f"- {f:%Y-%m-%d %H:%M}–{b:%H:%M} UTC, {(b - f).total_seconds() / 60:.0f} мин")
    if a["waiting"]:
        L += ["", "## Ждут сейчас", ""] + [f"- {w['task']} после {w['role']} с {w['since']:%Y-%m-%d %H:%M} UTC"
                                         for w in a["waiting"]]
    if ci is not None:
        L += ["", "## CI", "", "| | Медиана | 90% | Сумма | n |", "|---|---|---|---|---|",
              f"| очередь к раннеру | {stats([r['queue_min'] for r in ci])} |",
              f"| сборка целиком | {stats([r['total_min'] for r in ci])} |"]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--task-re", default=r"\bT\d{3}\b")
    ap.add_argument("--ci", action="store_true")
    ap.add_argument("--csv")
    ap.add_argument("--transcripts", help="каталог стенограмм (по умолчанию ~/.claude/projects/<проект>)")
    o = ap.parse_args()
    root = str(Path(o.cwd).resolve())
    tdir = Path(o.transcripts) if o.transcripts else Path.home() / ".claude" / "projects" / slug(root)
    files = sorted(glob.glob(str(tdir / "*.jsonl")))
    if not files:
        print(f"pipeline_queues: стенограмм нет в {tdir}")
        return 1
    ev, calls = read_events(files, re.compile(o.task_re))
    lo, hi = ts(o.since), ts(o.until)
    ev = [x for x in ev if (not lo or x["t"] >= lo) and (not hi or x["t"] <= hi)]
    calls = [c for c in calls if (not lo or c[0] >= lo) and (not hi or c[0] <= hi)]
    a = analyse(ev, calls)
    ci = ci_runs(root, lo) if o.ci else None
    print(report(a, ci), end="")
    if o.csv:
        d = Path(o.csv)
        d.mkdir(parents=True, exist_ok=True)
        for name, rows in (("work", a["work"]), ("queue", a["queue"])):
            with (d / f"pipeline-{name}.csv").open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["task", "role_or_after", "next", "from", "to", "min"])
                for r in rows:
                    w.writerow([r["task"], r.get("role") or r.get("after"), r.get("next", ""),
                                r["from"].isoformat(), r["to"].isoformat(), f"{r['min']:.2f}"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
