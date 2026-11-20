#!/usr/bin/env python3
"""На что уходит время и откуда берутся ошибки — по стенограмме одной сессии.

  monitor.py --since 2026-11-20T15:00Z <стенограмма.jsonl> [ещё…]

По каждой сессии за окно:

- **запуски по ролям** — сколько, медиана минут и запросов, уплотнения;
- **задачи** — номер из описания запуска (T-2262, T049): сколько запусков
  исполнителя и ревьюера на задачу. Два ревью и больше — задача вернулась;
- **красные проверки** — запуски проверок (check.sh, pytest, ruff, mypy, tsc,
  eslint, prettier, playwright, npm test/run) с ненулевым выходом, с разбивкой
  по причине: стиль и типы (их ловит быстрая проверка), тесты, e2e, время;
- **ожидание человека** — промежутки, кончившиеся сообщением человека, и
  сколько из них — короткое «продолжай»/«да»;
- **простой координатора** — промежутки больше 2 минут, кончившиеся
  уведомлением фоновой работы: координатор ждал, ничего не делая параллельно.

Цифры — подсказка, где искать; причину читай в стенограмме.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime

CHECK = re.compile(r"check\.sh|pytest|ruff|mypy|\btsc\b|eslint|prettier|playwright|npm (run|test)|pnpm|vitest|make (test|check)")
NOT_CHECK = re.compile(r"^\s*(grep|rg|cat|sed|head|tail|ls|git|find|echo|wc)\b")
TOKEN = re.compile(r"[\w.-]*\d[\w.-]*")


def task_key(desc: str) -> str | None:
    """Номер задачи и этап из описания запуска: «T-2262 5d-2», «A1a-3», «T049»."""
    d = re.sub(r"^\w+/[\w-]+:\s*", "", desc)
    d = re.sub(r"(?i)^(ревью|review|доработка|правка)\s+", "", d)
    d = re.sub(r"(?i)\b(круг|round)\s*\d+|\br\d+\b", "", d)
    toks = TOKEN.findall(d.split(":")[0])
    if not toks:
        return None
    if re.match(r"T-?\d+$", toks[0]) and len(toks) > 1:
        return f"{toks[0]} {toks[1]}"
    return toks[0]
GO = re.compile(r"^\s*(продолжай|продолжи|да|ок|ok|давай|делай|го|дальше|yes|continue)[\s.!]*$", re.I)


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def lines(path: str):
    for line in open(path, errors="replace"):
        try:
            yield json.loads(line)
        except Exception:
            continue


def blocks(o):
    c = (o.get("message") or {}).get("content")
    return c if isinstance(c, list) else []


def text_of(b) -> str:
    t = b.get("content")
    if isinstance(t, list):
        t = "".join(x.get("text", "") for x in t if isinstance(x, dict))
    return t or ""


def why_red(out: str) -> str:
    o = out.lower()
    if re.search(r"ruff|flake8|prettier|eslint|black|isort|line too long|e501|format", o):
        return "стиль/формат"
    if re.search(r"mypy|error ts\d|\btsc\b|type error|incompatible type", o):
        return "типы"
    if re.search(r"playwright|e2e|timeout.*exceeded|tobevisible", o):
        return "e2e"
    if re.search(r"timed out|timeout", o):
        return "время"
    if re.search(r"failed|error|assert", o):
        return "тесты"
    return "прочее"


def checks(path: str, since: datetime):
    """Запуски проверок: (время, причина) для красных, и сколько всего."""
    uses, red, total = {}, [], 0
    notes = {}
    for o in lines(path):
        for b in blocks(o):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == "Bash" and o.get("timestamp"):
                cmd = (b.get("input") or {}).get("command", "")
                if CHECK.search(cmd) and not NOT_CHECK.match(cmd) and ts(o["timestamp"]) >= since:
                    uses[b["id"]] = (o["timestamp"], cmd)
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                t, cmd = uses.pop(b["tool_use_id"])
                out = text_of(b)
                if "running in background" in out:
                    notes[b["tool_use_id"]] = (t, cmd)
                    continue
                total += 1
                if b.get("is_error") or re.search(r"exit[ =:]*[1-9]|exited with code [1-9]", out):
                    red.append((t, why_red(out[-3000:]), cmd[:80] + " ⟶ " + re.sub(r"\s+", " ", out[-160:])))
        if o.get("type") in ("user", "queue-operation"):
            raw = json.dumps(o, ensure_ascii=False)
            for m in re.finditer(r"<tool-use-id>(\w+)</tool-use-id>.*?<status>(\w+)</status>", raw):
                if m.group(1) in notes:
                    t, cmd = notes.pop(m.group(1))
                    total += 1
                    if m.group(2) != "completed":
                        red.append((t, "фон: " + ("полная" if "--full" in cmd else "проверка"), cmd[:80]))
    return total, red


FRICTION = {
    "отказ оболочки в рабочем дереве": re.compile(r"Split it into plain, separate commands|without the redirect|its own worktree"),
    "нет инструмента (command not found / npx tsc)": re.compile(r"command not found|This is not the tsc command|No module named"),
    "отказ прав": re.compile(r"Permission to use \w+ has been denied|was denied|requires approval"),
}


def friction(path: str, since: datetime) -> Counter:
    """Вызовы, которые ничего не сделали: отказ оболочки, нет инструмента, нет прав."""
    c: Counter = Counter()
    for o in lines(path):
        t = o.get("timestamp")
        if not t or ts(t) < since:
            continue
        for b in blocks(o):
            if isinstance(b, dict) and b.get("type") == "tool_result":
                out = text_of(b)[:2000]
                for k, rx in FRICTION.items():
                    if rx.search(out):
                        c[k] += 1
                        break
    return c


def runs(session: str, since: datetime):
    base = session[:-6]
    out = []
    for f in glob.glob(base + "/subagents/**/*.jsonl", recursive=True):
        try:
            meta = json.load(open(f[:-6] + ".meta.json"))
        except Exception:
            meta = {}
        first = last = None
        req = set()
        comp = 0
        for o in lines(f):
            t = o.get("timestamp")
            if not t:
                continue
            first = first or t
            last = t
            if o.get("type") == "assistant":
                req.add((o.get("message") or {}).get("id"))
            if o.get("subtype") == "compact_boundary":
                comp += 1
        if not first or ts(first) < since:
            continue
        out.append(dict(type=(meta.get("agentType") or "?").replace("muagba-base:", ""),
                        desc=meta.get("description") or "", start=first,
                        minutes=(ts(last) - ts(first)).total_seconds() / 60,
                        req=len(req), comp=comp, path=f))
    return out


def gaps(session: str, since: datetime):
    """Промежутки координатора и чем они кончились."""
    prev = last_any = None
    human, go, idle = [], 0, []
    for o in lines(session):
        t = o.get("timestamp")
        if not t:
            continue
        now = ts(t)
        if prev and now >= since and now > prev:
            gap = (now - prev).total_seconds() / 60
            if o.get("type") == "user":
                bs = blocks(o)
                content = (o.get("message") or {}).get("content")
                if isinstance(content, str) or any(isinstance(b, dict) and b.get("type") == "text" for b in bs):
                    txt = content if isinstance(content, str) else " ".join(
                        b.get("text", "") for b in bs if isinstance(b, dict) and b.get("type") == "text")
                    if "<task-notification>" in txt or "SYSTEM NOTIFICATION" in txt or "cross-session-message" in txt:
                        g = (now - last_any).total_seconds() / 60 if last_any else 0
                        if g > 2:
                            idle.append(g)
                    elif not o.get("isMeta") and not txt.startswith("<"):
                        human.append(gap)
                        if GO.match(txt):
                            go += 1
        if o.get("type") == "queue-operation" and last_any and (now - last_any).total_seconds() > 120 and now >= since:
            idle.append((now - last_any).total_seconds() / 60)
        if not last_any or now > last_any:
            last_any = now
        if o.get("type") == "assistant":
            prev = now if not prev or now > prev else prev
    return human, go, idle


def med(xs):
    return round(statistics.median(xs), 1) if xs else 0


def report(session: str, since: datetime):
    name = Counter(m.group(1) for line in open(session, errors="replace")
                   for m in re.finditer(r'"agentName":"([^"]*)"', line)).most_common(1)
    print(f"\n=== {name[0][0] if name else os.path.basename(session)}  ({os.path.basename(session)[:8]})")
    rs = runs(session, since)
    by = defaultdict(list)
    for r in rs:
        by[r["type"]].append(r)
    for typ, xs in sorted(by.items(), key=lambda x: -len(x[1])):
        print(f"  {typ:18} {len(xs):3} запусков  медиана {med([x['minutes'] for x in xs]):5} мин, "
              f"{med([x['req'] for x in xs]):5} запросов, уплотнений {sum(x['comp'] for x in xs)}")
    tasks = defaultdict(Counter)
    for r in rs:
        k = task_key(r["desc"])
        if k:
            tasks[k][r["type"]] += 1
    back = {k: v for k, v in tasks.items() if v.get("reviewer", 0) >= 2}
    if tasks:
        impl = [v.get("implementer", 0) + v.get("implementer-deep", 0) for v in tasks.values()]
        print(f"  задач {len(tasks)}; исполнителей на задачу — медиана {med(impl)}; "
              f"вернулись с ревью (≥2 ревью): {len(back)}")
        for k, v in sorted(back.items(), key=lambda x: -sum(x[1].values()))[:5]:
            print(f"    {k}: " + ", ".join(f"{t} ×{n}" for t, n in v.most_common()))
    total, red = 0, []
    for f in [session] + [r["path"] for r in rs]:
        n, rd = checks(f, since)
        total += n
        red += rd
    print(f"  проверок {total}, красных {len(red)}: "
          + ", ".join(f"{k} {n}" for k, n in Counter(r[1] for r in red).most_common()))
    if os.environ.get("MONITOR_RED"):
        for r in red:
            print("     ", r[0][11:16], r[1], "|", r[2][:260])
    fr: Counter = Counter()
    for f in [session] + [r["path"] for r in rs]:
        fr += friction(f, since)
    if fr:
        print("  впустую: " + ", ".join(f"{k} {n}" for k, n in fr.most_common()))
    human, go, idle = gaps(session, since)
    print(f"  ожидание человека: {len(human)} раз, {round(sum(human))} мин; из них «продолжай»/«да» — {go}")
    print(f"  простой координатора в ожидании фона (>2 мин): {len(idle)} раз, {round(sum(idle))} мин")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("sessions", nargs="+")
    a = ap.parse_args()
    since = ts(a.since)
    for s in a.sessions:
        report(s, since)


if __name__ == "__main__":
    main()
