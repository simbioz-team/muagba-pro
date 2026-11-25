#!/usr/bin/env python3
"""В проекте включено только то, что проект включил явно.

  plugin_scope.py [--root DIR] [--home DIR] [--apply]

Без `--apply` — показывает, что будет выключено, и выходит с 1, если есть что.

Каждый субагент и каждый запрос координатора несут в контексте списки
скилов, отложенных инструментов и инструкции MCP всех подключённых плагинов
и коннекторов claude.ai. У наставника 25.11 это ~84 тыс. символов (~25 тыс.
токенов) из 68 тыс. токенов старта исполнителя: финансы, продакт, дизайн,
Figma, Google, — для кода не нужны.

Пишет в `.claude/settings.local.json` проекта (личный файл, не в git):

- `enabledPlugins`: `false` каждому плагину, включённому в
  `~/.claude/settings.json`, но не упомянутому в `.claude/settings.json`
  проекта. Шаблона «выключить всё, кроме» у Claude Code нет — только
  перечислением. Плагины самой базы (`muagba-base`, `docsys`) не трогает:
  у проекта, настроенного до 0.23.23, их нет в своём `settings.json`.
- `syncClaudeAiPlugins: false` — плагины каталога из аккаунта claude.ai.
  Из общего `settings.json` проекта этот ключ не читается, только из личных.
- `disableClaudeAiConnectors: true` — коннекторы claude.ai. Ключ «истина
  из любого источника», поэтому он в личном файле: из общего его не
  отменить.

Скилы аккаунта (`syncClaudeAiSkills`) не трогает: их человек заводит сам.
Ключ, уже стоящий в личном файле, не меняет — это решение человека.
Вступает в силу со следующей сессии.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def load(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


BASE = {"muagba-base@muagba-pro", "docsys@docsys"}


def plan(root: str, home: str) -> tuple[dict, list[str]]:
    user = load(os.path.join(home, ".claude", "settings.json"))
    proj = load(os.path.join(root, ".claude", "settings.json"))
    local = load(os.path.join(root, ".claude", "settings.local.json"))
    mentioned = BASE | set(proj.get("enabledPlugins") or {}) | set(local.get("enabledPlugins") or {})
    changes: dict = {}
    notes: list[str] = []
    off = {}
    for pid, on in (user.get("enabledPlugins") or {}).items():
        if on and pid not in mentioned:
            off[pid] = False
            notes.append(f"плагин {pid}: включён у пользователя, проект его не включал — выключить")
    if off:
        changes["enabledPlugins"] = off
    if "syncClaudeAiPlugins" not in local:
        changes["syncClaudeAiPlugins"] = False
        notes.append("плагины каталога из аккаунта claude.ai — выключить (syncClaudeAiPlugins)")
    if "disableClaudeAiConnectors" not in local:
        changes["disableClaudeAiConnectors"] = True
        notes.append("коннекторы claude.ai — выключить (disableClaudeAiConnectors)")
    return changes, notes


def apply(root: str, changes: dict) -> None:
    path = os.path.join(root, ".claude", "settings.local.json")
    local = load(path)
    for k, v in changes.items():
        if k == "enabledPlugins":
            local.setdefault("enabledPlugins", {}).update(v)
        else:
            local[k] = v
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(local, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--home", default=os.path.expanduser("~"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(os.path.join(a.root, ".claude")):
        print("нет .claude/ — проект не настроен базой, ничего не делаю")
        return 0
    changes, notes = plan(a.root, a.home)
    if not changes:
        print("лишнего не включено")
        return 0
    for n in notes:
        print(("выключено: " if a.apply else "к выключению: ") + n)
    if a.apply:
        apply(a.root, changes)
        print("записано в .claude/settings.local.json; действует со следующей сессии")
        return 0
    print("применить: plugin_scope.py --apply")
    return 1


if __name__ == "__main__":
    sys.exit(main())
