#!/usr/bin/env python3
"""Проверка, что документы рамок заполнены, а не остались заготовками.

Шаблон подсовывает слоты вида <заполни>. Без этой проверки проект живёт
с ними месяцами: агент читает `<НАЗВАНИЕ ПРОЕКТА>` и не считает это ошибкой.

Запуск:
    python3 .claude/check-frames.py            # строго: код 1 при находках
    python3 .claude/check-frames.py --soft     # мягко: печатает и выходит 0

Живёт в проекте, а не в плагине: CI запускает check.sh, а в CI никакого
Claude Code нет.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Слот шаблона: <что-то> и пустое <>. Отсекаем HTML-теги, ссылки и стрелки.
SLOT = re.compile(r"<[^<>\n]{0,80}>")
# Инлайновый код: `specs/<NNN>-<slug>/` — это описание формата пути,
# а не слот под заполнение. Вырезаем перед поиском.
CODE_SPAN = re.compile(r"`[^`\n]*`")
NOT_A_SLOT = re.compile(
    r"^<(/|!|br|hr|img|a\s|p>|b>|i>|code|pre|div|span|sup|sub|https?://|mailto:)",
    re.IGNORECASE,
)
WORD_SLOTS = ("заполни", "НАЗВАНИЕ ПРОЕКТА", "TODO", "FIXME")

# Документы рамок. Отсутствующий обязательный файл — тоже находка.
REQUIRED = [
    "AGENTS.md",
    "docs/constitution.md",
    "docs/definition-of-done.md",
    "docs/tech-stack.md",
    "docs/structure.md",
    "docs/product/mission.md",
    "docs/product/roadmap.md",
    "docs/product/glossary.md",
]
OPTIONAL = ["README.md", "docs/infrastructure.md", "docs/toolchain.md"]


def section(text: str, heading_re: str) -> str | None:
    """Тело раздела по регулярке заголовка, до следующего заголовка того же
    или более высокого уровня."""
    m = re.search(heading_re, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    level = len(m.group(0)) - len(m.group(0).lstrip("#"))
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{max(level, 1)}}}\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def has_content(body: str | None) -> bool:
    """В разделе есть хоть одна содержательная строка: не пустая, не
    комментарий, не слот, не строка таблицы из одних прочерков."""
    if not body:
        return False
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("<!--", "-->", "|---", "#")):
            continue
        stripped = SLOT.sub("", line).strip(" -*|\t")
        if any(w in line for w in WORD_SLOTS):
            continue
        if stripped:
            return True
    return False


def find_slots(text: str) -> list[tuple[int, str]]:
    """Слоты вне комментариев, блоков кода и инлайнового кода.

    Слово из WORD_SLOTS ищется уже по строке без угловых слотов, иначе
    `<заполни>` попадает в отчёт дважды.
    """
    out: list[tuple[int, str]] = []
    in_comment = False
    in_fence = False
    for i, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment or "<!--" in raw:
            in_comment = "-->" not in raw
            continue

        # Угловые слоты — только вне инлайнового кода: `specs/<NNN>-<slug>/`
        # это описание формата пути, заполнять там нечего.
        angle = [
            t for t in SLOT.findall(CODE_SPAN.sub("", raw))
            if not NOT_A_SLOT.match(t)
        ]
        out.extend((i, t) for t in angle)

        # Слова-маркеры однозначны, их ищем и внутри кода: в таблице команд
        # слот записан как `<заполни>`. Пропускаем те, что уже учтены выше.
        for w in WORD_SLOTS:
            if w in raw and not any(w in t for t in angle):
                out.append((i, w))
    return out


def main() -> int:
    soft = "--soft" in sys.argv
    findings: list[str] = []

    # 1. Обязательные документы на месте?
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            findings.append(f"{rel}: файл отсутствует")

    # 2. Незаполненные слоты.
    for rel in REQUIRED + OPTIONAL:
        p = ROOT / rel
        if not p.exists():
            continue
        for line, tok in find_slots(p.read_text(encoding="utf-8")):
            findings.append(f"{rel}:{line}: незаполненный слот {tok!r}")

    # 3. Разделы, пустота которых ломает работу агентов.
    mission = ROOT / "docs/product/mission.md"
    if mission.exists():
        text = mission.read_text(encoding="utf-8")
        if not has_content(section(text, r"^#+\s*Чего продукт НЕ делает.*$")):
            findings.append(
                "docs/product/mission.md: раздел антицелей пуст — без него "
                "агент расширяет объём работы из лучших побуждений"
            )

    stack = ROOT / "docs/tech-stack.md"
    if stack.exists():
        text = stack.read_text(encoding="utf-8")
        if not has_content(section(text, r"^#+\s*Запрещено тянуть.*$")):
            findings.append(
                "docs/tech-stack.md: список запрещённого пуст — единственное, "
                "что останавливает агента от установки популярной библиотеки"
            )

    gloss = ROOT / "docs/product/glossary.md"
    if gloss.exists():
        rows = [
            l for l in gloss.read_text(encoding="utf-8").splitlines()
            if l.strip().startswith("|")
            and not l.strip().startswith("|---")
            and not re.search(r"\|\s*(Термин|Поле)\s*\|", l)
        ]
        if not any(has_content(r) for r in rows):
            findings.append("docs/product/glossary.md: нет ни одного термина")

    # 4. Конституция: у каждого принципа помечен способ исполнения.
    const = ROOT / "docs/constitution.md"
    if const.exists():
        text = const.read_text(encoding="utf-8")
        body = section(text, r"^##\s*Принципы\s*$") or text
        for m in re.finditer(r"^###\s+(.+)$", body, re.MULTILINE):
            title = m.group(1).strip()
            rest = body[m.end():]
            nxt = re.search(r"^###\s", rest, re.MULTILINE)
            chunk = rest[: nxt.start()] if nxt else rest
            if not re.search(r"Исполнение:", chunk):
                findings.append(
                    f"docs/constitution.md: принцип «{title}» без строки "
                    "«Исполнение:» — непонятно, машинно он держится или советом"
                )
            elif not re.search(r"(машинно|только совет)", chunk):
                findings.append(
                    f"docs/constitution.md: принцип «{title}» без пометки "
                    "«машинно» или «только совет»"
                )

    if not findings:
        print("рамки: документы заполнены")
        return 0

    label = "предупреждение" if soft else "НЕ ПРОЙДЕНО"
    print(f"рамки ({label}): незакрытых пунктов {len(findings)}")
    for f in findings:
        print(f"  - {f}")
    if soft:
        print("  (мягкий режим: не блокирует)")
    return 0 if soft else 1


if __name__ == "__main__":
    sys.exit(main())
