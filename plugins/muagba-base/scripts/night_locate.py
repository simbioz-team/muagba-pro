#!/usr/bin/env python3
"""Где лаунчер ночи этого проекта — без привязки к каталогу (ADR-0016).

Ищет `.claude/claude-night` рядом с `.claude/night/settings.json` в
каталоге сессии, в основном checkout и в его рабочих деревьях: у narta
ночные файлы лежали в дереве координатора, а сессия — в основном checkout.
Из нескольких предпочитает тот, где уже есть утверждённое на сегодня, затем
каталог сессии, затем основной checkout.

Печатает JSON: {"launcher": путь|null, "approved": путь, "approved_today": bool,
"candidates": [...]}.
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    cwd = Path(sys.argv[1] if len(sys.argv) > 1 else os.getcwd()).resolve()
    roots = [cwd]
    r = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        main_root = Path(r.stdout.strip()).parent
        roots += [main_root] + sorted(Path(p) for p in glob.glob(str(main_root / ".claude" / "worktrees" / "*")))
    today = datetime.date.today().isoformat()
    found = []
    for root in dict.fromkeys(roots):
        launcher = root / ".claude" / "claude-night"
        if launcher.is_file() and (root / ".claude" / "night" / "settings.json").is_file():
            appr = root / ".claude" / "night" / "approved.json"
            try:
                ok = json.loads(appr.read_text(encoding="utf-8")).get("date") == today
            except (OSError, ValueError):
                ok = False
            found.append({"launcher": str(launcher), "approved": str(appr), "approved_today": ok})
    best = next((f for f in found if f["approved_today"]), found[0] if found else None)
    print(json.dumps({**(best or {"launcher": None, "approved": None, "approved_today": False}),
                      "candidates": [f["launcher"] for f in found]}, ensure_ascii=False))
    return 0 if best else 1


if __name__ == "__main__":
    sys.exit(main())
