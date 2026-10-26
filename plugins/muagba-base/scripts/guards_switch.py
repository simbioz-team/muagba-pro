#!/usr/bin/env python3
"""Выключатель ограничений агентов в проекте: off | on | status.

  off     хуки-ограничители базы молчат, правила `deny` из
          .claude/settings.json и .claude/settings.local.json проекта
          убраны (во всех рабочих деревьях репозитория);
  on      правила возвращены ровно на места, хуки снова работают;
  status  что сейчас.
  notice  SessionStart: при снятых ограничениях — заметная строка человеку
          и агенту. Без пометки молчит.

Молчат protect-paths, guard-bash, сторож файлов базы (frame_lock guard) и
гейт (gate-check). Журналы, наблюдение и синхронизация работают: снятые
ограничения — не повод терять след. Правила `ask` не трогаются, и
пользовательские настройки (~/.claude) тоже: выключатель — про проект.

Пометка — `<git common dir>/muagba-guards-off`: одна на репозиторий, то
есть на все его рабочие деревья, и вне истории. В ней же снятые правила,
по ней `on` их возвращает. Срока нет: выключено, пока человек не включит,
и об этом напоминает каждая сессия.

Запускает человек (`!` в сессии): агенту guard-bash запрещает и `off`, и
запись пометки. Порог, а не стена — команду, собранную в переменной, хук
не увидит; но выключение тогда видно в журнале и в начале каждой сессии.
Пока ограничения сняты, .claude/settings.json изменён — не коммитьте его.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

MARK = "muagba-guards-off"
SETTINGS = (".claude/settings.json", ".claude/settings.local.json")


def git(cwd: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    except OSError:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def mark_path(cwd: Path) -> Path:
    """Пометка репозитория, которому принадлежит cwd. Вне git — в .claude/."""
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common:
        return Path(common) / MARK
    return cwd / ".claude" / MARK


def is_off(cwd: Path) -> bool:
    return mark_path(cwd).is_file()


def trees(cwd: Path) -> list[Path]:
    """Корни всех рабочих деревьев репозитория; вне git — сам cwd."""
    out = git(cwd, "worktree", "list", "--porcelain")
    roots = [Path(l[len("worktree "):]) for l in out.splitlines() if l.startswith("worktree ")]
    return roots or [cwd]


def load(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def write_json(p: Path, d: dict) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def log_event(cwd: Path, decision: str) -> None:
    root = Path(git(cwd, "rev-parse", "--show-toplevel") or cwd)
    d = root / ".claude" / "logs"
    if os.environ.get("MUAGBA_NO_LOG") or not d.is_dir():
        return
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
           "event": "guards", "decision": decision}
    try:
        with open(d / "agents.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def cmd_off(cwd: Path) -> int:
    mark = mark_path(cwd)
    if mark.is_file():
        print(f"Ограничения уже сняты (с {load(mark).get('since', '?')}).")
        return 0
    taken: dict[str, list] = {}
    for root in trees(cwd):
        for rel in SETTINGS:
            p = root / rel
            d = load(p)
            deny = (d.get("permissions") or {}).get("deny")
            if not isinstance(deny, list) or not deny:
                continue
            taken[str(p)] = deny
            d["permissions"]["deny"] = []
            write_json(p, d)
    mark.parent.mkdir(parents=True, exist_ok=True)
    write_json(mark, {"since": datetime.datetime.now().isoformat(timespec="seconds"), "deny": taken})
    log_event(cwd, "off")
    print("Ограничения агентов сняты: protect-paths, guard-bash, сторож файлов базы, гейт.")
    for p, deny in taken.items():
        print(f"  deny убран ({len(deny)}): {p}")
    print("Вернуть: ./.claude/guards on. Пока сняты, settings.json изменён — не коммитьте его.")
    return 0


def cmd_on(cwd: Path) -> int:
    mark = mark_path(cwd)
    if not mark.is_file():
        print("Ограничения и так действуют.")
        return 0
    for p, original in (load(mark).get("deny") or {}).items():
        p = Path(p)
        if not p.is_file():
            print(f"  нет файла, правила не возвращены: {p}")
            continue
        d = load(p)
        perms = d.setdefault("permissions", {})
        cur = perms.get("deny") if isinstance(perms.get("deny"), list) else []
        # Добавленное, пока ограничения были сняты, остаётся — после исходных.
        perms["deny"] = original + [r for r in cur if r not in original]
        write_json(p, d)
        print(f"  deny возвращён ({len(original)}): {p}")
    mark.unlink()
    log_event(cwd, "on")
    print("Ограничения агентов действуют.")
    return 0


def cmd_status(cwd: Path) -> int:
    mark = mark_path(cwd)
    if mark.is_file():
        print(f"Ограничения сняты с {load(mark).get('since', '?')}. Вернуть: ./.claude/guards on")
    else:
        print("Ограничения действуют.")
    return 0


def cmd_notice() -> int:
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        inp = {}
    cwd = Path(inp.get("cwd") or os.getcwd())
    mark = mark_path(cwd)
    if not mark.is_file():
        return 0
    msg = (f"⚠ Ограничения агентов в этом проекте сняты с {load(mark).get('since', '?')}: "
           "защита путей, разбор команд, сторож файлов базы, гейт и правила deny не действуют. "
           "Вернуть — человек: ! ./.claude/guards on")
    print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": msg}}, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["off", "on", "status", "notice"])
    ap.add_argument("--cwd", default=os.getcwd())
    a = ap.parse_args()
    if a.cmd == "notice":
        return cmd_notice()
    return {"off": cmd_off, "on": cmd_on, "status": cmd_status}[a.cmd](Path(a.cwd).resolve())


if __name__ == "__main__":
    sys.exit(main())
