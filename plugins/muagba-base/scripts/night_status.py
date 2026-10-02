#!/usr/bin/env python3
"""SessionStart (startup|resume): ночной режим включён — или должен был быть.

Ночь без лаунчера ничем не отличалась от дня: у narta подготовка прошла,
а сессию координатора подняли обычным `claude --resume` — вопросы снова
ждали человека, и никто этого не видел (ADR-0016).

- MUAGBA_MODE=night — напоминание агенту в контекст: человека нет, что
  делать, когда упёрся.
- Не ночь, но утверждённые на сегодня разрешения есть
  (.claude/night/approved.json с сегодняшней датой — в каталоге сессии, в
  основном checkout или в его рабочих деревьях) — предупреждение человеку и
  агенту: подготовка сделана, а ночной режим не действует.
Нет ни того, ни другого — молчит.
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import subprocess
import sys
from pathlib import Path


def approved_today(cwd: Path) -> Path | None:
    roots = [cwd]
    r = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        main = Path(r.stdout.strip()).parent
        roots += [main] + [Path(p) for p in glob.glob(str(main / ".claude" / "worktrees" / "*"))]
    today = datetime.date.today().isoformat()
    for root in dict.fromkeys(roots):
        f = root / ".claude" / "night" / "approved.json"
        try:
            if json.loads(f.read_text(encoding="utf-8")).get("date") == today:
                return f
        except (OSError, ValueError):
            continue
    return None


def main() -> None:
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        inp = {}
    cwd = Path(inp.get("cwd") or os.getcwd())
    if os.environ.get("MUAGBA_MODE") == "night":
        print("Ночной режим (ADR-0016): человека нет до утра. Всё, что требует его, — вопрос или "
              "действие сверх утверждённого на подготовке, — получит отказ и попадёт в "
              ".claude/logs/morning.md. Не жди и не обходи: обратимое реши по умолчанию со "
              "«Спросить: да», необратимое отложи и бери следующую независимую задачу.")
        return
    f = approved_today(cwd)
    if f:
        msg = (f"Подготовка к ночи на сегодня есть ({f}), но эта сессия запущена без лаунчера — "
               "ночной режим НЕ действует: вопросы и подтверждения будут ждать человека. "
               "Ночь запускается в терминале командой .claude/claude-night [--resume <сессия>], "
               "не через ! и не сообщением агенту.")
        print(json.dumps({"systemMessage": msg,
                          "hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": msg}}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
