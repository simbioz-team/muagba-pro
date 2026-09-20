#!/usr/bin/env python3
"""Разворачивает каркас в проект, ничего не перезаписывая.

Заменяет `cp -a -n`, и не из вкусовщины. Три причины, все найдены обкаткой на
живом проекте:

1. `cp -a -n` на coreutils 9.5 печатает «behavior of -n is non-portable and
   may change in future». Человек видит слово «warning» посреди чистой
   установки — ровно там, где только что прочитал, что здесь было затирание.
   Заменить на `--update=none` нельзя: его нет ни в coreutils до 9.3, ни в
   BSD, а база ставится на чужие машины.
2. `cp -v` печатает только скопированное. **Про пропущенное не печатает
   ничего** — ни строки, ни кода возврата. А важно как раз пропущенное: это и
   есть список совпадений, который нужно разобрать с человеком.
3. Разбор совпадений освобождает имена (существующий CLAUDE.md уезжает в
   AGENTS.md), и каркасный файл надо донести вторым проходом. Повторный
   запуск здесь безопасен и идемпотентен: занятое пропускается, свободное
   заполняется.

Печатает два списка — что легло и что пропущено как занятое. Пропущенное
идёт в конце и полностью: именно его показывают человеку.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from find_template import locate  # noqa: E402


def plan(src: Path, dst: Path) -> tuple[list[str], list[str], list[str]]:
    """(скопируется, совпадение, уже стоит). Пути относительные, для показа.

    «Уже стоит» — файл на месте и побайтово равен каркасному: это наш же
    предыдущий проход, а не чужое содержимое. Разделение нужно, чтобы второй
    проход после разбора не вываливал тридцать строк «занято» на то, что сам
    же и положил, и настоящее совпадение в этом шуме не потерялось."""
    fresh, differs, same = [], [], []
    for s in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = s.relative_to(src)
        d = dst / rel
        if not d.exists():
            fresh.append(rel.as_posix())
            continue
        try:
            identical = d.read_bytes() == s.read_bytes()
        except OSError:
            identical = False
        (same if identical else differs).append(rel.as_posix())
    return fresh, differs, same


def copy(src: Path, dst: Path, fresh: list[str]) -> None:
    for rel in fresh:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)


def main() -> int:
    ap = argparse.ArgumentParser(description="Каркас в проект, без перезаписи")
    ap.add_argument("dest", nargs="?", default=".", help="куда (по умолчанию .)")
    ap.add_argument("--from", dest="src", help="откуда (по умолчанию ищется сам)")
    ap.add_argument("--dry-run", action="store_true",
                    help="только показать, что будет: ничего не копировать")
    a = ap.parse_args()

    src = Path(a.src).expanduser().resolve() if a.src else locate()
    if src is None:
        print("не найден каркас: ни в репозитории базы, ни среди маркетплейсов.\n"
              "Подключи маркетплейс базы либо укажи путь через --from.",
              file=sys.stderr)
        return 1
    if not src.is_dir():
        print(f"не каталог: {src}", file=sys.stderr)
        return 1

    dst = Path(a.dest).expanduser().resolve()
    dst.mkdir(parents=True, exist_ok=True)
    fresh, differs, same = plan(src, dst)

    if not a.dry_run:
        copy(src, dst, fresh)

    head = "будет скопировано" if a.dry_run else "скопировано"
    print(f"каркас: {src}")
    print(f"{head}: {len(fresh)}")
    if same:
        print(f"уже стоит, совпадает с каркасом: {len(same)}")
    # Совпадения печатаются целиком и последними: это то, что человек должен
    # увидеть и разобрать. Молча оставить своё — такая же ошибка, как молча
    # затереть: дальше конвейер опирается на содержимое этих файлов.
    print(f"совпало по имени, содержимое своё: {len(differs)}")
    for rel in differs:
        print(f"  {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
