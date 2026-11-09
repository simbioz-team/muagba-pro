#!/usr/bin/env python3
"""Ночь конкретной сессии (ADR-0016, дополнение 2026-11-09).

Ночь — это процесс Claude, запущенный лаунчером `.claude/claude-night`:
правила контролёра режима `auto` он получает через `--settings` и видит их
только он, а `MUAGBA_MODE=night` в его окружении говорит хукам, что
человека нет. Другие сессии человека ночи не получают. Снять правила
контролёра с работающего процесса нельзя — только перезапуском.

Пометка сессии — ~/.claude/muagba-night/sessions/<id>.json. Её ставит
лаунчер (`mark`): по ней видно, какие сессии ночные, и по ней утро
выключает хуки, не дожидаясь перезапуска (`ended`). Хук считает сессию
ночной, когда в окружении `MUAGBA_MODE=night`, а пометка не закрыта.

  on      проверить, что ночь можно начать (настроена, утверждено на
          сегодня), и выдать человеку строки запуска: /exit и лаунчер
          с --resume этой сессии;
  mark    (зовёт лаунчер) поставить пометку ночи сессии;
  off     утро: закрыть пометку этой сессии — вопросы снова идут к
          человеку; ночные разрешения уходят перезапуском, строку для
          него выдаёт тут же. Эта сессия не ночная, а ночная одна —
          закрыть её; несколько — назвать их, закрыть все — off --all;
  status  какие сессии ночные.

До 0.22.6 ночь включалась и в той же сессии: `on` дописывал правила в
~/.claude/settings.json, и их видели все сессии человека в `auto`, а ночь,
поднятая лаунчером, для `off` не существовала — «Ночь не включена» у
сессии, которая всё ещё ночная (narta, 09.11). Остатки той схемы
(state.json и правила в настройках) `off` убирает.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def home() -> Path:
    return Path(os.path.expanduser("~")) / ".claude"


def state_dir() -> Path:
    return home() / "muagba-night"


def flag_path(sid: str) -> Path:
    return state_dir() / "sessions" / f"{sid}.json"


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


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def locate(cwd: str) -> dict:
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("night_locate.py")), cwd],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}


def env_night() -> bool:
    return os.environ.get("MUAGBA_MODE") == "night"


def night_flags() -> dict:
    """Открытые пометки: сессии, у которых ночь идёт (или упавшие ночью)."""
    out = {}
    for p in sorted((state_dir() / "sessions").glob("*.json")):
        d = load(p)
        if not d.get("ended"):
            out[p.stem] = d
    return out


def resume_line(sid: str, info: dict) -> str:
    where = info.get("cwd") or info.get("project")
    return (f"cd {where} && " if where else "") + f"claude --resume {sid}"


def legacy_cleanup() -> int:
    """Ночь в той же сессии (до 0.22.6): убрать её правила из настроек
    человека по state.json и её пометки. Правило, бывшее у человека до
    ночи, в state.json не записано и не трогается."""
    st = load(state_dir() / "state.json")
    if not st:
        return 0
    if "sessions" not in st:  # формат до 0.22.5
        sid = st.get("session") or "?"
        st = {"sessions": {sid: {}}, "added": {k: [{"item": x} for x in v]
                                               for k, v in (st.get("added") or {}).items()}}
    sp = home() / "settings.json"
    cfg = load(sp)
    removed = 0
    for key, recs in (st.get("added") or {}).items():
        sect, field = key.split(".")
        cur = (cfg.get(sect) or {}).get(field)
        for rec in recs:
            if isinstance(cur, list) and rec.get("item") in cur:
                cur.remove(rec["item"])
                removed += 1
        if isinstance(cur, list) and not cur:
            cfg[sect].pop(field, None)
        if sect in cfg and not cfg[sect]:
            cfg.pop(sect)
    if sp.exists():
        save(sp, cfg)
    for sid in st.get("sessions") or {}:
        try:
            flag_path(sid).unlink()
        except OSError:
            pass
    try:
        (state_dir() / "state.json").unlink()
    except OSError:
        pass
    return removed


def on(a) -> int:
    if env_night() and not load(flag_path(a.session)).get("ended"):
        print("night_switch: эта сессия уже ночная — её запустил лаунчер.")
        return 1
    loc = locate(a.cwd)
    if not loc.get("launcher"):
        print("night_switch: ночной режим в проекте не настроен — нет .claude/night/settings.json (В9.11).")
        return 1
    approved = Path(a.approved).resolve() if a.approved else Path(loc["approved"])
    if load(approved).get("date") != datetime.date.today().isoformat():
        print(f"night_switch: в {approved} нет утверждённого на сегодня — сначала подготовка.")
        return 1
    print(f"Ночь для сессии {a.session} готова. Она стартует перезапуском этой сессии лаунчером —\n"
          "только так ночные правила действуют в ней одной. Человеку, по порядку:\n"
          "  1. закрыть эту сессию: /exit\n"
          f"  2. в терминале: {loc['launcher']} --yes --approved {approved} --resume {a.session}\n"
          "Ночь продолжит эту же сессию по утверждённому плану. Утром — /muagba-base:day.")
    return 0


def mark(a) -> int:
    save(flag_path(a.session), {"date": datetime.date.today().isoformat(), "since": now(),
                                "project": a.project or a.cwd, "cwd": a.cwd,
                                "approved": a.approved, "via": "launcher"})
    return 0


def end(sid: str, info: dict) -> None:
    info = dict(info)
    info.update({"ended": now(), "ended_ts": time.time()})
    save(flag_path(sid), info)


def off(a) -> int:
    legacy = legacy_cleanup()
    tail = f" Убраны ночные правила старой схемы из ~/.claude/settings.json: {legacy}." if legacy else ""
    flags = night_flags()
    me = a.session
    mine = env_night() and not load(flag_path(me)).get("ended") if me else False
    if env_night() and not mine and not a.all:
        # Эта сессия — ночь лаунчера, уже снятая утром: снимать нечего, а
        # чужую ночную трогать по ошибке не надо.
        others = f" Ночные сессии: {', '.join(flags)} — off --all закроет и их." if flags else ""
        print("Ночь этой сессии уже снята: вопросы идут к человеку. Ночные разрешения "
              f"контролёра уйдут перезапуском: /exit, затем {resume_line(me, {'cwd': a.cwd})}."
              + others + tail)
        return 0
    if a.all:
        leaving = dict(flags)
        if mine:
            leaving.setdefault(me, load(flag_path(me)) or {"cwd": a.cwd})
    elif mine:
        leaving = {me: flags.get(me) or {"cwd": a.cwd}}
    elif me in flags or len(flags) == 1:
        # Пометка без ночного окружения — эта сессия поднята не лаунчером
        # (ночь уже ушла перезапуском) или упала ночью; ночная одна — утро
        # в другой сессии снимает её, как до 0.22.5.
        leaving = {me: flags[me]} if me in flags else dict(flags)
    elif flags:
        print("night_switch: эта сессия не ночная. Ночные сессии: "
              + ", ".join(flags) + ". Закрыть ночь у всех — off --all." + tail)
        return 1
    else:
        print("Ночь не включена." + tail)
        return 0
    for sid, info in leaving.items():
        end(sid, info)
    lines = []
    for sid, info in leaving.items():
        who = "эта сессия" if sid == me else f"сессия {sid}"
        lines.append(f"  {who}: /exit, затем {resume_line(sid, info)}")
    left = [s for s in night_flags()]
    print("Ночь снята: хуки больше не отказывают вместо человека, вопросы снова идут к тебе.\n"
          "Ночные разрешения контролёра держит сам процесс до перезапуска — перезапусти обычным claude:\n"
          + "\n".join(lines)
          + (f"\nНочными остались: {', '.join(left)} — off --all закроет и их." if left else "")
          + tail)
    return 0


def status(a) -> int:
    flags = night_flags()
    me = a.session
    mine_flag = load(flag_path(me)) if me else {}
    out = []
    if env_night():
        if mine_flag.get("ended"):
            out.append(f"Эта сессия: ночь снята в {mine_flag['ended']}, ночные разрешения — до перезапуска.")
        else:
            out.append("Эта сессия ночная (запущена лаунчером).")
    if flags:
        out.append(f"Ночных сессий: {len(flags)}.")
        for sid, info in flags.items():
            m = " (эта)" if sid == me else ""
            out.append(f"  {sid}{m}: с {info.get('since')}, {info.get('cwd') or info.get('project')}")
    if (state_dir() / "state.json").exists():
        out.append("В ~/.claude/settings.json остались ночные правила старой схемы — уберёт off.")
    print("\n".join(out) if out else "Ночь не включена.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["on", "mark", "off", "status"])
    ap.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--approved", default="", help="on, mark: файл утверждённого")
    ap.add_argument("--project", default="", help="mark: корень проекта")
    ap.add_argument("--all", action="store_true", help="off: снять ночь у всех сессий")
    a = ap.parse_args()
    if a.cmd in ("on", "mark") and not a.session:
        print("night_switch: нужен --session <id сессии>.")
        return 1
    return {"on": on, "mark": mark, "off": off, "status": status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
