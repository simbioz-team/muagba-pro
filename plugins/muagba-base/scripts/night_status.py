#!/usr/bin/env python3
"""SessionStart (startup|resume): ночной режим включён — или должен был быть.

Ночь без лаунчера ничем не отличалась от дня: у narta подготовка прошла,
а сессию координатора подняли обычным `claude --resume` — вопросы снова
ждали человека, и никто этого не видел (ADR-0016).

- MUAGBA_MODE=night — напоминание агенту в контекст: человека нет, что
  делать, когда упёрся.
- Пометка ночи сессии (~/.claude/muagba-night/sessions/<id>.json) у
  сессии, поднятой не лаунчером, снимается: ночь ушла перезапуском.
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
    sid = str(inp.get("session_id") or "")
    nd = Path(os.path.expanduser("~")) / ".claude" / "muagba-night"
    flag = nd / "sessions" / f"{sid}.json" if sid else None
    try:
        fd = json.loads(flag.read_text(encoding="utf-8")) if flag else None
    except (OSError, ValueError):
        fd = {} if flag and flag.exists() else None
    night = os.environ.get("MUAGBA_MODE") == "night"
    if fd is not None:
        # Пометка живёт, пока жив ночной процесс. Сессия поднята не
        # лаунчером — ночь ушла перезапуском. Лаунчер старше 0.22.6 пометку
        # не ставит, и закрытая утром прошлой ночи досталась бы этой ночи:
        # закрытая до начала ночи — старая.
        stale = not night
        if night and fd.get("ended"):
            try:
                start = datetime.datetime.fromisoformat(os.environ.get("MUAGBA_NIGHT_START", "")).timestamp()
            except ValueError:
                start = 0
            stale = float(fd.get("ended_ts") or 0) < start
        if stale:
            try:
                flag.unlink()
            except OSError:
                pass
            fd = None
    if night and not (fd or {}).get("ended"):
        print("Ночной режим (ADR-0016): человека нет до утра. Всё, что требует его, — вопрос или "
              "действие сверх утверждённого на подготовке, — получит отказ и попадёт в "
              ".claude/logs/morning.md. Не жди и не обходи: обратимое реши по умолчанию со "
              "«Спросить: да», необратимое отложи и бери следующую независимую задачу.")
        return
    # Остатки ночи в той же сессии (до 0.22.6): правила в пользовательских
    # настройках, их видят все сессии в auto.
    try:
        st = json.loads((nd / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    # Формат до 0.22.5 — одна сессия в корне состояния.
    sessions = st.get("sessions") or ({st["session"]: st} if st.get("added") and st.get("session") else {})
    if sessions:
        who = "; ".join(f"сессия {sid} с {i.get('since')}, проект {i.get('project')}"
                        for sid, i in sessions.items())
        msg = (f"В ~/.claude/settings.json остались ночные правила старой схемы ({who}). Убрать — "
               "./.claude/night-switch off: правила видят все сессии в режиме auto.")
        print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": msg}}, ensure_ascii=False))
        return
    f = approved_today(cwd)
    if f:
        msg = (f"Подготовка к ночи на сегодня есть ({f}), но эта сессия запущена без лаунчера — "
               "ночной режим НЕ действует: вопросы и подтверждения будут ждать человека. "
               "Начать ночь этой сессии — /muagba-base:night.")
        print(json.dumps({"systemMessage": msg,
                          "hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": msg}}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
