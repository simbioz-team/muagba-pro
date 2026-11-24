#!/usr/bin/env python3
"""Правило жизни тестов миграций (T-1406): где живут, когда идут, когда удаляются.

Тесты переноса данных миграций копились годами: в блокирующем прогоне до 19.10.2026 шёл
тест миграции, после которой прошло 130–180 других. Такой тест откатывает общую базу
группы и дорог, а проверяет код, давно раскатанный на прод. Правило (решение владельца
19.10.2026, `docs/engineering/testing.md` §5.2):

1. Тест с откатом схемы базы живёт только в модуле `test_migration_<NNNN>…` того
   приложения, чью миграцию `NNNN` он проверяет.
2. Пока миграции нет в main — тест идёт в дневном прогоне.
3. Миграция попала в main (= прод, тегов релиза нет) — тест идёт только ночью
   (тяжёлый модуль реестра, `scripts/test_registry.py`).
4. После следующего мержа в main тест просрочен — проверка краснеет и требует удалить его.

«Попала в main» — файл миграции появился в первом по first-parent коммите ветки main.
«Пережила следующий мерж» — после этого коммита на first-parent main есть ещё хоть один.
Ветка main ищется так: `--main-ref`, переменная `MIGRATION_MAIN_REF`, затем `origin/main`
(checkout в CI), `github/main` (удалённый репозиторий у разработчиков), локальная `main`.

Откат схемы узнаётся по коду, а не по имени: использование `MigrationExecutor` или вызов
`call_command("migrate", …)` в тест-файле `django-api` (модуль `test*.py`/`tests*.py` или
любой файл в каталоге `tests/`).

Исключения — раздел `migration_test_exceptions` в `docs/engineering/test-registry.json`:
путь модуля → `why` и `decision` (ссылка на решение). Нарушение исключённого модуля
печатается предупреждением, а не ошибкой. Исключение без нарушения, исключение на
несуществующий модуль и исключение без причины или решения — ошибка: список не протухает.

Usage:
    python3 scripts/check_migration_tests.py                   # проверить (pre-commit)
    python3 scripts/check_migration_tests.py --require-main    # то же, без main — отказ (CI)
    python3 scripts/check_migration_tests.py --list            # состояние каждого модуля
    python3 scripts/check_migration_tests.py --main-ref github/main

Exit: 0 — чисто, 1 — нарушение, 2 — не удалось выполнить (нет main при --require-main,
неполная история, неразбираемая конфигурация).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "docs/engineering/test-registry.json"
DJANGO_ROOT = "services/django-api"
DOC_REF = "docs/engineering/testing.md §5.2"

#: Переменная окружения с именем ветки main; порядок поиска — в `resolve_main_ref`.
MAIN_REF_ENV = "MIGRATION_MAIN_REF"
DEFAULT_MAIN_REFS = ("origin/main", "github/main", "main")

#: Модуль теста миграции: `test_migration_0185.py`, `test_migration_0185_subject_areas.py`.
MIGRATION_TEST_NAME = re.compile(r"^test_migration_(\d{4})(?:_[a-z0-9_]+)?\.py$")

#: Тест-файл `django-api`: `test_x.py`, `tests_x.py`, `tests.py`, `test.py`.
_TEST_FILE = re.compile(r"^tests?(?:_.+)?\.py$")
_SKIP_PARTS = frozenset({"migrations", "__pycache__", ".venv", "node_modules"})

#: Состояния миграции относительно main, по возрастанию «зрелости».
PENDING, IN_MAIN, EXPIRED = "pending", "in_main", "expired"
_ORDER = {PENDING: 0, IN_MAIN: 1, EXPIRED: 2}


# --------------------------------------------------------------------- модули


def migration_test_parts(path: str) -> tuple[str, str] | None:
    """Приложение и номер миграции модуля `test_migration_<NNNN>…`.

    Args:
        path: путь модуля от корня репозитория.

    Returns:
        `(app, "NNNN")` — приложение берётся первым каталогом под `services/django-api`;
        None, если модуль не по шаблону или лежит вне приложения `django-api`.
    """

    parts = Path(path).parts
    root_parts = Path(DJANGO_ROOT).parts
    if len(parts) < len(root_parts) + 2 or parts[: len(root_parts)] != root_parts:
        return None
    found = MIGRATION_TEST_NAME.match(parts[-1])
    if not found:
        return None
    return parts[len(root_parts)], found.group(1)


def migration_guard(path: str) -> str | None:
    """Шаблон файла миграции, которую проверяет модуль `test_migration_<NNNN>…`.

    Он же сторожимый путь тяжёлого модуля (`scripts/test_registry.py`): новая миграция
    не требует ручной записи в раздел `heavy`.

    Args:
        path: путь модуля от корня репозитория.

    Returns:
        Glob от корня — `services/django-api/<app>/migrations/<NNNN>_*.py`; None для
        модуля не по шаблону.
    """

    parts = migration_test_parts(path)
    if parts is None:
        return None
    app, number = parts
    return f"{DJANGO_ROOT}/{app}/migrations/{number}_*.py"


def scan_test_files(root: Path = ROOT) -> list[str]:
    """Тест-файлы `django-api`: модули `test*.py`/`tests*.py` и всё в каталогах `tests/`.

    Каталог `tests/` берётся целиком: базовый класс с откатом схемы в `tests/_base.py`
    иначе прошёл бы мимо проверки.

    Args:
        root: корень репозитория.

    Returns:
        Пути от корня репозитория, отсортированные.
    """

    base = root / DJANGO_ROOT
    found: list[str] = []
    if not base.is_dir():
        return found
    for path in base.rglob("*.py"):
        rel = path.relative_to(root)
        if _SKIP_PARTS & set(rel.parts):
            continue
        if _TEST_FILE.match(path.name) or "tests" in rel.parts[:-1]:
            found.append(rel.as_posix())
    return sorted(found)


def schema_rollback_line(source: str) -> int | None:
    """Строка, на которой тест трогает схему базы миграциями; None — не трогает.

    Признаки — использование `MigrationExecutor` (импорт, имя, атрибут) и вызов
    `call_command("migrate", …)`. Разбор синтаксиса, а не поиск текста: упоминание в
    docstring или комментарии нарушением не считается.

    Args:
        source: текст модуля.

    Returns:
        Номер первой такой строки.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    lines: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and any(alias.name == "MigrationExecutor" for alias in node.names)
            or isinstance(node, ast.Name)
            and node.id == "MigrationExecutor"
            or isinstance(node, ast.Attribute)
            and node.attr == "MigrationExecutor"
        ):
            lines.append(node.lineno)
        elif isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if (
                name == "call_command"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "migrate"
            ):
                lines.append(node.lineno)
    return min(lines) if lines else None


# ------------------------------------------------------------------------- git


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout


def resolve_main_ref(explicit: str | None = None, root: Path = ROOT) -> str | None:
    """Найти ветку main: явная → `MIGRATION_MAIN_REF` → origin/main → github/main → main.

    Args:
        explicit: имя из командной строки; если задано, другие не пробуются.
        root: корень репозитория.

    Returns:
        Имя ссылки, которая разрешается в коммит; None — ни одной.
    """

    wanted = explicit or os.environ.get(MAIN_REF_ENV) or ""
    candidates = (wanted,) if wanted else DEFAULT_MAIN_REFS
    for ref in candidates:
        if _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            return ref
    return None


def is_shallow(root: Path = ROOT) -> bool:
    """Неполная ли история: на ней первое появление файла в main врёт."""

    return (_git(root, "rev-parse", "--is-shallow-repository") or "").strip() == "true"


@dataclass(frozen=True)
class MainState:
    """Где миграция относительно main.

    Attributes:
        state: `pending` — в main её нет; `in_main` — пришла последним мержем;
            `expired` — после её мержа в main был ещё хоть один.
        commit: первый first-parent коммит main с файлом миграции; пусто для `pending`.
        later: сколько first-parent коммитов main после него.
        migration: файл миграции, по которому вынесено состояние.
    """

    state: str
    commit: str = ""
    later: int = 0
    migration: str = ""


def migration_state(migrations: list[str], ref: str, root: Path = ROOT) -> MainState:
    """Состояние миграции(-й) одного номера относительно ветки main.

    Несколько файлов одного номера (так бывает после слияния веток) судятся по самому
    свежему: пока хоть один не в main, тест ещё нужен днём.

    Args:
        migrations: файлы миграций от корня репозитория.
        ref: ветка main.
        root: корень репозитория.

    Returns:
        Наименее зрелое состояние среди файлов.
    """

    best: MainState | None = None
    for migration in migrations:
        # -m + --first-parent: у мержа в main дифф против первого родителя, то есть
        # «что этот мерж принёс в main». --no-renames: переименование — тоже появление.
        out = _git(
            root,
            "log",
            "--first-parent",
            "-m",
            "--no-renames",
            "--diff-filter=A",
            "--format=%H",
            ref,
            "--",
            migration,
        )
        commits = (out or "").split()
        if not commits:
            current = MainState(state=PENDING, migration=migration)
        else:
            first = commits[-1]
            count = _git(
                root, "rev-list", "--count", "--first-parent", f"{first}..{ref}"
            )
            later = int((count or "0").strip() or 0)
            current = MainState(
                state=EXPIRED if later else IN_MAIN,
                commit=first,
                later=later,
                migration=migration,
            )
        if best is None or _ORDER[current.state] < _ORDER[best.state]:
            best = current
    return best or MainState(state=PENDING)


def _match_files(pattern: str, files: list[str]) -> list[str]:
    prefix, _, suffix = pattern.partition("*")
    return sorted(
        f
        for f in files
        if f.startswith(prefix) and f.endswith(suffix) and "/" not in f[len(prefix) :]
    )


def tree_migrations(root: Path = ROOT) -> list[str]:
    """Файлы миграций `django-api` в рабочем дереве (не по индексу git: новая миграция
    ещё может быть не добавлена)."""

    base = root / DJANGO_ROOT
    if not base.is_dir():
        return []
    return sorted(
        p.relative_to(root).as_posix()
        for p in base.glob("*/migrations/[0-9][0-9][0-9][0-9]_*.py")
    )


def pending_migration_tests(
    paths: list[str], root: Path = ROOT, ref: str | None = None
) -> frozenset[str] | None:
    """Модули `test_migration_<NNNN>…`, чьей миграции ещё нет в main: им место днём.

    Args:
        paths: пути тест-модулей от корня репозитория (лишние отбрасываются).
        root: корень репозитория.
        ref: ветка main; None — искать по порядку `resolve_main_ref`.

    Returns:
        Пути модулей; None — main не найдена или история неполная, состояние неизвестно.
    """

    ref = resolve_main_ref(ref, root)
    if ref is None or is_shallow(root):
        return None
    files = tree_migrations(root)
    pending: set[str] = set()
    for path in paths:
        guard = migration_guard(path)
        if guard is None:
            continue
        found = _match_files(guard, files)
        if not found or migration_state(found, ref, root).state == PENDING:
            pending.add(path)
    return frozenset(pending)


# --------------------------------------------------------------------- проверка


@dataclass
class Report:
    """Итог проверки.

    Attributes:
        problems: нарушения — проверка красная.
        warnings: нарушения под исключением и неизвестное состояние — не красят.
        states: путь модуля `test_migration_<NNNN>…` → состояние его миграции.
        ref: ветка main, по которой судили; None — не найдена.
    """

    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    states: dict[str, MainState] = field(default_factory=dict)
    ref: str | None = None


def load_exceptions(root: Path = ROOT) -> dict[str, dict]:
    """Раздел `migration_test_exceptions` конфигурации реестра тестов."""

    path = root / CONFIG_REL
    if not path.is_file():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✗ конфигурация не разбирается: {path} — {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return config.get("migration_test_exceptions") or {}


def audit(
    root: Path = ROOT,
    ref: str | None = None,
    exceptions: dict[str, dict] | None = None,
) -> Report:
    """Проверить правило жизни тестов миграций.

    Args:
        root: корень репозитория.
        ref: ветка main; None — сроки жизни не проверяются (только место теста).
        exceptions: исключения `путь → {why, decision}`.

    Returns:
        Отчёт: нарушения, предупреждения и состояние каждого модуля теста миграции.
    """

    exceptions = exceptions or {}
    report = Report(ref=ref)
    violations: dict[str, list[str]] = {}
    files = scan_test_files(root)
    migrations = tree_migrations(root)

    for path in files:
        try:
            source = (root / path).read_text(encoding="utf-8")
        except OSError:
            continue
        guard = migration_guard(path)
        line = schema_rollback_line(source)
        if line is not None and guard is None:
            violations.setdefault(path, []).append(
                f"`{path}` откатывает схему базы (строка {line}) вне модуля "
                "`test_migration_<NNNN>…`: тест переноса данных миграции живёт только "
                f"в таком модуле своего приложения ({DOC_REF})"
            )
        if guard is None:
            continue
        found = _match_files(guard, migrations)
        if not found:
            report.problems.append(
                f"`{path}` назван по миграции, которой нет в дереве (`{guard}`): "
                "номер в имени модуля обязан совпадать с миграцией, которую он проверяет"
            )
            continue
        if ref is None:
            continue
        state = migration_state(found, ref, root)
        report.states[path] = state
        if state.state == EXPIRED:
            violations.setdefault(path, []).append(
                f"`{path}` просрочен: миграция `{state.migration}` пришла в {ref} "
                f"коммитом {state.commit[:10]}, после него в main ещё {state.later} "
                f"мерж(ей) — тест удалить ({DOC_REF})"
            )

    for path, messages in violations.items():
        entry = exceptions.get(path)
        if entry is None:
            report.problems.extend(messages)
            continue
        for message in messages:
            report.warnings.append(
                f"{message} — под исключением {CONFIG_REL}: {entry.get('decision', '')}"
            )

    known = set(files)
    for path, entry in exceptions.items():
        entry = entry or {}
        if path not in known:
            report.problems.append(
                f"исключение `{path}` в {CONFIG_REL} называет несуществующий тест-модуль — "
                "убрать исключение"
            )
            continue
        if not entry.get("why") or not entry.get("decision"):
            report.problems.append(
                f"исключение `{path}` без `why` или `decision` — причина и ссылка на "
                "решение обязательны"
            )
        if path not in violations and (
            ref is not None or migration_guard(path) is None
        ):
            report.problems.append(
                f"исключение `{path}` ничего не исключает — модуль правилу не нарушает, "
                "убрать исключение"
            )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--main-ref", help="ветка main (по умолчанию — поиск по порядку)"
    )
    parser.add_argument(
        "--require-main",
        action="store_true",
        help="без ветки main или на неполной истории — отказ (для CI)",
    )
    parser.add_argument("--list", action="store_true", help="состояние каждого модуля")
    args = parser.parse_args()

    ref = resolve_main_ref(args.main_ref)
    shallow = ref is not None and is_shallow()
    if ref is None or shallow:
        why = (
            "ветка main не найдена ("
            + (
                args.main_ref
                or os.environ.get(MAIN_REF_ENV)
                or ", ".join(DEFAULT_MAIN_REFS)
            )
            + ")"
            if ref is None
            else "история git неполная (shallow) — первое появление миграции в main неизвестно"
        )
        if args.require_main:
            print(f"✗ {why}; в CI нужен fetch main с полной историей", file=sys.stderr)
            return 2
        print(f"⚠ {why}: сроки жизни тестов миграций не проверены", file=sys.stderr)
        ref = None

    report = audit(ref=ref, exceptions=load_exceptions())

    if args.list:
        for path, state in sorted(report.states.items()):
            where = {
                PENDING: "миграции нет в main — идёт днём",
                IN_MAIN: f"в main с {state.commit[:10]} — идёт ночью; следующий мерж в main его просрочит",
                EXPIRED: f"просрочен: после мержа {state.commit[:10]} ещё {state.later}",
            }[state.state]
            print(f"{path}: {where}")

    for warning in report.warnings:
        print(f"⚠ {warning}", file=sys.stderr)
    for problem in report.problems:
        print(f"✗ {problem}", file=sys.stderr)
    if report.problems:
        return 1
    print(
        f"OK: тесты миграций по правилу ({len(report.states)} модулей test_migration_*, "
        f"main = {ref or 'не проверялась'}, исключений {len(report.warnings)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
