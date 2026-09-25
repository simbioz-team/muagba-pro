#!/usr/bin/env python3
"""Проверка артефактов фич в `specs/NNN-slug/`: форма, трассировка, покрытие.

Форму, которую ничего не проверяет, не держит даже тот, кто её придумал. Это
не предположение: проект, где такую проверку завели, тут же поймал 23 находки
в собственных спеках, написанных часом раньше. Отсюда и эта проба.

Что проверяется:

- три файла на фичу: `spec.md`, `plan.md`, `tasks.md`;
- в спеке строка `- **status:** draft|active`;
- требования вида `- R1. КОГДА … СИСТЕМА ДОЛЖНА …`, у каждого «Проверка:»;
- в плане раздел «Сверка с конституцией» с таблицей, где названы **все**
  принципы конституции проекта — список читается из `docs/constitution.md`,
  а не зашит константой;
- задачи `- [ ] T001 … → результат` со ссылкой `[R1, R2]` и строкой «Файлы:»;
- отмеченная задача несёт, кто и когда её закрыл;
- у спеки со `status: active` — ни одной живой пометки «[ТРЕБУЕТ УТОЧНЕНИЯ»
  вне раздела «Решения по умолчанию», пустой раздел «Открытые вопросы», ни
  одного решения с «Спросить: да», и каждое требование покрыто задачей.

Требования ищутся в разделе «Требования», если он есть, иначе по всему
файлу. Иначе строка `- R1.` в любом другом разделе — например, в нумерации
решений — становилась требованием без «Проверка:» и без задачи; писатель
проекта narta обходил это кириллической «Р».

`draft` проверяется на форму, `active` — ещё и на готовность. Спеки нет —
проверять нечего, это не находка.

Основа — `check-specs.py`, написанный в проекте, который вёл на базе живую
разработку. Обобщены три места: список принципов берётся из конституции,
раздел про схему хранилища спрашивается только при признаке `storage`, пути
и корень определяются, а не задаются.

Запуск: `python3 check_specs.py [корень проекта]` — код 1 при находках.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MARK = "[ТРЕБУЕТ УТОЧНЕНИЯ"
REQ = re.compile(r"^- R(\d+)\.", re.M)
TASK = re.compile(r"^- \[( |x)\] (T\d{3}) (.*)$", re.M)
# Принцип конституции: «### I. Название» либо «## I. Название».
PRINCIPLE = re.compile(r"^#{2,3}\s+([IVX]+)\.\s+\S", re.M)


def section(text: str, title_re: str) -> str | None:
    m = re.search(rf"^## {title_re}.*$", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return m.group(0) + (rest[: nxt.start()] if nxt else rest)


def principles(root: Path) -> list[str]:
    """Римские номера принципов проекта. Пусто — сверять не с чем."""
    try:
        text = (root / "docs" / "constitution.md").read_text(encoding="utf-8")
    except OSError:
        return []
    seen: list[str] = []
    for num in PRINCIPLE.findall(text):
        if num not in seen:
            seen.append(num)
    return seen


def has_storage(root: Path) -> bool:
    """Признак `storage` из состояния настройки. Не объявлен — не требуем."""
    try:
        state = json.loads((root / ".claude" / "setup.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return bool((state.get("traits") or {}).get("storage"))


def open_questions(spec: str) -> list[str]:
    """Непустые строки раздела «Открытые вопросы» — без заголовка,
    комментариев и явного «нет»."""
    sec = section(spec, r"Открытые вопросы")
    if not sec:
        return []
    body = re.sub(r"<!--.*?-->", "", sec, flags=re.S).splitlines()[1:]
    items = [ln.strip() for ln in body if ln.strip()]
    if len(items) == 1 and re.fullmatch(r"[—–-]|нет\.?|пусто\.?", items[0], re.I):
        return []
    return items


def refs_of(body: str) -> set[int]:
    nums: set[int] = set()
    for r in re.findall(r"\[R([\dR,\s–-]+)\]", body):
        for part in re.split(r"[,\s]+", r.replace("R", "").strip()):
            if not part:
                continue
            if "–" in part or "-" in part:
                a, b = re.split(r"[–-]", part)
                if a.isdigit() and b.isdigit():
                    nums.update(range(int(a), int(b) + 1))
            elif part.isdigit():
                nums.add(int(part))
    return nums


def check_feature(d: Path, princ: list[str], storage: bool) -> list[str]:
    out: list[str] = []
    files = {n: d / f"{n}.md" for n in ("spec", "plan", "tasks")}
    for n, p in files.items():
        if not p.exists():
            out.append(f"{d.name}: нет {n}.md")
    if out:
        return out
    spec, plan, tasks = (files[n].read_text(encoding="utf-8") for n in ("spec", "plan", "tasks"))

    m = re.search(r"^- \*\*status:\*\* (draft|active)\b", spec, re.M)
    if not m:
        return [f"{d.name}/spec.md: нет строки `- **status:** draft|active`"]
    active = m.group(1) == "active"

    req_text = section(spec, r"Требования") or spec
    reqs = [int(x) for x in REQ.findall(req_text)]
    if not reqs:
        out.append(f"{d.name}/spec.md: нет требований вида `- R1. КОГДА … СИСТЕМА ДОЛЖНА …`")
    for chunk in re.split(r"^(?=- R\d+\.)", req_text, flags=re.M):
        mm = re.match(r"- R(\d+)\.", chunk)
        if mm and "Проверка:" not in chunk.split("\n- ", 1)[0]:
            out.append(f"{d.name}/spec.md: у R{mm.group(1)} нет «Проверка:»")

    if active:
        defaults = section(spec, r"Решения по умолчанию") or ""
        if MARK in (spec.replace(defaults, "") if defaults else spec):
            out.append(f"{d.name}/spec.md: status active, но есть «{MARK}» вне раздела "
                       "«Решения по умолчанию» — уточнить у человека или вернуть draft")
        if open_questions(spec):
            out.append(f"{d.name}/spec.md: status active, но раздел «Открытые вопросы» "
                       "не пуст — спросить человека или вернуть draft")
        if re.search(r"Спросить:\s*да\b", defaults, re.I):
            out.append(f"{d.name}/spec.md: status active, но в «Решения по умолчанию» есть "
                       "решение с «Спросить: да» — вопрос не задан, а спека объявлена готовой")
        if MARK in defaults and "заказчик" not in defaults:
            out.append(f"{d.name}/spec.md: пометки в «Решения по умолчанию» без записи о том, "
                       "кто снял правило «плана нет, пока остались пометки»")

    conf = section(plan, r"Сверка с конституцией")
    if conf is None:
        out.append(f"{d.name}/plan.md: нет раздела «## Сверка с конституцией»")
    elif princ:
        rows = [ln for ln in conf.splitlines() if ln.startswith("|")]
        for p in princ:
            if not any(re.search(rf"^\|[^|]*\b{p}\b", ln) for ln in rows):
                out.append(f"{d.name}/plan.md: в сверке нет принципа {p}")
    if storage and not re.search(r"^## Расхождения со\b", plan, re.M):
        out.append(f"{d.name}/plan.md: нет раздела «## Расхождения со <схемой>» "
                   "(у проекта есть хранилище — признак storage)")

    covered: set[int] = set()
    lines = tasks.splitlines()
    for i, ln in enumerate(lines):
        mt = TASK.match(ln)
        if not mt:
            continue
        tid, body = mt.group(2), mt.group(3)
        nums = refs_of(body)
        if not nums and "[R—]" not in body:
            out.append(f"{d.name}/tasks.md: {tid} не ссылается на требование `[R…]`")
        covered |= nums
        if "→" not in body:
            out.append(f"{d.name}/tasks.md: {tid} без «→ проверяемый результат»")
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not nxt.startswith("Файлы:"):
            out.append(f"{d.name}/tasks.md: у {tid} нет строки «Файлы:» сразу под задачей")
        if mt.group(1) == "x" and not re.search(r"\(\S+, \d{4}-\d{2}-\d{2}", body):
            out.append(f"{d.name}/tasks.md: {tid} отмечена, но без «(кто, ГГГГ-ММ-ДД)»")
    if active:
        missing = sorted(set(reqs) - covered)
        if missing:
            out.append(f"{d.name}/tasks.md: требования без задачи: "
                       + ", ".join(f"R{n}" for n in missing))
    return out


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    specs = root / "specs"
    dirs = sorted(p for p in specs.iterdir()
                  if p.is_dir() and re.match(r"\d{3}-", p.name)) if specs.is_dir() else []
    if not dirs:
        print("check-specs: фич нет, проверять нечего")
        return 0
    princ, storage = principles(root), has_storage(root)
    findings: list[str] = []
    for d in dirs:
        findings += check_feature(d, princ, storage)
    if findings:
        print("check-specs: находки")
        for f in findings:
            print("  -", f)
        return 1
    print(f"check-specs: ок ({len(dirs)} фич, принципов сверяется {len(princ)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
