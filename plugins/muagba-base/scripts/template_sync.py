#!/usr/bin/env python3
"""Файлы каркаса обновляются сами, вместе с плагином (ADR-0017).

Каркас копируется в проект один раз, и всё, что база потом в нём меняла,
до проектов не доезжало: лаунчер ночи, правила агента в AGENTS.md —
человек копировал руками. Здесь — то, что база может обновлять сама:

- **файлы-механизмы** (`sync/manifest.json` → files): в них нет ничего от
  проекта. Переписываются, если проект их не менял: текущее содержимое
  совпадает с одной из выпущенных версий (`sync/history.json`) или с тем,
  что база записала в прошлый раз (`.claude/muagba-sync.json`);
- **управляемые блоки** (→ blocks): правила базы между метками
  `<!-- muagba:begin <id> -->` и `<!-- muagba:end <id> -->`, остальное в
  файле — проекта. Нет меток — блок дописывается в конец файла один раз.

Изменённое проектом не трогается: сообщение говорит, где лежит новая
версия. Содержание проекта (миссия, конституция, workflow, спеки) не
трогается никогда — новое туда приходит через пробы и вопросы.

Режимы:
  (по умолчанию)  SessionStart: синхронизировать каталог сессии; молчит,
                  если версия плагина та же, что в прошлый раз;
  --build         в репозитории базы: собрать sync/ из template/ и истории git;
  --check         в репозитории базы: sync/ собран из текущего template/.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_lock import (block_bounds, begin_line, is_base_repo, project_root,  # noqa: E402
                        update_window, window)

PLUGIN = Path(__file__).resolve().parent.parent
SYNC = PLUGIN / "sync"
STATE = ".claude/muagba-sync.json"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(cwd, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)


def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------------------
# Сборка (репозиторий базы)
# --------------------------------------------------------------------------
def build(repo: Path, write: bool) -> list[str]:
    """Собрать sync/files, sync/blocks и sync/history.json из template/.
    Возвращает список расхождений с тем, что лежит сейчас."""
    man = load(SYNC / "manifest.json")
    tpl = repo / "template"
    want: dict[Path, bytes] = {}
    history: dict[str, list[str]] = {}
    for f in man.get("files", []):
        src = tpl / f["path"]
        want[SYNC / "files" / f["path"]] = src.read_bytes()
        hs = set()
        log = git(repo, "log", "--format=%H", "--", f"template/{f['path']}").stdout.decode().split()
        for c in log:
            r = git(repo, "show", f"{c}:template/{f['path']}")
            if r.returncode == 0:
                hs.add(sha(r.stdout))
        hs.add(sha(src.read_bytes()))
        history[f["path"]] = sorted(hs)
    for b in man.get("blocks", []):
        text = (tpl / b["path"]).read_text(encoding="utf-8")
        bb = block_bounds(text, b["id"])
        if not bb:
            raise SystemExit(f"template/{b['path']}: нет блока {b['id']}")
        inner = text[bb[0]:bb[1]]
        want[SYNC / "blocks" / f"{b['id']}.md"] = inner.encode("utf-8")
        hs = {sha(inner.encode("utf-8"))}
        for c in git(repo, "log", "--format=%H", "--", f"template/{b['path']}").stdout.decode().split():
            r = git(repo, "show", f"{c}:template/{b['path']}")
            if r.returncode == 0:
                old = r.stdout.decode("utf-8", "replace")
                ob = block_bounds(old, b["id"])
                if ob:
                    hs.add(sha(old[ob[0]:ob[1]].encode("utf-8")))
        history[f"block:{b['id']}"] = sorted(hs)
    want[SYNC / "history.json"] = (json.dumps(history, ensure_ascii=False, indent=2) + "\n").encode()
    diffs = []
    for p, data in want.items():
        cur = p.read_bytes() if p.exists() else None
        if cur != data:
            diffs.append(str(p.relative_to(PLUGIN)))
            if write:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
    return diffs


# --------------------------------------------------------------------------
# Синхронизация проекта
# --------------------------------------------------------------------------
def sync(root: Path, version: str, force: bool = False) -> tuple[list[str], list[str]]:
    """(обновлено, конфликты)."""
    man = load(SYNC / "manifest.json")
    hist = load(SYNC / "history.json")
    statep = root / STATE
    st = load(statep)
    if st.get("version") == version and not force:
        return [], []
    written = dict(st.get("written") or {})
    held = dict(st.get("held") or {})
    updated, conflicts = [], []
    # Снять блокировку → применить → вернуть: сторож frame_lock.py не трогает
    # открытое окно, а закрывается оно при любом выходе.
    with update_window(root):
        _apply(root, man, hist, written, held, updated, conflicts)
    st = {"version": version, "written": written}
    if held:
        st["held"] = held
    statep.parent.mkdir(parents=True, exist_ok=True)
    statep.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return updated, conflicts


def _apply(root, man, hist, written, held, updated, conflicts) -> None:
    for f in man.get("files", []):
        dst = root / f["path"]
        new = (SYNC / "files" / f["path"]).read_bytes()
        if f.get("requires") and not (root / f["requires"]).exists():
            continue
        if not dst.exists():
            if not f.get("create"):
                continue
        else:
            cur = dst.read_bytes()
            if cur == new:
                written[f["path"]] = sha(new)
                held.pop(f["path"], None)
                continue
            if f["path"] in held:
                conflicts.append(f"{f['path']} — закреплён за проектом; новая версия: {SYNC / 'files' / f['path']} "
                                 "(скопируйте её на место — файл вернётся базе)")
                continue
            if sha(cur) not in set(hist.get(f["path"], [])) | {written.get(f["path"])}:
                conflicts.append(f"{f['path']} — изменён в проекте; новая версия: {SYNC / 'files' / f['path']}")
                continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(new)
        if f.get("exec"):
            dst.chmod(dst.stat().st_mode | 0o111)
        written[f["path"]] = sha(new)
        updated.append(f["path"])
    for b in man.get("blocks", []):
        dst = root / b["path"]
        if not dst.exists():
            continue
        new = (SYNC / "blocks" / f"{b['id']}.md").read_text(encoding="utf-8")
        text = dst.read_text(encoding="utf-8")
        key = f"block:{b['id']}"
        bb = block_bounds(text, b["id"])
        if bb is None:
            text = text.rstrip("\n") + "\n\n" + begin_line(b["id"]) + new + f"<!-- muagba:end {b['id']} -->\n"
            dst.write_text(text, encoding="utf-8")
            written[key] = sha(new.encode())
            updated.append(f"{b['path']} (блок {b['id']} добавлен в конец: если эти правила уже "
                           f"были в файле вне блока — удалите повтор)")
            continue
        inner = text[bb[0]:bb[1]]
        if inner == new:
            written[key] = sha(new.encode())
            held.pop(key, None)
            continue
        if key in held:
            conflicts.append(f"{b['path']}, блок {b['id']} — закреплён за проектом; новая версия: "
                             f"{SYNC / 'blocks' / (b['id'] + '.md')}")
            continue
        if sha(inner.encode()) not in set(hist.get(key, [])) | {written.get(key)}:
            conflicts.append(f"{b['path']}, блок {b['id']} — правлен в проекте; новая версия: "
                             f"{SYNC / 'blocks' / (b['id'] + '.md')}")
            continue
        dst.write_text(text[:bb[0]] + new + text[bb[1]:], encoding="utf-8")
        written[key] = sha(new.encode())
        updated.append(f"{b['path']} (блок {b['id']})")


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in ("--build", "--check"):
        repo = PLUGIN.parent.parent
        diffs = build(repo, write=args[0] == "--build")
        if args[0] == "--check" and diffs:
            print("sync/ не собран из текущего template/: " + ", ".join(diffs)
                  + ". Запусти: python3 plugins/muagba-base/scripts/template_sync.py --build")
            return 1
        print("sync/: " + (", ".join(diffs) if diffs else "без изменений"))
        return 0
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        inp = {}
    cwd = Path(inp.get("cwd") or os.getcwd())
    root = project_root(cwd)
    # Репозиторий самой базы: template/ — исходник, синхронизировать некуда.
    if is_base_repo(root) or not (root / ".claude").is_dir():
        return 0
    version = load(PLUGIN / ".claude-plugin" / "plugin.json").get("version", "?")
    w = window(root)
    if w and w.get("by") == "human":
        # Окно человека не закрыто: обновлять поверх его правки нельзя, а
        # сторож, пока окно открыто, не работает.
        msg = (f"Блокировка файлов базы снята человеком с {w.get('since')} и не возвращена: "
               f"сторож не работает, обновление отложено. Вернуть: "
               f"! python3 {PLUGIN / 'scripts' / 'frame_lock.py'} lock")
        print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": msg}}, ensure_ascii=False))
        return 0
    updated, conflicts = sync(root, version, force="--force" in args)
    if not updated and not conflicts:
        return 0
    lines = [f"muagba-base {version} обновила файлы базы в проекте:"] + [f"- {u}" for u in updated]
    if updated:
        lines.append("Проверь разницу (git diff) и закоммить отдельным коммитом "
                     f"«muagba-base {version}: обновление файлов базы».")
    if conflicts:
        lines += ["Не обновлено — проект менял эти файлы, решает человек:"] + [f"- {c}" for c in conflicts]
    msg = "\n".join(lines)
    print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": msg}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
