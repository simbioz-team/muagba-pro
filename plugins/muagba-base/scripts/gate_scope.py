#!/usr/bin/env python3
"""Сдаёт ли сабагент код: его ли остановку держать гейтом.

Аргументы: каталог сабагента (`cwd` входа SubagentStop), стенограмма
сессии (`transcript_path`), каталог проекта — запасной, если стенограммы
нет. Выход 0 — держать, 1 — отпустить.

Раньше гейт узнавал исполнителя по имени роли: `implementer` или
`*:implementer`. Проект narta завёл свою роль `implementer-high`, и почти
все задачи с этапа 1.4 сдавались вовсе без гейта: 640 событий роли в
журнале и ни одной проверки. Имя роли — дело проекта, поэтому гейт
смотрит на свойство: **в дереве сабагента есть то, чего нет в дереве
сессии** — незакоммиченные правки или коммиты сверх HEAD сессии.

Сабагент, работавший в дереве самой сессии, не держится: его правки
проверит гейт хода сессии (Stop), а разделить их с правками координатора
нельзя. Проверяющий и исследователь в своём дереве ничего не оставляют и
проходят без проверки, как прежде.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def git(cwd: str, *args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return r.returncode, r.stdout.strip()


def session_cwd(transcript: str) -> str:
    """Последний `cwd` стенограммы сессии: координатор мог уйти в своё дерево."""
    try:
        with open(transcript, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 262144))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            cwd = json.loads(line).get("cwd")
        except (ValueError, AttributeError):
            continue
        if cwd:
            return cwd
    return ""


def holds(agent_cwd: str, transcript: str, project: str) -> bool:
    code, top = git(agent_cwd, "rev-parse", "--show-toplevel")
    if code != 0 or not top:
        return False
    sess = session_cwd(transcript) or project
    _, sess_top = git(sess, "rev-parse", "--show-toplevel") if sess else (1, "")
    if sess_top and os.path.realpath(sess_top) == os.path.realpath(top):
        return False
    code, dirty = git(top, "status", "--porcelain")
    if code == 0 and dirty:
        return True
    code, base = git(sess_top, "rev-parse", "HEAD") if sess_top else (1, "")
    if code != 0 or not base:
        return False
    code, ahead = git(top, "rev-list", "--count", f"{base}..HEAD")
    return code == 0 and ahead not in ("", "0")


def main() -> int:
    a = (sys.argv[1:] + ["", "", ""])[:3]
    return 0 if holds(*a) else 1


if __name__ == "__main__":
    sys.exit(main())
