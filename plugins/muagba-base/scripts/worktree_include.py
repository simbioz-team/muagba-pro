#!/usr/bin/env python3
"""Докладывает в рабочее дерево файлы из `.worktreeinclude` проекта.

Claude Code копирует их только в деревья, которые заводит сам. Дерево,
заведённое `git worktree add` — конвейером, координатором, человеком, —
стартует без `.env`, и всё, что от него зависит, падает. У narta (17.11) так
гейт Stop краснел ~12 ходов подряд: e2e-сервер без DATABASE_URL. Скопировать
файл агент не мог — `.env` защищён, и правильно: правит его человек. Но копия
байт в байт из основного checkout'а — не правка, а то, что проект уже
объявил в `.worktreeinclude`. Её делает база, без агента и без разрешений.

Правила копии — те же, что у Claude Code: файл подходит под шаблон
`.worktreeinclude` основного checkout'а **и** игнорируется git'ом
(отслеживаемое в дереве и так есть). Сверх того:

- кладётся только недостающее: свой файл дерева не трогается никогда;
- содержимое не печатается — только пути;
- нет `.worktreeinclude` или дерево не связанное — ничего не делается.

Подготовка дерева. Копией не поставить зависимости: `node_modules` у веток
с разными lock-файлами общим быть не может, а без них быстрая часть
`check.sh` краснеет на `tsc` (наставник, 26.11: «npm ci» вписывали руками в
каждое задание). Стек знает только проект, поэтому шаг — его:
исполняемый `.claude/worktree-setup` в самом дереве. Нет файла — no-op.
База запускает его в корне дерева с `MUAGBA_MAIN_CHECKOUT` и
`MUAGBA_WORKTREE`, не дольше `MUAGBA_WORKTREE_SETUP_TIMEOUT` (600) с.
Скрипт обязан быть идемпотентным: гейт зовёт его перед каждым прогоном.

Режимы:
  hook          PostToolUse(Bash): после `git worktree add` наполняет все
                связанные деревья репозитория, готовит свежие (моложе
                10 минут) и сообщает агенту, что сделано.
  fill КАТАЛОГ  наполнить одно дерево (гейт перед проверкой). Печатает пути.
  setup КАТАЛОГ запустить `.claude/worktree-setup` дерева. Код скрипта;
                при сбое — хвост вывода в stdout. Нет скрипта — 0.
  covers ПУТЬ   код 0, если ПУТЬ лежит в связанном дереве и база кладёт его
                сама (guard-bash: подсказка вместо «иди к человеку»).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


def git(cwd: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                           text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def roots(path: Path) -> tuple[Path, Path] | None:
    """(корень дерева, корень основного checkout'а) для связанного дерева."""
    top = git(path, "rev-parse", "--show-toplevel")
    common = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not top or not common:
        return None
    tree, common_dir = Path(top.strip()), Path(common.strip())
    if common_dir.name != ".git":  # голый репозиторий — основного дерева нет
        return None
    main = common_dir.parent
    if tree.resolve() == main.resolve():
        return None
    return tree, main


def included(main: Path) -> list[str]:
    """Пути (от корня), которые проект просит класть в каждое дерево."""
    spec = main / ".worktreeinclude"
    if not spec.is_file():
        return []
    # -o -i с --exclude-from: неотслеживаемые файлы, подходящие под шаблоны
    # .worktreeinclude. Из них — только игнорируемые git'ом, как у Claude Code.
    out = git(main, "ls-files", "-z", "--others", "--ignored",
              f"--exclude-from={spec}")
    if not out:
        return []
    cand = [p for p in out.split("\0") if p]
    try:
        r = subprocess.run(["git", "-C", str(main), "check-ignore", "-z", "--stdin"],
                           input="\0".join(cand), capture_output=True, text=True,
                           timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return []
    ignored = {p for p in r.stdout.split("\0") if p}
    return [p for p in cand if p in ignored and (main / p).is_file()]


def fill(tree: Path, main: Path) -> list[str]:
    placed = []
    for rel in included(main):
        dst = tree / rel
        if os.path.lexists(dst):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            # O_EXCL: файл, появившийся между проверкой и записью, не затирается.
            fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, "wb") as out, open(main / rel, "rb") as src:
            shutil.copyfileobj(src, out)
        shutil.copymode(main / rel, dst)
        placed.append(rel)
    return placed


SETUP = ".claude/worktree-setup"
FRESH_S = 600


def setup(tree: Path, main: Path) -> tuple[int, str] | None:
    """Запустить подготовку дерева. None — скрипта нет; иначе (код, хвост)."""
    script = tree / SETUP
    if not (script.is_file() and os.access(script, os.X_OK)):
        return None
    env = dict(os.environ, MUAGBA_MAIN_CHECKOUT=str(main), MUAGBA_WORKTREE=str(tree))
    try:
        limit = float(os.environ.get("MUAGBA_WORKTREE_SETUP_TIMEOUT") or 600)
    except ValueError:
        limit = 600.0
    try:
        r = subprocess.run([str(script)], cwd=tree, env=env, capture_output=True,
                           text=True, timeout=limit, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return 124, f"{SETUP}: не уложился в {int(limit)} с"
    except OSError as e:
        return 126, f"{SETUP}: не запустился: {e}"
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
    return r.returncode, tail


def fresh(tree: Path) -> bool:
    """Дерево заведено только что: файл .git моложе FRESH_S."""
    try:
        return time.time() - (tree / ".git").stat().st_mtime < FRESH_S
    except OSError:
        return False


def linked_trees(main: Path) -> list[Path]:
    out = git(main, "worktree", "list", "--porcelain") or ""
    trees = [Path(l[len("worktree "):]) for l in out.splitlines()
             if l.startswith("worktree ")]
    return [t for t in trees if t.is_dir() and t.resolve() != main.resolve()]


WORKTREE_ADD = re.compile(r"\bgit\b[^;&|\n]*\bworktree\s+add\b")


def cmd_hook() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    cmd = ((data.get("tool_input") or {}).get("command")) or ""
    if not WORKTREE_ADD.search(cmd):
        return 0
    cwd = Path(data.get("cwd") or os.getcwd())
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common or Path(common.strip()).name != ".git":
        return 0
    main = Path(common.strip()).parent
    has_include = bool(included(main))
    notes, prepared = [], []
    for tree in linked_trees(main):
        placed = fill(tree, main) if has_include else []
        if placed:
            notes.append(f"{tree}: {', '.join(placed)}")
        if fresh(tree):
            res = setup(tree, main)
            if res is not None:
                code, tail = res
                prepared.append(f"{tree}: готово" if code == 0 else
                                f"{tree}: код {code}\n{tail}")
    msgs = []
    if notes:
        msgs.append("База положила в рабочее дерево файлы из .worktreeinclude "
                    "(копия основного checkout'а): " + "; ".join(notes) +
                    ". Копировать их руками не нужно.")
    if prepared:
        msgs.append(f"База запустила {SETUP} в новом дереве: " + "; ".join(prepared) +
                    ". Повторять его руками не нужно, если он не упал.")
    if msgs:
        msg = " ".join(msgs)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": msg}},
                         ensure_ascii=False))
    return 0


def existing(p: Path) -> Path:
    while not p.is_dir() and p != p.parent:
        p = p.parent
    return p


def cmd_fill(path: str) -> int:
    r = roots(existing(Path(path)))
    if r:
        for rel in fill(*r):
            print(rel)
    return 0


def cmd_setup(path: str) -> int:
    r = roots(existing(Path(path)))
    if not r:
        return 0
    res = setup(*r)
    if res is None:
        return 0
    code, tail = res
    if code:
        print(tail)
    return code


def cmd_covers(path: str) -> int:
    p = Path(path)
    r = roots(existing(p.parent))
    if not r:
        return 1
    tree, main = r
    try:
        rel = p.resolve().relative_to(tree.resolve()).as_posix()
    except ValueError:
        return 1
    return 0 if rel in included(main) else 1


def main() -> int:
    a = sys.argv[1:]
    if a == ["hook"]:
        # Хук обязан быть no-op при любой беде: сбой копии не повод ронять ход.
        try:
            return cmd_hook()
        except Exception:
            return 0
    if len(a) == 2 and a[0] == "fill":
        return cmd_fill(a[1])
    if len(a) == 2 and a[0] == "setup":
        return cmd_setup(a[1])
    if len(a) == 2 and a[0] == "covers":
        return cmd_covers(a[1])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
