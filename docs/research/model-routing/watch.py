#!/usr/bin/env python3
"""Стало ли дешевле: окно «после» против недели «до» по стенограммам Claude Code.

  watch.py --since 2026-11-20T10:00Z [--base-from 2026-11-13T00:00Z]

Цены — API (за 1 млн токенов: ввод, вывод, запись 5 мин, запись 1 ч, чтение).
Лимит подписки считается иначе, но доли и отношения переносятся.

Нормировка — на активный час: 10-минутные отрезки, в которых был хоть один
запрос. Объём работы до и после разный, сырые доллары не сравнимы.

Второе мерило — **цена сделанной задачи** по проекту: весь расход проекта в
окне (координатор и субагенты, все сессии) делится на задачи, сделанные в
окне. Что считать сделанным, видно по git проекта, по всем веткам:

- есть `specs/*/tasks.md` — отметки `- [x]`, первое появление каждой задачи;
- нет — влитые ветки задач: коммиты слияния `Merge <ветка>…`, кроме слияния
  основной ветки внутрь.

Карточки Narta не годятся: одна карточка — несколько этапов за дни, а «на
проверку» сессии переводят её редко. Задачи, закоммиченные без слияния и без
отметки, не видны — цена задачи у такого проекта завышена.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone

P = {"opus": (4, 20, 5, 8, .2), "sonnet": (2, 10, 2.5, 4, .1),
     "haiku": (.1, .5, .125, .2, .01), "fable": (10, 50, 12.5, 20, .5)}
ROOT = os.path.expanduser("~/.claude/projects")


def fam(m: str | None) -> str:
    for k in P:
        if k in (m or ""):
            return k
    return "opus"


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def requests(path: str):
    """(время, модель, usage) по одному на запрос: строки одного ответа повторяют id."""
    seen = {}
    for line in open(path, errors="replace"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        m = o.get("message") if o.get("type") == "assistant" else None
        if isinstance(m, dict) and m.get("usage") and o.get("timestamp"):
            if "synthetic" in (m.get("model") or ""):
                continue
            seen[m.get("id")] = (ts(o["timestamp"]), m.get("model"), m["usage"])
    return list(seen.values())


def cost(model, u) -> tuple[float, float, int]:
    """Цена запроса, переплата за перезапись кэша (запись сверх чтения), вывод."""
    p = P[fam(model)]
    cc = u.get("cache_creation") or {}
    c1 = cc.get("ephemeral_1h_input_tokens", 0)
    c5 = u.get("cache_creation_input_tokens", 0) - c1
    total = (u.get("input_tokens", 0) * p[0] + u.get("output_tokens", 0) * p[1]
             + c5 * p[2] + c1 * p[3] + u.get("cache_read_input_tokens", 0) * p[4]) / 1e6
    over = ((c5 * (p[2] - p[4]) + c1 * (p[3] - p[4])) / 1e6) if c5 + c1 > 20_000 else 0.0
    return total, over, u.get("output_tokens", 0)


def project(d: str) -> str:
    """Каталог стенограмм → проект: сессии рабочих деревьев — к своему проекту."""
    return os.path.basename(d).split("--claude-worktrees-")[0].replace("-home-rustam-develop-simbioz-team-", "")


def repo_of(d: str) -> str | None:
    for f in glob.glob(d + "/*.jsonl"):
        for line in open(f, errors="replace"):
            m = re.search(r'"cwd":"([^"]+)"', line)
            if not m:
                continue
            try:
                g = subprocess.run(["git", "-C", m.group(1), "rev-parse", "--path-format=absolute",
                                    "--git-common-dir"], capture_output=True, text=True, timeout=5).stdout.strip()
            except Exception:
                g = ""
            if g:
                return os.path.dirname(g)
            break
    return None


def done_tasks(top: str, start: datetime, end: datetime, how: str | None = None) -> tuple[int, str]:
    """Сколько задач сделано в [start, end) и по какому следу.

    След выбирается один на проект для обоих окон (`how`), иначе до и после
    несравнимы: у наставника tasks.md есть, но задачи ведутся слияниями.
    """
    if how is None:
        a, _ = done_tasks(top, start, end, "tasks.md")
        b, _ = done_tasks(top, start, end, "слияния")
        how = "tasks.md" if a >= b else "слияния"
    def git(*a):
        try:
            return subprocess.run(["git", "-C", top, *a], capture_output=True, text=True, timeout=120).stdout
        except Exception:
            return ""
    if how == "tasks.md":
        first: dict[str, datetime] = {}
        t = path = None
        for line in git("log", "--all", "--format=@@%cI", "-p", "--", "specs/*/tasks.md").splitlines():
            if line.startswith("@@") and not line.startswith("@@ "):
                t = ts(line[2:])
            elif line.startswith("+++ b/"):
                path = line[6:]
            else:
                m = re.match(r"^\+\s*[-*] \[[xX]\]\s*(\S+)", line)
                if m and t:
                    k = f"{path}:{m.group(1)}"
                    first[k] = min(first.get(k, t), t)
        return sum(1 for v in first.values() if start <= v < end), "tasks.md"
    n = 0
    for line in git("log", "--all", "--merges", "--format=%cI %s").splitlines():
        when, _, subj = line.partition(" ")
        if not subj.startswith("Merge ") or re.search(r"branch '(main|master)'|origin/|remote-tracking", subj):
            continue
        if start <= ts(when) < end:
            n += 1
    return n, "слияния"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--base-from", default="2026-11-13T00:00Z")
    a = ap.parse_args()
    since, base_from = ts(a.since), ts(a.base_from)
    now = datetime.now(timezone.utc)

    W = {w: defaultdict(float) for w in ("до", "после")}
    buckets = {w: set() for w in W}
    runs = {w: [] for w in W}  # (тип, модель, цена, запросы)

    def window(t):
        return "после" if t >= since else ("до" if t >= base_from else None)

    spent = {w: defaultdict(float) for w in W}  # проект → $
    repos: dict[str, str | None] = {}
    for d in glob.glob(ROOT + "/-home-rustam-develop-simbioz-team-*"):
        # Ключ — репозиторий: каталоги стенограмм рабочих деревьев одного проекта
        # сходятся в один, иначе его задачи посчитались бы дважды.
        top = repo_of(d)
        pr = os.path.basename(top) if top else project(d)
        repos.setdefault(pr, top)
        for f in glob.glob(d + "/*.jsonl"):
            if os.path.getmtime(f) < base_from.timestamp():
                continue
            for t, mo, u in requests(f):
                w = window(t)
                if not w:
                    continue
                c, over, out = cost(mo, u)
                W[w]["коорд $"] += c
                spent[w][pr] += c
                W[w]["коорд вывод"] += out
                W[w]["коорд запросов"] += 1
                buckets[w].add(int(t.timestamp() // 600))
        for f in glob.glob(d + "/*/subagents/**/*.jsonl", recursive=True):
            if os.path.getmtime(f) < base_from.timestamp():
                continue
            rq = requests(f)
            if not rq:
                continue
            w = window(min(r[0] for r in rq))
            if not w:
                continue
            try:
                meta = json.load(open(f[:-6] + ".meta.json"))
            except Exception:
                meta = {}
            total = over_sum = 0.0
            models = defaultdict(float)
            for t, mo, u in rq:
                c, over, _ = cost(mo, u)
                total += c
                over_sum += over
                models[fam(mo)] += c
                buckets[w].add(int(t.timestamp() // 600))
            W[w]["суб $"] += total
            spent[w][pr] += total
            W[w]["суб перезапись кэша $"] += over_sum
            for k, v in models.items():
                W[w][f"суб {k} $"] += v
            typ = meta.get("agentType") or "?"
            runs[w].append((typ, total, len(rq)))
            if typ == "general-purpose":
                W[w]["суб general-purpose $"] += total

    rows = []
    for w in W:
        h = max(len(buckets[w]) / 6, 1e-9)
        s = W[w]
        n = len(runs[w]) or 1
        rows.append((w, {
            "активных часов": round(len(buckets[w]) / 6, 1),
            "всего $/час": round((s["коорд $"] + s["суб $"]) / h, 1),
            "координатор $/час": round(s["коорд $"] / h, 1),
            "субагенты $/час": round(s["суб $"] / h, 1),
            "запусков субагентов": len(runs[w]),
            "$ за запуск": round(s["суб $"] / n, 2),
            "запросов на запуск": round(sum(r[2] for r in runs[w]) / n),
            "доля Sonnet в субагентах": f'{100 * s["суб sonnet $"] / max(s["суб $"], 1e-9):.0f}%',
            "доля general-purpose": f'{100 * s["суб general-purpose $"] / max(s["суб $"], 1e-9):.0f}%',
            "перезапись кэша $/час": round(s["суб перезапись кэша $"] / h, 1),
            "вывод координатора на запрос": round(s["коорд вывод"] / max(s["коорд запросов"], 1)),
        }))
    keys = list(rows[0][1])
    print(f"окно «после»: с {since:%d.%m %H:%M}Z по {now:%d.%m %H:%M}Z")
    print(f"{'':32} {'до':>10} {'после':>10}")
    for k in keys:
        print(f"{k:32} {str(rows[0][1][k]):>10} {str(rows[1][1][k]):>10}")
    by = defaultdict(lambda: [0, 0.0])
    for typ, c, _ in runs["после"]:
        by[typ][0] += 1
        by[typ][1] += c
    if by:
        print("\nпосле, по ролям:")
        for typ, (k, c) in sorted(by.items(), key=lambda x: -x[1][1]):
            print(f"  {typ:32} {k:3} запусков  ${c:7.2f}")


    ends = {"до": (base_from, since), "после": (since, now)}
    lines = []
    tot = {w: [0.0, 0] for w in W}
    for pr in sorted(set(spent["до"]) | set(spent["после"]), key=lambda p: -spent["после"].get(p, 0)):
        top = repos.get(pr)
        if not top:
            continue
        cells = []
        _, src = done_tasks(top, base_from, now)
        for w in W:
            n, _ = done_tasks(top, *ends[w], src)
            c = spent[w].get(pr, 0.0)
            if n:
                tot[w][0] += c
                tot[w][1] += n
            cells.append(f"{n:3} за ${c:7.0f} → " + (f"${c / n:6.1f}" if n else "     —"))
        if any(spent[w].get(pr, 0) > 1 for w in W):
            lines.append(f"  {pr:22} {cells[0]}   {cells[1]}   ({src})")
    if lines:
        print("\nцена сделанной задачи (задач · расход проекта → $ на задачу):")
        print(f"  {'':22} {'до':^27}   {'после':^27}")
        print("\n".join(lines))
        print("  " + f"{'всего, где задачи есть':22} "
              + "   ".join(f"{tot[w][1]:3} за ${tot[w][0]:7.0f} → "
                           + (f"${tot[w][0] / tot[w][1]:6.1f}" if tot[w][1] else "     —") for w in W))


if __name__ == "__main__":
    main()
