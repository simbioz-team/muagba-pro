#!/usr/bin/env python3
"""Блокировка файлов базы в проекте (ADR-0017).

Файлы базы — то, что `template_sync.py` обновляет в проекте сам:
файлы-механизмы и управляемые блоки (`sync/manifest.json`). Агенту их
править нельзя: правила базы в AGENTS.md, переписанные агентом под себя,
перестают быть правилами.

Блокировка — не права файловой системы. `chmod` агент снимет той же
командой, git его не хранит, а людям он мешает. Блокировка здесь — сторож
по последствиям: после каждого действия агента (PostToolUse) файлы базы
сверяются с законным состоянием — тем, что записала база
(`.claude/muagba-sync.json` → written), — и изменённое возвращается из копии
в плагине. Сторожу всё равно, каким путём пришла правка — Edit, `sed`,
путь в переменной или скрипт: он смотрит на результат, а не на команду.

Законно менять файлы базы можно только через окно — один алгоритм для
любого обновления:

  1. снять блокировку  — открыть окно (сторож его пропускает);
  2. применить         — обновление плагина или правка человека;
  3. вернуть блокировку — закрыть окно и записать новое законное состояние.

Обновление плагина проходит его само (template_sync.py, окно закрывается
и при сбое). Человек — командами `unlock` и `lock` через `!` в сессии;
агенту `unlock` запрещает guard-bash. Изменённое человеком в окне
закрепляется за проектом (held): база его больше не сторожит и не
перезаписывает, а о новой версии сообщает.

Запуск:
  frame_lock.py guard            PostToolUse: сверить и вернуть;
  frame_lock.py unlock|lock|status [--cwd КАТАЛОГ]
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SYNC = PLUGIN / "sync"
STATE = ".claude/muagba-sync.json"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(root: Path, st: dict) -> None:
    p = root / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(cwd, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)


def project_root(cwd: Path) -> Path:
    r = git(cwd, "rev-parse", "--show-toplevel")
    return Path(r.stdout.decode().strip()) if r.returncode == 0 and r.stdout.strip() else cwd


def is_base_repo(root: Path) -> bool:
    return (root / "plugins" / "muagba-base" / ".claude-plugin").is_dir()


# --------------------------------------------------------------------------
# Блоки
# --------------------------------------------------------------------------
def block_bounds(text: str, bid: str) -> tuple[int, int] | None:
    """(начало содержимого, конец содержимого) блока или None."""
    b = text.find(f"<!-- muagba:begin {bid}")
    if b < 0:
        return None
    start = text.find("\n", b)
    end = text.find(f"<!-- muagba:end {bid} -->", start)
    if start < 0 or end < 0:
        return None
    return start + 1, end


def begin_line(bid: str) -> str:
    return (f"<!-- muagba:begin {bid} — блок обновляет плагин muagba-base; "
            f"правки сюда не вносить, своё — выше -->\n")


def put_block(text: str, bid: str, inner: str) -> str:
    bb = block_bounds(text, bid)
    if bb is None:
        return text.rstrip("\n") + "\n\n" + begin_line(bid) + inner + f"<!-- muagba:end {bid} -->\n"
    return text[:bb[0]] + inner + text[bb[1]:]


def items(root: Path):
    """(ключ, путь в проекте, копия в плагине, id блока или None)."""
    man = load(SYNC / "manifest.json")
    for f in man.get("files", []):
        yield f["path"], root / f["path"], SYNC / "files" / f["path"], None, f
    for b in man.get("blocks", []):
        yield f"block:{b['id']}", root / b["path"], SYNC / "blocks" / f"{b['id']}.md", b["id"], b


def current(dst: Path, bid: str | None) -> bytes | None:
    """Содержимое файла или блока; None — нет файла или меток блока."""
    try:
        data = dst.read_bytes()
    except OSError:
        return None
    if bid is None:
        return data
    text = data.decode("utf-8", "replace")
    bb = block_bounds(text, bid)
    return text[bb[0]:bb[1]].encode("utf-8") if bb else None


# --------------------------------------------------------------------------
# Окно
# --------------------------------------------------------------------------
def window_path(root: Path) -> Path:
    # Вне дерева и вне истории: окно — состояние этого checkout'а сейчас,
    # а не факт о проекте. В рабочем дереве у каждого своё.
    r = git(root, "rev-parse", "--git-path", "muagba-frame-window")
    if r.returncode == 0 and r.stdout.strip():
        p = Path(r.stdout.decode().strip())
        return p if p.is_absolute() else root / p
    return root / ".claude" / "muagba-frame-window"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def window(root: Path) -> dict | None:
    """Открытое окно или None. Окно обновления, чей процесс умер, — закрыто:
    ловушка на выход не срабатывает только при kill -9."""
    w = load(window_path(root))
    if not w:
        return None
    if w.get("by") == "sync" and not alive(int(w.get("pid") or 0)):
        with contextlib.suppress(OSError):
            window_path(root).unlink()
        return None
    return w


def open_window(root: Path, by: str) -> None:
    p = window_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"by": by, "pid": os.getpid(),
                             "since": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n",
                 encoding="utf-8")


def close_window(root: Path) -> None:
    with contextlib.suppress(OSError):
        window_path(root).unlink()


@contextlib.contextmanager
def update_window(root: Path):
    """Снять блокировку → применить → вернуть. Окно закрывается при любом
    выходе, в том числе по SIGTERM (тайм-аут хука)."""
    prev = signal.getsignal(signal.SIGTERM)

    def term(*_):
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, term)
    open_window(root, "sync")
    try:
        yield
    finally:
        close_window(root)
        signal.signal(signal.SIGTERM, prev)


# --------------------------------------------------------------------------
# Сторож
# --------------------------------------------------------------------------
def guard(root: Path) -> list[str]:
    """Вернуть изменённые в обход окна файлы базы. Сторожит только то, чью
    текущую версию записала база: законный отпечаток (written) совпадает с
    копией в плагине. Конфликтное, закреплённое за проектом (held) и
    незаписанное — не его."""
    if is_base_repo(root) or window(root):
        return []
    st = load(root / STATE)
    written, held = st.get("written") or {}, st.get("held") or {}
    restored = []
    for key, dst, copy, bid, spec in items(root):
        legit = written.get(key)
        if not legit or key in held:
            continue
        try:
            new = copy.read_bytes()
        except OSError:
            continue
        if sha(new) != legit:
            continue
        cur = current(dst, bid)
        if cur is not None and sha(cur) == legit:
            continue
        if bid is None:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(new)
            if spec.get("exec"):
                dst.chmod(dst.stat().st_mode | 0o111)
            restored.append(spec["path"])
        else:
            if not dst.exists():
                continue  # файл целиком убрал человек или проект — не блок базы
            text = dst.read_text(encoding="utf-8")
            dst.write_text(put_block(text, bid, new.decode("utf-8")), encoding="utf-8")
            restored.append(f"{spec['path']} (блок {bid})")
    return restored


def log_event(rec: dict) -> None:
    if os.environ.get("MUAGBA_NO_LOG"):
        return
    d = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / ".claude" / "logs"
    if not d.is_dir():
        return
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), **rec}
    with contextlib.suppress(OSError), open(d / "agents.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def hook_guard() -> int:
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        inp = {}
    cwd = Path(inp.get("cwd") or os.getcwd())
    roots = {project_root(cwd)}
    fp = (inp.get("tool_input") or {}).get("file_path")
    if fp:
        # Правила на файл — его проекта, а не сессии (owner_dir).
        d = Path(fp).parent
        while not d.exists() and d != d.parent:
            d = d.parent
        roots.add(project_root(d))
    restored = []
    for root in roots:
        for r in guard(root):
            restored.append(r)
            log_event({"event": "guard", "session_id": inp.get("session_id"),
                       "agent_type": inp.get("agent_type") or None, "cwd": str(cwd),
                       "hook": "frame-lock", "decision": "restored", "target": r})
    if not restored:
        return 0
    msg = ("Возвращено: " + ", ".join(restored) + " — файлы базы muagba-base, правка агента "
           "откатана. Их обновляет плагин, а меняет человек через окно: "
           "`! python3 <плагин>/scripts/frame_lock.py unlock`, правка, `… lock`. "
           "Нужна правка — попроси человека; своё правило — в AGENTS.md выше блока базы.")
    print(json.dumps({"decision": "block", "reason": msg, "systemMessage": msg}, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------
# Окно человека
# --------------------------------------------------------------------------
def cmd_unlock(root: Path) -> int:
    w = window(root)
    if w:
        print(f"Окно уже открыто ({w.get('by')}, с {w.get('since')}).")
        return 0
    open_window(root, "human")
    print("Блокировка файлов базы снята. Внесите правку и верните: frame_lock.py lock")
    return 0


def cmd_lock(root: Path) -> int:
    st = load(root / STATE)
    written, held = st.setdefault("written", {}), st.setdefault("held", {})
    kept = []
    for key, dst, copy, bid, spec in items(root):
        cur = current(dst, bid)
        if cur is None or not written.get(key) or sha(cur) == written[key]:
            continue
        held[key] = sha(cur)
        kept.append(spec["path"] + (f" (блок {bid})" if bid else ""))
    if not held:
        st.pop("held")
    if kept:
        save_state(root, st)
    close_window(root)
    print("Блокировка возвращена." + (" Закреплено за проектом (база не сторожит и не обновляет, "
                                      "о новой версии сообщит): " + ", ".join(kept) if kept else ""))
    return 0


def cmd_status(root: Path) -> int:
    w = window(root)
    st = load(root / STATE)
    print(f"Окно открыто ({w.get('by')}, с {w.get('since')})." if w else "Блокировка действует.")
    if st.get("held"):
        print("Закреплено за проектом: " + ", ".join(st["held"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["guard", "unlock", "lock", "status"])
    ap.add_argument("--cwd", default=os.getcwd())
    a = ap.parse_args()
    if a.cmd == "guard":
        return hook_guard()
    root = project_root(Path(a.cwd))
    if is_base_repo(root):
        print("Репозиторий базы: template/ — исходник, блокировки нет.")
        return 0
    return {"unlock": cmd_unlock, "lock": cmd_lock, "status": cmd_status}[a.cmd](root)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
