#!/usr/bin/env python3
"""SessionStart: загруженная версия плагина совпадает с выпуском.

Два случая, которые нашли на живых проектах и которые иначе не видно:

- **Устарела.** Автообновление обновляет установку пользователя, а
  проектная остаётся: у study_mcp три дня работала 0.13.3 при выпущенной
  0.17.0. И уже запущенная сессия живёт на том, что загрузила при старте.
- **Не из выпуска.** Маркетплейс-каталог Claude Code копирует как есть,
  вместе с незакоммиченными правками. У narta «0.16.3» оказалась рабочим
  деревом базы на середине правки: версия уже поднята, исправление — нет.

Сверяет: версию из plugin.json загруженной копии; версию в листинге
маркетплейса; и, если маркетплейс — git-репозиторий, что установлен коммит
тега `<имя>--v<версия>`. Расхождение — предупреждение человеку и агенту.
Решений не принимает. Нет какого-то файла — молчит.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def vtuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return ()


def git(repo: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                           text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def problems(root: Path, home: Path) -> list[str]:
    me = load(root / ".claude-plugin" / "plugin.json")
    name, loaded = me.get("name"), me.get("version")
    if not name or not loaded:
        return []
    installed = load(home / "installed_plugins.json")
    installed = installed.get("plugins", installed)
    entry, key = None, None
    for k, rows in installed.items():
        if not k.startswith(name + "@") or not isinstance(rows, list):
            continue
        for r in rows:
            try:
                same = Path(r.get("installPath", "")).resolve() == root.resolve()
            except OSError:
                same = False
            if same:
                entry, key = r, k
    if not entry:
        return []
    mp = key.split("@", 1)[1]
    scope = entry.get("scope") or "user"
    upd = f"claude plugin update {name}@{mp} --scope {scope}"
    loc = load(home / "known_marketplaces.json").get(mp, {}).get("installLocation")
    if not loc:
        return []
    loc = Path(loc)
    out: list[str] = []

    listing = load(loc / ".claude-plugin" / "marketplace.json")
    src = next((p.get("source") for p in listing.get("plugins") or []
                if p.get("name") == name), None)
    if isinstance(src, str):
        latest = load(loc / src / ".claude-plugin" / "plugin.json").get("version")
        if latest and vtuple(latest) > vtuple(loaded):
            out.append(f"загружена {name} {loaded}, в маркетплейсе уже {latest}. "
                       f"Обновить: `{upd}`, затем перезапустить сессию.")

    if git(loc, "rev-parse", "--is-inside-work-tree") == "true":
        tag = f"{name}--v{loaded}"
        tagged = git(loc, "rev-list", "-n", "1", tag)
        sha = entry.get("gitCommitSha") or ""
        if not tagged:
            out.append(f"загруженной {name} {loaded} нет среди выпусков (нет тега {tag}) — "
                       "похоже, это рабочее дерево маркетплейса на середине правки.")
        elif sha and not tagged.startswith(sha[:7]) and not sha.startswith(tagged[:7]):
            out.append(f"загруженная {name} {loaded} собрана не из выпуска: коммит "
                       f"{sha[:7]}, а у тега {tag} — {tagged[:7]}. Переустановить: `{upd}`.")
    return out


def main() -> int:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not root:
        return 0
    home = Path(os.environ.get("MUAGBA_PLUGINS_HOME")
                or Path.home() / ".claude" / "plugins")
    try:
        found = problems(Path(root), home)
    except Exception:
        return 0  # проверка версии не должна мешать старту сессии
    if not found:
        return 0
    text = "muagba: " + " ".join(found)
    print(json.dumps({"systemMessage": text,
                      "hookSpecificOutput": {"hookEventName": "SessionStart",
                                             "additionalContext": text}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
