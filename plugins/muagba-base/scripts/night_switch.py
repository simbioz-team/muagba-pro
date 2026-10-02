#!/usr/bin/env python3
"""Ночь в текущей сессии, в том же терминале (ADR-0016, дополнение).

Работающая сессия не может сменить то, с чем её запустили, но Claude Code
подхватывает изменения настроек на ходу. Правила контролёра (`autoMode`)
он берёт только из пользовательских настроек, управляемых и файла
`--settings`, проектные игнорирует. Поэтому ночь в той же сессии — это:

  on   дописать в ~/.claude/settings.json ночные правила проекта
       (.claude/night/settings.json) и утверждённое на сегодня
       (.claude/night/approved.json); поставить пометку ночи для сессии —
       ~/.claude/muagba-night/sessions/<id>. Хуки базы по ней отвечают
       отказом вместо вопроса;
  off  убрать ровно добавленное (список — в state.json) и пометку;
  status  что включено.

Запускает человек (`!` в сессии): правка своих прав агенту запрещена, и
правильно. Режим `auto` (Shift+Tab) включает тоже человек.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def home() -> Path:
    return Path(os.path.expanduser("~")) / ".claude"


def state_dir() -> Path:
    return home() / "muagba-night"


def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def locate(cwd: str) -> dict:
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("night_locate.py")), cwd],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}


def on(a) -> int:
    loc = locate(a.cwd)
    if not loc.get("launcher"):
        print("night_switch: ночной режим в проекте не настроен — нет .claude/night/settings.json (В9.11).")
        return 1
    if not loc.get("approved_today"):
        print("night_switch: на сегодня нет утверждённого (.claude/night/approved.json) — сначала подготовка.")
        return 1
    st = load(state_dir() / "state.json")
    if st.get("added"):
        print(f"night_switch: ночь уже включена (сессия {st.get('session')}). Сначала off.")
        return 1
    night_dir = Path(loc["approved"]).parent
    rules = load(night_dir / "settings.json")
    appr = load(Path(loc["approved"]))
    am = rules.get("autoMode") or {}
    add = {
        "autoMode.environment": list(am.get("environment") or []),
        "autoMode.allow": list(am.get("allow") or []) + list(appr.get("allow_rules") or []),
        "autoMode.soft_deny": list(am.get("soft_deny") or []),
        "autoMode.hard_deny": list(am.get("hard_deny") or []),
        "permissions.allow": list(appr.get("allow_commands") or []),
        "permissions.deny": list((rules.get("permissions") or {}).get("deny") or []),
    }
    sp = home() / "settings.json"
    cfg = load(sp)
    # Копия на случай, если что-то пойдёт не так: off убирает по списку,
    # а не восстанавливает копию — днём настройки могли поменяться.
    state_dir().mkdir(parents=True, exist_ok=True)
    if sp.exists():
        shutil.copyfile(sp, state_dir() / "settings.before.json")
    added: dict[str, list] = {}
    for key, items in add.items():
        sect, field = key.split(".")
        cur = cfg.setdefault(sect, {}).setdefault(field, [])
        new = [x for x in items if x not in cur]
        cur.extend(new)
        added[key] = new
    save(sp, cfg)
    today = datetime.date.today().isoformat()
    save(state_dir() / "state.json", {"session": a.session, "project": str(night_dir.parent.parent),
                                      "date": today, "since": datetime.datetime.now().isoformat(timespec="seconds"),
                                      "added": added})
    save(state_dir() / "sessions" / f"{a.session}.json", {"date": today, "project": str(night_dir.parent.parent)})
    n = sum(len(v) for v in added.values())
    print(f"Ночь включена для сессии {a.session}: добавлено {n} правил в ~/.claude/settings.json "
          f"(убираются командой off). Включите режим auto (Shift+Tab), если он ещё не включён.")
    return 0


def off(a) -> int:
    st = load(state_dir() / "state.json")
    sp = home() / "settings.json"
    cfg = load(sp)
    removed = 0
    for key, items in (st.get("added") or {}).items():
        sect, field = key.split(".")
        cur = (cfg.get(sect) or {}).get(field)
        if isinstance(cur, list):
            for x in items:
                if x in cur:
                    cur.remove(x)
                    removed += 1
            if not cur:
                cfg[sect].pop(field, None)
        if sect in cfg and not cfg[sect]:
            cfg.pop(sect)
    if st:
        save(sp, cfg)
    sess = a.session or st.get("session")
    for s in {sess, st.get("session")} - {None}:
        try:
            (state_dir() / "sessions" / f"{s}.json").unlink()
        except OSError:
            pass
    try:
        (state_dir() / "state.json").unlink()
    except OSError:
        pass
    print(f"Ночь выключена: убрано {removed} ночных правил, пометка снята. Режим верните по вкусу (Shift+Tab).")
    return 0


def status(a) -> int:
    st = load(state_dir() / "state.json")
    if not st:
        print("Ночь не включена.")
        return 0
    n = sum(len(v) for v in (st.get("added") or {}).values())
    print(f"Ночь включена с {st.get('since')} для сессии {st.get('session')} ({st.get('project')}): {n} правил.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["on", "off", "status"])
    ap.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    ap.add_argument("--cwd", default=os.getcwd())
    a = ap.parse_args()
    if a.cmd == "on" and not a.session:
        print("night_switch: нужен --session <id сессии>.")
        return 1
    return {"on": on, "off": off, "status": status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
