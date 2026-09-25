#!/usr/bin/env python3
"""Уборка рабочих деревьев, которая уничтожит работу.

Читает команду со stdin, рабочий каталог — первым аргументом. Печатает две
строки — что не так и что делать — и выходит с 1; молчит и 0, если всё
чисто.

Уборка дерева — хозяйство, а не работа. Безопасная уборка разрешена
правилами каркаса (`git worktree remove` без `--force`, `git branch -d`):
git сам откажется удалить грязное дерево или неслитую ветку. Опасная —
запрещается с причиной, а не отдаётся на вопрос: ночью вопрос висит до утра,
а оставленное дерево никому не мешает. Нашёл проект narta: агенты убирали
деревья посреди автономной работы, и каждое удаление ждало человека.

Ловит:
- `git worktree remove --force|-f <дерево>`, когда в дереве незакоммиченное;
- `git branch -D <ветка>`, когда её коммиты не достижимы ни из одной другой
  ветки — локальной или удалённой;
- `rm -r…` по каталогу, который git знает как рабочее дерево: `rm` оставляет
  в git битые записи и уносит незакоммиченное.
"""
from __future__ import annotations

import os
import subprocess
import sys

from shell_split import segments  # общий разбор: см. shell_split.py


def git(cwd: str, *args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return r.returncode, r.stdout


def git_argv(argv: list[str], cwd: str) -> tuple[list[str], str]:
    """argv без `git` и глобальных опций; каталог с учётом `-C`."""
    rest, i = argv[1:], 0
    while i < len(rest):
        if rest[i] == "-C" and i + 1 < len(rest):
            cwd = os.path.join(cwd, rest[i + 1])
            i += 2
        elif rest[i] == "-c" and i + 1 < len(rest):
            i += 2
        else:
            break
    return rest[i:], cwd


def worktrees(cwd: str) -> set[str]:
    code, out = git(cwd, "worktree", "list", "--porcelain")
    if code != 0:
        return set()
    return {os.path.realpath(l[9:]) for l in out.splitlines() if l.startswith("worktree ")}


def check(command: str, cwd: str) -> tuple[str, str] | None:
    cd = cwd
    for seg in segments(command):
        argv = seg
        head = argv[0].rsplit("/", 1)[-1] if argv else ""
        if head == "cd" and len(argv) > 1:
            cd = os.path.join(cd, argv[1])
            continue
        if head == "git":
            sub, gcwd = git_argv(argv, cd)
            if sub[:2] == ["worktree", "remove"]:
                opts = [a for a in sub[2:] if a.startswith("-")]
                paths = [a for a in sub[2:] if not a.startswith("-")]
                if not any(o in ("--force", "-f", "-ff") for o in opts) or not paths:
                    continue
                tree = os.path.join(gcwd, paths[0])
                code, dirty = git(tree, "status", "--porcelain")
                if code == 0 and dirty.strip():
                    return (f"git worktree remove --force по дереву с незакоммиченной "
                            f"работой ({len(dirty.splitlines())} файлов в {paths[0]})",
                            "работа пропадёт. Закоммить её в ветку дерева, либо оставь "
                            "дерево как есть и отметь в журнале сессии — человек разберёт. "
                            "Без --force git сам не даст удалить грязное дерево.")
            if sub[:1] == ["branch"] and ("-D" in sub or ("-d" in sub and "--force" in sub)):
                for br in [a for a in sub[1:] if not a.startswith("-")]:
                    code, only = git(gcwd, "rev-list", "--max-count=1", br, "--not",
                                     f"--exclude={br}", "--branches", "--remotes")
                    if code == 0 and only.strip():
                        return (f"git branch -D {br}: в ветке есть коммиты, которых нет "
                                "ни в одной другой ветке",
                                "они пропадут. Слей ветку или запушь её, либо оставь и "
                                "отметь в журнале сессии. Для слитой ветки хватит "
                                "`git branch -d`.")
        recursive = any(a == "--recursive" or (a.startswith("-") and not a.startswith("--")
                                               and ("r" in a or "R" in a)) for a in argv[1:])
        if head == "rm" and recursive:
            known = worktrees(cd)
            for a in argv[1:]:
                if a.startswith("-"):
                    continue
                target = os.path.realpath(os.path.join(cd, a))
                if target in known and target != os.path.realpath(cd):
                    return (f"rm -r по рабочему дереву git ({a})",
                            "rm оставляет в git битые записи и уносит незакоммиченное. "
                            "Убирай дерево через `git worktree remove` без --force — "
                            "git сам откажется, если в нём есть работа.")
    return None


def main() -> int:
    cwd = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    found = check(sys.stdin.read(), cwd)
    if found:
        print(found[0])
        print(found[1])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
