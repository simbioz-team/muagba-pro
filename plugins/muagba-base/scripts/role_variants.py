#!/usr/bin/env python3
"""Варианты ролей: одно тело — разные модель и effort.

Модель и effort субагента задаются только описанием роли: effort вызовом
Agent не передаётся. Поэтому `implementer` на Sonnet и `implementer-deep` на
Opus — две роли. Включать одну роль в другую Claude Code не умеет, а ручная
копия расходится: у narta `implementer-high` отстал от `implementer` базы на
несколько выпусков. Здесь копия собирается из исходника, `run.sh` сверяет.

  role_variants.py --build   записать варианты
  role_variants.py --check   выход 1, если вариант разошёлся с исходником

Выбор роли по шагу — правило координатора в `base-rules` (ADR-0020).
"""
from __future__ import annotations

import sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parent.parent / "agents"

VARIANTS = [
    {
        "source": "implementer",
        "name": "implementer-deep",
        "fields": {
            "description": (
                "Реализует одну задачу, дифф которой трогает опасное место — конкурентность "
                "и транзакции, миграцию со сменой существующих данных, платежи, вход и права, "
                "выкатку и CI, состояние формы, — или ищет причину неясного сбоя. Тот же "
                "порядок, что у implementer, на сильной модели. Задание начинается строкой "
                "«риск: …». Доработка по находкам не про опасное место, починка по логу, "
                "rebase — implementer."
            ),
            "model": "opus",
            "effort": "medium",
        },
        "preface": (
            "Тебе отдали **рискованный шаг**: ошибка здесь дорогая и тихая — гонка,\n"
            "порча данных, сломанная выкатка. Поэтому ты на сильной модели.\n"
            "\n"
            "**Если задача — найти причину сбоя** (`fix`, причина неясна):\n"
            "сначала воспроизведение — команда и её вывод; потом причина с\n"
            "доказательством — строка кода и почему она даёт этот вывод; потом\n"
            "тест, красный до правки. Правка без воспроизведения — догадка.\n"
            "Причина найдена, а правка механическая — доложи и предложи отдать\n"
            "правку `implementer`: найти дорого, исправить найденное — нет.\n"
        ),
    },
]

FIELD_ORDER = ("name", "description", "model", "effort")


def split(text: str) -> tuple[list[str], str]:
    if not text.startswith("---\n"):
        raise SystemExit("нет frontmatter")
    end = text.index("\n---\n", 4)
    return text[4:end].splitlines(), text[end + 5:]


def render(v: dict) -> str:
    src = AGENTS / f"{v['source']}.md"
    fm, body = split(src.read_text(encoding="utf-8"))
    fields = {"name": v["name"], **v["fields"]}
    out, done = [], set()
    for line in fm:
        key = line.split(":", 1)[0].strip()
        if key in fields:
            out.append(f"{key}: {fields[key]}")
            done.add(key)
        else:
            out.append(line)
    for key in FIELD_ORDER:
        if key in fields and key not in done:
            out.append(f"{key}: {fields[key]}")
    head = (f"<!-- Собрано role_variants.py из {v['source']}.md: не править руками. "
            f"Тело общее; меняй исходник и пересобирай. -->\n\n")
    return "---\n" + "\n".join(out) + "\n---\n\n" + head + v["preface"] + "\n" + body.lstrip("\n")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    bad = 0
    for v in VARIANTS:
        dst = AGENTS / f"{v['name']}.md"
        want = render(v)
        if mode == "--build":
            dst.write_text(want, encoding="utf-8")
        elif not dst.exists() or dst.read_text(encoding="utf-8") != want:
            print(f"{dst.name} разошёлся с {v['source']}.md: role_variants.py --build")
            bad = 1
    return bad


if __name__ == "__main__":
    sys.exit(main())
