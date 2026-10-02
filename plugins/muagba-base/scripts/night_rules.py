#!/usr/bin/env python3
"""Ночные правила: базовые из плагина + проекта + утверждённое на сегодня.

Базовые (`night/base.json` плагина) обновляются с плагином; проект в
`.claude/night/settings.json` дописывает своё. Общая функция для
night_switch.py и лаунчера. Запуск из лаунчера:
  python3 night_rules.py <project-settings.json> <approved.json> <out.json> [night_start]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "night" / "base.json"


def load(p) -> dict:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def merged(project: dict, approved: dict) -> dict:
    """Списки складываются без повторов, в порядке: база, проект, утверждённое."""
    base = load(BASE)
    out: dict = {"permissions": {}, "autoMode": {}}

    def add(sect: str, field: str, *lists) -> None:
        cur = out[sect].setdefault(field, [])
        for lst in lists:
            for x in lst or []:
                if x not in cur:
                    cur.append(x)

    for f in ("environment", "allow", "soft_deny", "hard_deny"):
        add("autoMode", f, (base.get("autoMode") or {}).get(f), (project.get("autoMode") or {}).get(f))
    add("autoMode", "allow", approved.get("allow_rules"))
    add("permissions", "deny", (base.get("permissions") or {}).get("deny"),
        (project.get("permissions") or {}).get("deny"))
    add("permissions", "allow", (project.get("permissions") or {}).get("allow"), approved.get("allow_commands"))
    return out


if __name__ == "__main__":
    proj, appr, out = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
    m = merged(proj, appr)
    if len(sys.argv) > 4:
        m["env"] = {"MUAGBA_MODE": "night", "MUAGBA_NIGHT_START": sys.argv[4]}
    Path(out).write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Ночью разрешено сверх дневного (утверждено " + str(appr.get("date")) + "):")
    for r in appr.get("allow_rules") or []:
        print("  • " + r)
    for c in appr.get("allow_commands") or []:
        print("  • команда " + c)
    for d in appr.get("dangerous") or []:
        print("  ⚠ ОПАСНОЕ, утверждено явно: " + d)
    for t in appr.get("tasks") or []:
        print("  ▸ задача: " + t)
