#!/usr/bin/env python3
"""Где лежит каркас (template/) базы.

Плагин и каркас живут в одном репозитории, но ставятся по-разному: плагин
кэшируется, каркас копируется руками. Скил не должен просить человека вспомнить
путь к клону — путь известен Claude Code, надо только его достать.

Печатает путь и выходит с 0. Не нашёл — печатает причину в stderr и выходит с 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKER = "docs/constitution.md"  # по нему отличаем каркас от чего угодно ещё


def looks_like_template(p: Path) -> bool:
    return p.is_dir() and (p / MARKER).exists() and (p / ".claude").is_dir()


def candidates() -> list[Path]:
    out: list[Path] = []
    # 1. Репозиторий базы, если скрипт запущен прямо из него.
    for parent in HERE.parents:
        out.append(parent / "template")
    # 2. Маркетплейсы Claude Code: installLocation указывает на корень репозитория
    #    и для github-источника, и для локального каталога.
    reg = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    for name, entry in (data or {}).items():
        loc = (entry or {}).get("installLocation")
        if loc:
            out.append(Path(loc) / "template")
    # 3. Каталог маркетплейсов на случай, если запись не завелась.
    out += sorted((Path.home() / ".claude" / "plugins" / "marketplaces").glob("*/template"))
    return out


def main() -> int:
    seen = set()
    for c in candidates():
        c = c.expanduser()
        if c in seen:
            continue
        seen.add(c)
        if looks_like_template(c):
            print(c)
            return 0
    print("не найден каркас: ни в репозитории базы, ни среди маркетплейсов.\n"
          "Подключи маркетплейс базы либо укажи путь к клону вручную.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
