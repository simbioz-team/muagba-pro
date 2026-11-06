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

Ночь — у каждой сессии своя (с 0.22.5). Правила в ~/.claude/settings.json
общие для всех сессий человека, а пометка — у каждой. До 0.22.5 состояние
было одно на машину: вторая сессия того же проекта получала «ночь уже
включена (сессия …). Сначала off», а off первой снимал правила и у всех.
Теперь у каждого добавленного правила — список сессий, которым оно нужно:
  on            сессия добавляет недостающие правила и становится
                владельцем своих; уже добавленные ночью — делит;
  off           снимает пометку этой сессии; правило уходит из настроек,
                когда у него не остаётся сессий;
  off --all     снимает ночь целиком (упавшая ночная сессия иначе держит
                правила до утра).
Правило, бывшее в настройках человека до ночи, ночи не принадлежит и не
убирается никогда.

До 0.21.1 запускал человек (`!` в сессии): правка своих прав агенту
запрещена. Владельцу это мешало каждый вечер и утро, и теперь агент зовёт
её сам через обёртку проекта `.claude/night-switch`. Разрешение на неё —
в `.claude/settings.json` каркаса и в `allowed-tools` скилов night/day.
Разрешение выдаёт человек, а порог остался там же: `on` не включит ночь
без утверждённого им на сегодня, скил — без его «да». Режим `auto`
(Shift+Tab) включает по-прежнему человек.
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


def read_state() -> dict:
    """Состояние ночи. Формат до 0.22.5 — одна сессия и списки добавленного —
    переводится на лету: все правила принадлежат той сессии."""
    st = load(state_dir() / "state.json")
    if not st:
        return {"sessions": {}, "added": {}}
    if "sessions" in st:
        st.setdefault("added", {})
        return st
    sid = st.get("session") or "?"
    return {"sessions": {sid: {k: st.get(k) for k in ("project", "date", "since")}},
            "added": {key: [{"item": x, "sessions": [sid]} for x in items]
                      for key, items in (st.get("added") or {}).items()}}


def write_state(st: dict) -> None:
    if st["sessions"]:
        save(state_dir() / "state.json", st)
    else:
        try:
            (state_dir() / "state.json").unlink()
        except OSError:
            pass


def rules_count(st: dict) -> int:
    return sum(len(v) for v in st["added"].values())


def on(a) -> int:
    loc = locate(a.cwd)
    if not loc.get("launcher"):
        print("night_switch: ночной режим в проекте не настроен — нет .claude/night/settings.json (В9.11).")
        return 1
    if not loc.get("approved_today"):
        print("night_switch: на сегодня нет утверждённого (.claude/night/approved.json) — сначала подготовка.")
        return 1
    st = read_state()
    if a.session in st["sessions"]:
        print(f"night_switch: ночь у этой сессии уже включена (с {st['sessions'][a.session].get('since')}).")
        return 1
    night_dir = Path(loc["approved"]).parent
    from night_rules import merged
    m = merged(load(night_dir / "settings.json"), load(Path(loc["approved"])))
    sp = home() / "settings.json"
    cfg = load(sp)
    state_dir().mkdir(parents=True, exist_ok=True)
    # Копия на случай, если что-то пойдёт не так: off убирает по списку,
    # а не восстанавливает копию — днём настройки могли поменяться. Копия —
    # до первой ночной сессии: у второй в настройках уже ночь.
    if sp.exists() and not st["sessions"]:
        shutil.copyfile(sp, state_dir() / "settings.before.json")
    new_n = 0
    for sect in ("autoMode", "permissions"):
        for field, items in m[sect].items():
            key = f"{sect}.{field}"
            cur = cfg.setdefault(sect, {}).setdefault(field, [])
            owned = st["added"].setdefault(key, [])
            for x in items:
                rec = next((r for r in owned if r["item"] == x), None)
                if rec is not None:
                    if a.session not in rec["sessions"]:
                        rec["sessions"].append(a.session)
                    if x not in cur:  # человек убрал днём — ночи оно нужно
                        cur.append(x)
                elif x not in cur:
                    cur.append(x)
                    owned.append({"item": x, "sessions": [a.session]})
                    new_n += 1
            if not owned:
                st["added"].pop(key)
            if not cur:
                cfg[sect].pop(field)
        if sect in cfg and not cfg[sect]:
            cfg.pop(sect)
    save(sp, cfg)
    today = datetime.date.today().isoformat()
    project = str(night_dir.parent.parent)
    st["sessions"][a.session] = {"project": project, "date": today,
                                 "since": datetime.datetime.now().isoformat(timespec="seconds")}
    write_state(st)
    save(state_dir() / "sessions" / f"{a.session}.json", {"date": today, "project": project})
    others = [s for s in st["sessions"] if s != a.session]
    tail = f" Ночных сессий теперь {len(st['sessions'])}." if others else ""
    print(f"Ночь включена для сессии {a.session}: добавлено {new_n} правил в ~/.claude/settings.json "
          f"(убираются командой off).{tail} Включите режим auto (Shift+Tab), если он ещё не включён.")
    return 0


def off(a) -> int:
    st = read_state()
    if a.all:
        leaving = set(st["sessions"])
    elif a.session in st["sessions"]:
        leaving = {a.session}
    elif len(st["sessions"]) == 1:
        # Ночная сессия одна — off из любой (утро в другой сессии, `!` без
        # номера) снимает её, как до 0.22.5. Чужую из нескольких — только --all.
        leaving = set(st["sessions"])
    else:
        if st["sessions"]:
            print(f"night_switch: у этой сессии ночь не включена. Ночные сессии: "
                  f"{', '.join(st['sessions'])}. Снять ночь у всех — off --all.")
        else:
            print("Ночь не включена.")
        return 0 if not st["sessions"] else 1
    sp = home() / "settings.json"
    cfg = load(sp)
    removed = 0
    for key in list(st["added"]):
        sect, field = key.split(".")
        cur = (cfg.get(sect) or {}).get(field)
        keep = []
        for rec in st["added"][key]:
            rec["sessions"] = [s for s in rec["sessions"] if s not in leaving]
            if rec["sessions"]:
                keep.append(rec)
            elif isinstance(cur, list) and rec["item"] in cur:
                cur.remove(rec["item"])
                removed += 1
        if keep:
            st["added"][key] = keep
        else:
            st["added"].pop(key)
        if isinstance(cur, list) and not cur:
            cfg[sect].pop(field, None)
        if sect in cfg and not cfg[sect]:
            cfg.pop(sect)
    save(sp, cfg)
    for s in leaving:
        st["sessions"].pop(s, None)
        try:
            (state_dir() / "sessions" / f"{s}.json").unlink()
        except OSError:
            pass
    write_state(st)
    left = st["sessions"]
    if left:
        print(f"Ночь выключена для {', '.join(sorted(leaving))}: убрано {removed} правил, пометка снята. "
              f"Ночными остались {', '.join(left)} — их правила ({rules_count(st)}) на месте; "
              "снять у всех — off --all.")
    else:
        print(f"Ночь выключена: убрано {removed} ночных правил, пометка снята. Режим верните по вкусу (Shift+Tab).")
    return 0


def status(a) -> int:
    st = read_state()
    if not st["sessions"]:
        print("Ночь не включена.")
        return 0
    print(f"Ночь включена, ночных сессий: {len(st['sessions'])}, правил в настройках: {rules_count(st)}.")
    for sid, info in st["sessions"].items():
        mark = " (эта)" if sid == a.session else ""
        print(f"  {sid}{mark}: с {info.get('since')}, {info.get('project')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["on", "off", "status"])
    ap.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--all", action="store_true", help="off: снять ночь у всех сессий")
    a = ap.parse_args()
    if a.cmd == "on" and not a.session:
        print("night_switch: нужен --session <id сессии>.")
        return 1
    return {"on": on, "off": off, "status": status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
