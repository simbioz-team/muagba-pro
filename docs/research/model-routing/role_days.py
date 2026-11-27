#!/usr/bin/env python3
"""Расход по ролям субагентов: всего и медиана на задачу, вчера против сегодня.

  role_days.py [--since 2026-11-20T10:00Z] [--today ГГГГ-ММ-ДД]

Столбцы:
- «всего» — весь расход роли с --since (как в watch.py);
- «вчера» и «сегодня» — медиана расхода роли на одну задачу за сутки:
  запуски роли за сутки складываются по задаче, медиана берётся по задачам;
- «Δ» — изменение медианы сегодня к вчера, в процентах.

Задача — номер в описании запуска (T1234, T-2240, С9-T4, Е9-2, ЕК-3, Н-2)
и проект.
Запуски без номера в медиану не идут, их доля печатается отдельно: у них
нет задачи, к которой отнести расход. Сутки — по локальному времени машины.
Цены и разбор стенограмм — из watch.py.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import watch  # noqa: E402

# Серия с номером внутри (С9-T4, С1-T7a, Е9-2) — раньше простого T1234:
# иначе С9-T4 и С1-T4 слились бы в одну задачу «T4».
TASK = re.compile(r"(?<![\w-])(?:([А-ЯЁA-Z]\d+-(?:T\d+[a-zа-яё]?|\d+))|T-?(\d+[а-яё]?)|(ЕК-\d+)|(Н-\d+))")
ROLE_PREFIX = "muagba-base:"


def task_of(desc: str) -> str | None:
    m = TASK.search(desc or "")
    if not m:
        return None
    if m.group(1):
        return m.group(1).upper()
    return "T" + m.group(2) if m.group(2) else (m.group(3) or m.group(4)).upper()


def fmt_money(x: float | None) -> str:
    return "—" if x is None else f"${x:,.2f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", default="2026-11-20T10:00Z")
    ap.add_argument("--today", help="какие сутки считать сегодняшними (по умолчанию — сегодня)")
    a = ap.parse_args()
    since = watch.ts(a.since)
    today = date.fromisoformat(a.today) if a.today else datetime.now().astimezone().date()
    yesterday = today - timedelta(days=1)

    total = defaultdict(float)                       # роль → $
    per_day = defaultdict(lambda: defaultdict(float))  # (роль, сутки) → задача → $
    untagged = defaultdict(lambda: [0, 0])           # роль → [без номера, всего] за двое суток

    for d in glob.glob(watch.ROOT + "/-home-rustam-develop-simbioz-team-*"):
        pr = watch.project(d)
        for f in glob.glob(d + "/*/subagents/**/*.jsonl", recursive=True):
            if os.path.getmtime(f) < since.timestamp():
                continue
            rq = watch.requests(f)
            if not rq:
                continue
            start = min(r[0] for r in rq)
            if start < since:
                continue
            try:
                meta = json.load(open(f[:-6] + ".meta.json"))
            except Exception:
                meta = {}
            role = (meta.get("agentType") or "?").removeprefix(ROLE_PREFIX)
            c = sum(watch.cost(mo, u)[0] for _, mo, u in rq)
            total[role] += c
            day = start.astimezone().date()
            if day not in (today, yesterday):
                continue
            t = task_of(meta.get("description", ""))
            untagged[role][1] += 1
            if t is None:
                untagged[role][0] += 1
                continue
            per_day[(role, day)][(pr, t)] += c

    def med(role: str, day: date) -> tuple[float | None, int]:
        v = list(per_day[(role, day)].values())
        return (statistics.median(v) if v else None), len(v)

    print(f"Роли с {a.since}; медиана на задачу: вчера {yesterday:%d.%m}, сегодня {today:%d.%m} "
          f"(локальное время)\n")
    head = f"{'Роль':<18} {'всего':>10} {'вчера':>9} {'задач':>5} {'сегодня':>9} {'задач':>5} {'Δ':>7}"
    print(head)
    print("-" * len(head))
    for role in sorted(total, key=total.get, reverse=True):
        y, ny = med(role, yesterday)
        t, nt = med(role, today)
        delta = f"{(t - y) / y * 100:+.0f}%" if y and t is not None else "—"
        print(f"{role:<18} {fmt_money(total[role]):>10} {fmt_money(y):>9} {ny:>5} "
              f"{fmt_money(t):>9} {nt:>5} {delta:>7}")
    miss = {r: v for r, v in untagged.items() if v[0]}
    if miss:
        print("\nБез номера задачи (в медиану не вошли), за двое суток: "
              + ", ".join(f"{r} {v[0]} из {v[1]}" for r, v in sorted(miss.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
