#!/usr/bin/env python3
"""Утренний отчёт ночного прогона (ADR-0016).

Источники:
- `.claude/logs/morning.md` — что агенты отложили человеку: вопросы
  целиком и действия, требовавшие разрешения (пишет хук log-wait.sh в
  ночном режиме);
- `.claude/logs/agents.jsonl` — события night_deferred, gate, запуски
  агентов;
- стенограммы сессий проекта (~/.claude/projects/<проект>/ и его рабочих
  деревьев), основные и сабагентов, — отказы контролёра (режим auto):
  результат инструмента с «denied by the Claude Code auto mode
  classifier». Одобрения контролёра в стенограмме не видны;
- коммиты ночи во всех ветках — добавленные строки с «Спросить: да»:
  решения, принятые агентом по умолчанию. Координатор пишет их в журнал и
  в спеку, а не в morning.md; у narta утром 22.10 отчёт показал «ничего»,
  хотя за ночь таких решений было больше десятка, а morning.md координатор
  уже перенёс в журнал и очистил.

Логи — из основного checkout'а (туда пишут хуки), даже если отчёт
запущен из рабочего дерева.

Запуск: python3 night_report.py [--cwd КАТАЛОГ] [--since ISO] [--hours 16]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

DENIED = re.compile(r"denied by the Claude Code auto mode classifier\.?\s*(?:Reason:\s*([^\n.]*))?", re.I)


def ts(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.astimezone()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--since")
    ap.add_argument("--hours", type=float, default=16)
    ap.add_argument("--transcripts")
    o = ap.parse_args()
    root = Path(o.cwd).resolve()
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip().endswith("/.git"):
        root = Path(r.stdout.strip()).parent
    since = ts(o.since) or (dt.datetime.now().astimezone() - dt.timedelta(hours=o.hours))
    L = [f"# Утро после ночи — с {since:%Y-%m-%d %H:%M}", ""]

    morning = root / ".claude" / "logs" / "morning.md"
    text = morning.read_text(encoding="utf-8") if morning.exists() else ""
    L += ["## Отложено человеку", ""]
    L += [text.rstrip() or "Ничего: ни одного вопроса и ни одного действия, ждавшего человека.", ""]

    asked = []
    r = subprocess.run(["git", "-C", str(root), "log", "--all", f"--since={since.isoformat()}",
                        "-p", "-U0", "--format=@@commit %h"], capture_output=True, text=True, errors="replace")
    commit = ""
    for line in r.stdout.splitlines() if r.returncode == 0 else []:
        if line.startswith("@@commit "):
            commit = line.split()[1]
        elif line.startswith("+") and not line.startswith("+++") and "Спросить: да" in line:
            item = line[1:].strip().lstrip("-* ").strip()
            # Строки таблиц — реестры документов (INDEX/TAGS), а не решения.
            if item.startswith("|"):
                continue
            if item and item not in (a for _, a in asked):
                asked.append((commit, item))
    L += ["## Решено по умолчанию (Спросить: да)", ""]
    L += [f"- {a[:300]}{'…' if len(a) > 300 else ''} ({c})" for c, a in asked[:60]] or \
         ["Нет: ни одной строки «Спросить: да» в коммитах ночи."]
    if len(asked) > 60:
        L += [f"- … ещё {len(asked) - 60}: git log --all -p --since=… | grep «Спросить: да»"]
    L += [""]

    ev = []
    log = root / ".claude" / "logs" / "agents.jsonl"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            t = ts(e.get("ts"))
            if t and t >= since:
                ev.append(e)
    deferred = Counter(f"{e.get('tool')}: {e.get('class')}" for e in ev if e.get("event") == "night_deferred")
    gates = Counter(e.get("decision") for e in ev if e.get("event") == "gate")
    started = sum(1 for e in ev if e.get("event") == "SubagentStart")

    slug = re.sub(r"[^A-Za-z0-9]", "-", str(root))
    tdir = Path(o.transcripts) if o.transcripts else Path.home() / ".claude" / "projects" / slug
    denials: Counter = Counter()
    merges = 0
    tdirs = [tdir] if o.transcripts else [tdir] + [Path(d) for d in glob.glob(str(tdir) + "--claude-worktrees-*")]
    files = []
    for d in tdirs:
        files += glob.glob(str(d / "*.jsonl")) + glob.glob(str(d / "*" / "subagents" / "**" / "*.jsonl"), recursive=True)
    for f in files:
        try:
            lines = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in lines:
            if "auto mode classifier" not in line and "pr merge" not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            t = ts(e.get("timestamp"))
            if not t or t < since:
                continue
            content = (e.get("message") or {}).get("content")
            for b in content if isinstance(content, list) else []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_result":
                    m = DENIED.search(json.dumps(b.get("content"), ensure_ascii=False))
                    if m:
                        denials[(m.group(1) or "без причины").strip(" []")] += 1
                if b.get("type") == "tool_use" and b.get("name") == "Bash" \
                        and re.search(r"\bgh\b.*\bpr\s+merge\b", str((b.get("input") or {}).get("command"))):
                    merges += 1

    L += ["## Отказы контролёра", ""]
    L += [f"- {k} — {v}" for k, v in denials.most_common()] or ["Нет."]
    L += ["", "Каждый отказ — либо верно остановленное, либо разрешение, которое стоило "
               "утвердить на подготовке. Второе — в следующую подготовку.", ""]
    L += ["## Ночь в цифрах", "",
          f"- запусков агентов: {started}",
          f"- слияний PR: {merges}",
          f"- отложено до человека: {sum(deferred.values())}"
          + (" (" + ", ".join(f"{k} ×{v}" for k, v in deferred.most_common()) + ")" if deferred else ""),
          f"- гейт хода: " + (", ".join(f"{k} ×{v}" for k, v in gates.items()) or "не срабатывал с красным"),
          ""]
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
