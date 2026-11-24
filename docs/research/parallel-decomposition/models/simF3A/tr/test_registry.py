#!/usr/bin/env python3
"""Реестр тестов: среда → группа → тест. Единственный источник правды о том, что запускать.

Э1 из `docs/architecture/algorithms/design-test-orchestration.md`. Заменил три разошедшихся
места, каждое из которых знало свой кусок: шаги CI (шесть групп django, фронт одной кучей),
`scripts/run-all-tests.sh` (четыре набора своими лейблами, без `invites`) и поглощённый
`scripts/ci_test_groups.py` (раскладка только внутри `courses/`). Расхождение между ними не
гипотетическое: больше тысячи тестов не запускались нигде — ml-llm, `user_auth`, `invites`,
ml-bkt, web-import.

Три вещи сделаны иначе, чем в предшественнике, и каждая — из замера, а не из вкуса:

1. **Верхний уровень — среда, а не контейнер.** `scripts` и e2e идут на хосте: браузеры
   playwright лежат в корне репозитория, а `localhost/study` изнутри контейнера не
   резолвится в nginx.
2. **Метка нормализуется перед сравнением.** Правило `\\bsaga\\b` не находило `saga` в
   `courses.tests_saga_gating`: подчёркивание — словесный символ, границы слова там нет, и
   тест гейтов саги молча лежал в свалке. После нормализации граница — идиома
   `(?:^|_)x(?:_|$)`, одинаково работающая на пакетах, файлах и компонентах React.
3. **Словарь групп общий для всех сред.** `--group billing` поднимает и джанговские тесты,
   и ml-llm, и фронт: смысловое изменение пересекает сервисы, а свой словарь на среду
   сделал бы `--group` неоднозначным.

Свалка `core` остаётся catch-all — иначе новый тест выпал бы из прогона молча, а это
нарушение требования «полный прогон запускает всё». Но её размер зафиксирован храповиком в
`docs/engineering/test-registry.json`: расти нельзя, убывать можно.

Usage:
    python3 scripts/test_registry.py --list                    # раскладка целиком
    python3 scripts/test_registry.py --list --env ml-llm       # раскладка одной среды
    python3 scripts/test_registry.py --check                   # сверка (для CI)
    python3 scripts/test_registry.py --labels django-api saga  # метки для раннера
    python3 scripts/test_registry.py --envs                    # перечислить среды
    python3 scripts/test_registry.py --json                    # машинный вывод
    python3 scripts/test_registry.py --heavy                   # тяжёлые модули и их стражи
    python3 scripts/test_registry.py --heavy --day changed.txt # что из тяжёлого пойдёт днём
    python3 scripts/test_registry.py --labels django-api core --day changed.txt
    python3 scripts/test_registry.py --ci-groups --day changed.txt  # группы CI (ADR-117)

Тяжёлые модули (T-1404). Модуль с пометкой `fresh_db_only` или из раздела `heavy`
конфигурации — тяжёлый: дневной прогон CI его пропускает, если ни один из его
сторожимых путей не тронут, а ночной гоняет всё. `--day ФАЙЛ` включает дневной отбор:
в файле — изменённые пути от корня репозитория, по одному на строку.

Тест миграции (T-1406) — модуль `test_migration_<NNNN>…`: пока его миграции нет в main,
он не тяжёлый и идёт днём всегда; миграция в main — тяжёлый, сторожит свою миграцию
(страж выводится из имени, запись в `heavy` не нужна). Ветка main — как у
`scripts/check_migration_tests.py` (`MIGRATION_MAIN_REF`, затем origin/main, github/main,
main); не найдена — тесты миграций днём идут все.

Порог по настенному времени (T-1407) — только в тяжёлом модуле: `--check` краснеет на
дневном модуле `django-api`, который и читает часы `time`, и сравнивает на «меньше/больше».

Exit: 0 — чисто, 1 — сверка не прошла, 2 — не удалось выполнить.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_migration_tests import (  # noqa: E402
    migration_guard,
    pending_migration_tests,
    resolve_main_ref,
)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "docs/engineering/test-registry.json"


# --------------------------------------------------------------------------- среды


@dataclass(frozen=True)
class Environment:
    """Где и чем исполняется набор тестов.

    Attributes:
        key: имя среды в командной строке.
        where: `container` или `host` — от этого зависит, кто вообще может её запустить.
        runner: чем гоняются тесты; человеку для отчёта, раннеру для сборки команды.
        service: имя сервиса compose; None для хостовых сред.
        root: корень среды от корня репозитория — относительно него строится метка.
        test_roots: подкаталоги внутри `root`, где ищутся тесты.
        label_style: `django` (точечная метка) или `path` (путь от `root`).
        default: входит ли в полный прогон без явного флага.
    """

    key: str
    where: str
    runner: str
    service: str | None
    root: str
    test_roots: tuple[str, ...]
    label_style: str
    default: bool = True


#: Порядок значим: он же порядок исполнения — дешёвое раньше дорогого, чтобы падение
#: всплывало быстро. Порядок фиксирован здесь, а не вычисляется по замеренной длительности:
#: недетерминированный порядок сломал бы воспроизводимость возобновления.
ENVIRONMENTS: tuple[Environment, ...] = (
    Environment(
        key="scripts",
        where="host",
        runner="unittest",
        service=None,
        root=".",
        test_roots=("scripts/tests",),
        label_style="django",
    ),
    Environment(
        key="ml-bkt",
        where="container",
        runner="pytest",
        service="ml-bkt",
        root="services/ml-bkt",
        test_roots=("tests",),
        label_style="path",
    ),
    Environment(
        key="web-import",
        where="container",
        runner="pytest",
        service="web-import",
        root="services/web-import",
        test_roots=("tests",),
        label_style="path",
    ),
    Environment(
        key="ml-llm",
        where="container",
        runner="pytest",
        service="ml-llm",
        root="services/ml-llm",
        test_roots=("tests",),
        label_style="path",
    ),
    Environment(
        key="frontend",
        where="container",
        runner="jest",
        service="frontend",
        root="services/frontend",
        test_roots=("__tests__",),
        label_style="path",
    ),
    Environment(
        key="django-api",
        where="container",
        runner="manage.py test",
        service="django-api",
        root="services/django-api",
        # Корни — по INSTALLED_APPS, а не по тому, где тесты нашлись сегодня.
        # `system_core` тестов пока не имеет, и корень здесь — страховка: первый
        # написанный там тест обязан попасть в прогон, а не стать сиротой. Обратный
        # пример рядом: `run-all-tests.sh` гоняет `document_storage`, которого в
        # дереве уже нет.
        test_roots=("courses", "user_auth", "invites", "system_core"),
        label_style="django",
    ),
    Environment(
        key="e2e",
        where="host",
        runner="playwright",
        service=None,
        root="services/frontend",
        test_roots=("tests/e2e",),
        label_style="path",
        default=False,
    ),
)

ENV_BY_KEY = {env.key: env for env in ENVIRONMENTS}


# ------------------------------------------------------------------- нормализация


#: Граница camelCase: `lessonStreaming` → `lesson_Streaming`. Применяется ДО приведения к
#: нижнему регистру, иначе граница исчезает.
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

#: Вторая граница — конец группы заглавных перед словом: `modeBChat` → `mode_B_Chat`,
#: `HTTPServer` → `HTTP_Server`. Без неё `modeBChat` схлопывается в `mode_bchat`, и правило
#: `mode_b` промахивается ровно так же, как промахивалось `\\bsaga\\b`. Замерено, не угадано.
_CAMEL_RUN = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")

#: Разделители, приводимые к подчёркиванию. Дефис сюда входит, подчёркивание — НЕТ:
#: замена `_` на что-либо ломает половину правил (`usage_ledger`, `topic_content`).
_SEPARATORS = re.compile(r"[.\\/ \-]+")

_UNDERSCORES = re.compile(r"_+")

#: Составные расширения снимаются целиком: `.test.tsx` — не `.tsx` с точкой посередине.
_EXTENSIONS = (
    ".test.tsx",
    ".test.ts",
    ".spec.tsx",
    ".spec.ts",
    ".test.js",
    ".spec.js",
    ".tsx",
    ".ts",
    ".py",
)


def strip_extension(name: str) -> str:
    """Снять расширение, включая составное (`.test.tsx`)."""

    for suffix in _EXTENSIONS:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def normalize(label: str) -> str:
    """Привести метку к одному алфавиту: нижний регистр, разделитель — подчёркивание.

    Причина существования: искать слова в метке, где разделители неоднородны, нельзя.
    `lessonStreaming`, `courses.tests_saga_gating` и `TopicApproveButton` — три разных
    способа записать одно и то же, и регулярка со `\\b` видит их по-разному.

    Args:
        label: метка в любом виде — путь, django-label, имя компонента.

    Returns:
        Нормализованную метку: `lesson_streaming`, `courses_tests_saga_gating`,
        `topic_approve_button`.
    """

    text = strip_extension(label)
    text = _CAMEL_RUN.sub("_", _CAMEL.sub("_", text))
    text = _SEPARATORS.sub("_", text)
    text = _UNDERSCORES.sub("_", text.lower())
    return text.strip("_")


def _boundary(pattern: str) -> re.Pattern[str]:
    """Обернуть правило границей, где словом считается кусок между подчёркиваниями.

    Хвостовое `s?` — не косметика: единственное и множественное число дают промах целым
    классом. `tariffs`, `modals`, `distractors`, `learning_tasks`, `embedded_items` мимо
    правил `tariff`, `modal`, `distractor`, `learning_task`, `embedded_item` — восемь
    модулей в свалке на одном этом. Дешевле снять оптовым правилом, чем перечислять формы.
    """

    return re.compile(rf"(?:^|_)(?:{pattern})s?(?:_|$)")


# ------------------------------------------------------------------------- правила


#: Порядок значим: побеждает ПЕРВОЕ совпавшее правило. Не совпало ни одно — `core`.
#: Правила пишутся уже в нормализованном алфавите (snake_case, нижний регистр).
GROUP_RULES: tuple[tuple[str, str], ...] = (
    (
        # Сверки расхождения и реестры — тесты инструментов, а не продукта. Перечислены
        # поимённо, потому что общего слова у них нет: `check` встречается и в продуктовых
        # метках (`test_coverage_check`), и правило по нему утащило бы чужое.
        "governance",
        r"drift|module_coverage|module_readme|module_registry|module_boundaries|module_map|invariant_coverage"
        r"|invariant_duplication"
        r"|doc_links|docs_index|doc_freshness|doc_status|api_doc_coverage"
        r"|frontend_encoding|ui_terminology|coevolution|diff_coverage|mutants"
        r"|test_discipline|test_location|loc_budget|manifest_provenance|stack_facts"
        r"|test_registry|run_tests|process_map|zone_map|fixture_imports",
    ),
    (
        # `course_price` — окно цены курса (T-1518): его читают продажа курса и оплаченное
        # прохождение, тесты гоняются с ними.
        "billing",
        r"billing|usage_costs|usage_ledger|usage_context|usage|tariff|subscription|paid_passage"
        r"|payment|invoice|balance|unit|pricing|fx|cbr|exchange|ledger|cost|money|seat|quota"
        r"|course_price",
    ),
    (
        "explorer",
        r"explorer",
    ),
    (
        "wording",
        r"wording|naming|name_guard|formulation|morph|terminology",
    ),
    (
        # `course_pipeline` — оркестрация гейтов, вынесенная из saga (T-1502): без него
        # тесты пакета ушли бы по слову `pipeline` в `structure`. Пакет `publication`
        # (views публикации и модерации, вынесены из saga, Э2.4) ловится словом
        # `publication`: его тесты остаются в группе `saga`, где гонялись до переноса.
        # `methodology_params` — числа гейтов 1, 3, 4 курса (T-2251): их тесты гоняют
        # reopen и снятие с публикации, место им рядом с гейтами.
        "saga",
        r"saga|course_pipeline|lifecycle|gating|gate\d*|coordinator|reopen|moderation"
        r"|publication|publish|methodology_params",
    ),
    (
        # Выделено из свалки замером: дизайн предполагал, что vision там есть, — есть.
        "vision",
        r"vision|describe_image|gigachat_vlm|gigachat_config|vlm|downscale",
    ),
    (
        # Шлюз к модели. Тот самый шов, который стерегут Т1 и Т2, — у него свои тесты и
        # в ml-llm, и в django, и падать они должны вместе.
        "transport",
        r"ml_transport|transport|client_factory|call_param|llm_failure|llm_json_parse"
        r"|sampling|runtime_config|runtime_profile|prompt_versioning|tiktoken"
        r"|ml_boundary|f6a|f6b|f6c",
    ),
    (
        "lessons",
        r"lesson|dialogue|rule_engine|grader|grading|mode_a|mode_b|tutor|understanding"
        r"|streaming|stream|chat|turn|quoting|session|judge|hint|action|recurrence"
        r"|ir_writes|interaction_record",
    ),
    (
        "documents",
        r"document|parsing|parser|chunk|chunker|web_import|import|upload|extract"
        r"|docx|pdf|smoke",
    ),
    (
        "banks",
        r"bank|learning_task|embedded|embeddeditem|itemcontent|diagnostic"
        r"|item_template|task_class|distractor|solvability|item|question|answer"
        r"|attempt|task|exam_codifier|exam_tasks|exam_bank_import"
        r"|exam_solver|exam_methodologist_queue",
    ),
    (
        "content",
        r"content|topic_content|section|summary|richtext|latex|lexical|editor"
        r"|autosave|node_deletion|version_label",
    ),
    (
        "structure",
        r"structure|brief|generation|generator|generate|pipeline|phase\d*|augment"
        r"|bloom|outline|regen",
    ),
    (
        "graph",
        r"ksa|graph|graph3|mastery|matching|match|ukgs|tkml|competency|competencies"
        r"|track|gap|prereq|prerequisite|dependency|dependencies|bkt|knowledge|topic"
        r"|discipline|subject_area|planner|relation|attitude|description|origin",
    ),
    (
        "platform",
        r"admin|auth|access|role|permission|invite|space|statistic|feedback|bug"
        r"|openapi|dev_auth|command|telemetry|monitor|health|dataset_export"
        r"|synthetic_ir|migration|settings|logging|cache|redis|celery|user|student"
        r"|dashboard|profile|pace|forecast|debug|questionnaire|notification|endpoint"
        r"|owner|registration|api_error|audit|metric",
    ),
    (
        "ui",
        r"modal|layout|button|shell|toast|tooltip|form|confirm|split|panel|tab|menu"
        r"|dropdown|badge|chip|spinner|overlay|icon|theme|style|css|dnd|reorder"
        r"|sticky_scroll|polling_refresh|optimistic_version|tour|bulk_bar|pill",
    ),
)

CATCH_ALL = "core"

GROUP_TITLES = {
    "governance": "сверки расхождения, реестры, дисциплина тестов",
    "vision": "описание изображений, GigaChat VLM",
    "transport": "шлюз к модели: транспорт, профили, промпты",
    "billing": "тарифы, обменник юнитов, журнал расхода",
    "explorer": "Explorer — подбор и предложения",
    "wording": "правила формулирования",
    "saga": "сага, гейты, жизненный цикл курса",
    "lessons": "рантайм уроков А и Б, диалоговый движок",
    "documents": "разбор и импорт материалов",
    "banks": "банки заданий, диагностика, шаблоны",
    "content": "содержание темы, разделы, богатый текст",
    "structure": "генерация структуры курса",
    "graph": "граф знаний, мастерство, матчинг, треки",
    "platform": "доступ, статистика, служебное, инфраструктура",
    "ui": "обобщённые компоненты интерфейса",
    "core": "всё, что не подошло ни под одно правило",
}

GROUPS: tuple[str, ...] = tuple(name for name, _ in GROUP_RULES) + (CATCH_ALL,)

_COMPILED: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, _boundary(pattern)) for name, pattern in GROUP_RULES
)


def classify(key: str, exceptions: dict[str, str] | None = None) -> str:
    """Определить группу нормализованной метки.

    Args:
        key: метка, уже прошедшая `normalize`.
        exceptions: карта `метка → группа`, которая бьёт правила. Для модулей, чьё имя
            врёт о содержании.

    Returns:
        Имя группы; `core`, если не совпало ни одно правило.
    """

    if exceptions and key in exceptions:
        return exceptions[key]
    for name, pattern in _COMPILED:
        if pattern.search(key):
            return name
    return CATCH_ALL


#: Модули, проверяющие ПЕРЕХОД состояний схемы. На сохранённой базе (`--keepdb`) они
#: проверяют не то, что обещают, и остаются зелёными — то есть врут ровно тем способом,
#: против которого заведён весь набор сверок. Реестр их помечает; кто переиспользует базу,
#: обязан их не запускать и перенести в ближайший полный прогон.
_FRESH_DB = _boundary(r"migration\d*|migrate|schema_change|backfill")


def requires_fresh_database(key: str, extra: frozenset[str] = frozenset()) -> bool:
    """Обязателен ли этому модулю прогон на заново построенной базе.

    Замер соседней сессии 10.09.2026: построение тестовой базы django — 291 миграция,
    160 таблиц, 22 минуты, и это происходит до первого исполненного теста. Отсюда
    неизбежность `--keepdb` при возобновлении и отсюда же этот список: переиспользование
    базы дёшево ровно до тех пор, пока на ней не гоняют тесты самой схемы.

    Args:
        key: нормализованная метка модуля.
        extra: метки, добавленные вручную через конфигурацию.

    Returns:
        True, если модуль имеет смысл только на свежей базе.
    """

    return key in extra or bool(_FRESH_DB.search(key))


# ------------------------------------------------------------------------ тяжёлые


#: Среда, чей раннер CI умеет отбирать тяжёлые модули (`scripts/ci_django_test_groups.sh`).
#: Пометка в другой среде ничего бы не меняла — сверка такую отвергает, а не терпит молча.
HEAVY_ENVS = frozenset({"django-api"})


def guard_pattern(pattern: str) -> re.Pattern[str]:
    """Скомпилировать шаблон сторожимого пути в регулярку.

    Семантика glob, а не fnmatch: `*` не переходит через `/`, `**` — переходит. В
    fnmatch `*` съедал бы косую черту, и `courses/*.py` сторожил бы всё дерево.

    Args:
        pattern: путь от корня репозитория, допускаются `*`, `**`, `?`.

    Returns:
        Регулярку, совпадающую с путём целиком.
    """

    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


@dataclass(frozen=True)
class Heavy:
    """Тяжёлый модуль: в дневном прогоне идёт, только если тронут сторожимый путь.

    Attributes:
        unit: сам модуль.
        why: почему он тяжёлый — `fresh_db_only` (пометка по имени модуля) или
            причина из конфигурации.
        guards: сторожимые пути; первым всегда идёт файл самого модуля — правка теста
            обязана его запустить.
    """

    unit: Unit
    why: str
    guards: tuple[str, ...]

    def touched_by(self, changed: list[str]) -> list[str]:
        """Какие из изменённых путей попали под сторожимые шаблоны."""

        compiled = [guard_pattern(g) for g in self.guards]
        return [path for path in changed if any(p.match(path) for p in compiled)]


def heavy_units(
    units: list[Unit], config: dict, pending: frozenset[str] = frozenset()
) -> list[Heavy]:
    """Отобрать тяжёлые модули: пометка `fresh_db_only` плюс раздел `heavy` конфигурации.

    Ключ раздела `heavy` — путь модуля от корня репозитория: он уникален во всех средах и
    сам по себе первый сторожимый путь. Модулю `test_migration_<NNNN>…` страж — файл его
    миграции — добавляется сам (T-1406).

    Args:
        units: полная раскладка.
        config: конфигурация реестра (`docs/engineering/test-registry.json`).
        pending: модули тестов миграций, которых ещё нет в main (T-1406): они не
            тяжёлые — идут днём всегда.

    Returns:
        Тяжёлые модули в порядке раскладки.
    """

    declared: dict = config.get("heavy") or {}
    fresh_extra = frozenset(config.get("fresh_db_only") or ())
    found: list[Heavy] = []
    for unit in units:
        if unit.path in pending:
            continue
        entry = declared.get(unit.path)
        # Пометка по имени значит что-то только там, где есть база и раннер отбора:
        # `scripts/tests/test_check_migration_tests.py` базы не трогает.
        fresh = unit.env in HEAVY_ENVS and requires_fresh_database(
            unit.key, fresh_extra
        )
        if entry is None and not fresh:
            continue
        guards = [unit.path, *((entry or {}).get("guards") or ())]
        own = migration_guard(unit.path)
        if own is not None:
            guards.append(own)
        why = "fresh_db_only" if fresh else str((entry or {}).get("why") or "heavy")
        found.append(Heavy(unit=unit, why=why, guards=tuple(dict.fromkeys(guards))))
    return found


def daytime_skipped(heavy: list[Heavy], changed: list[str] | None) -> set[str]:
    """Пути тяжёлых модулей, которые дневной прогон пропускает.

    Args:
        heavy: тяжёлые модули.
        changed: изменённые пути от корня репозитория; None — изменения неизвестны.

    Returns:
        Пути модулей вне дневного прогона. Неизвестные изменения не пропускают ничего:
        ошибиться в сторону лишнего прогона дешевле, чем в сторону пропуска.
    """

    if changed is None:
        return set()
    return {h.unit.path for h in heavy if not h.touched_by(changed)}


def check_heavy(
    units: list[Unit], config: dict, tree_files: list[str] | None = None
) -> list[str]:
    """Сверка раздела `heavy`. Возвращает список нарушений.

    Args:
        units: полная раскладка.
        config: конфигурация реестра.
        tree_files: файлы дерева (`git ls-files`); None — шаблоны на живость не сверять.
    """

    problems: list[str] = []
    declared: dict = config.get("heavy") or {}
    paths = {u.path for u in units}
    for path, entry in declared.items():
        if path not in paths:
            problems.append(
                f"тяжёлый модуль `{path}` не найден среди тест-модулей — пометка устарела"
            )
        if not (entry or {}).get("guards"):
            problems.append(f"тяжёлый модуль `{path}` не объявил сторожимых путей")
    for item in heavy_units(units, config):
        if item.unit.env not in HEAVY_ENVS:
            problems.append(
                f"тяжёлый модуль `{item.unit.path}` в среде {item.unit.env}: раннер CI "
                f"отбирает тяжёлые только в {', '.join(sorted(HEAVY_ENVS))}"
            )
        if len(item.guards) == 1:
            problems.append(
                f"тяжёлый модуль `{item.unit.path}` ({item.why}) не объявил сторожимых "
                f"путей в разделе `heavy` {CONFIG_REL}: днём он не пошёл бы ни на какую "
                "правку кода, который проверяет"
            )
        if tree_files is not None:
            for guard in item.guards[1:]:
                pattern = guard_pattern(guard)
                if not any(pattern.match(f) for f in tree_files):
                    problems.append(
                        f"сторожимый путь `{guard}` модуля `{item.unit.path}` не совпал "
                        "ни с одним файлом дерева — шаблон мёртв"
                    )
    return problems


#: Часы, чьё чтение означает замер настенного времени: `time.perf_counter()` и родня.
_CLOCKS = frozenset(
    {
        "perf_counter",
        "perf_counter_ns",
        "monotonic",
        "monotonic_ns",
        "time",
        "time_ns",
        "process_time",
        "process_time_ns",
    }
)

#: Сравнения «меньше/больше» — форма, в которой замер становится порогом.
_ORDER_ASSERTS = frozenset(
    {"assertLess", "assertLessEqual", "assertGreater", "assertGreaterEqual"}
)


def wallclock_threshold(source: str) -> tuple[int, int] | None:
    """Найти в тест-модуле порог по настенному времени.

    Признак — модуль и читает часы модуля `time` (`time.perf_counter()`,
    `time.monotonic()`, `time.time()` или те же имена, импортированные из `time`), и
    сравнивает что-то на «меньше/больше» (`assertLess` и родня или `assert a < b`).
    Признак грубый и намеренно строгий: модуль целиком, без прослеживания, что именно
    сравнивается. Подменённые часы (`mock.patch("time.sleep")`) — не чтение.

    Args:
        source: текст модуля.

    Returns:
        Пару строк (чтение часов, первое сравнение) или None, если порога нет.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    imported_clocks = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "time"
        for alias in node.names
        if alias.name in _CLOCKS
    }
    clock_line = order_line = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_clock = (
                isinstance(func, ast.Attribute)
                and func.attr in _CLOCKS
                and isinstance(func.value, ast.Name)
                and func.value.id == "time"
            ) or (isinstance(func, ast.Name) and func.id in imported_clocks)
            if is_clock and clock_line is None:
                clock_line = node.lineno
            if (
                isinstance(func, ast.Attribute)
                and func.attr in _ORDER_ASSERTS
                and order_line is None
            ):
                order_line = node.lineno
        elif (
            isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Compare)
            and any(
                isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE))
                for op in node.test.ops
            )
            and order_line is None
        ):
            order_line = node.lineno
    if clock_line is None or order_line is None:
        return None
    return clock_line, order_line


def check_wallclock(units: list[Unit], config: dict, root: Path = ROOT) -> list[str]:
    """Дневные модули `django-api` не держат порогов по настенному времени (T-1407).

    Порог по времени на общей машине CI — готовое ложное падение: CI #851 упал на
    0,34 с при пороге 0,2 с без единой правки кода. Такой замер живёт в тяжёлом
    модуле (раздел `heavy`) и идёт ночью; днём остаётся функциональная часть.

    Args:
        units: полная раскладка.
        config: конфигурация реестра.
        root: корень репозитория.

    Returns:
        Список нарушений — по одному на дневной модуль с порогом.
    """

    heavy = {h.unit.path for h in heavy_units(units, config)}
    problems: list[str] = []
    for unit in units:
        if unit.env not in HEAVY_ENVS or unit.path in heavy:
            continue
        try:
            source = (root / unit.path).read_text(encoding="utf-8")
        except OSError:
            continue
        found = wallclock_threshold(source)
        if found:
            problems.append(
                f"`{unit.path}` читает часы (строка {found[0]}) и сравнивает на "
                f"меньше/больше (строка {found[1]}): порог по настенному времени "
                "держится в тяжёлом модуле раздела `heavy`, а не в дневном "
                "(docs/engineering/testing.md §5.1)"
            )
    return problems


def tracked_files(root: Path = ROOT) -> list[str] | None:
    """Файлы дерева по `git ls-files`; None, если git недоступен."""

    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.splitlines()


def read_changed(path: str) -> list[str]:
    """Прочитать список изменённых путей: по одному на строку, пустые строки — мимо."""

    text = Path(path).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


# ------------------------------------------------------------------------- находка


@dataclass(frozen=True)
class Unit:
    """Один тест-модуль: как его зовут, где он лежит и в какую группу попал.

    Attributes:
        env: ключ среды.
        label: то, что понимает раннер этой среды.
        path: путь от корня репозитория — для сверки сирот и для отчётов о падении.
        key: нормализованная метка, по которой считалась группа.
        group: имя группы.
    """

    env: str
    label: str
    path: str
    key: str
    group: str


#: Питоновский тест-модуль: `test_x.py`, `tests_x.py`, `tests.py`. `__init__.py` и
#: `conftest.py` сюда не попадают — они не модули с тестами.
_PY_TEST = re.compile(r"^(?:tests?_.+|tests?)\.py$")

#: Тест фронта или e2e: `x.test.tsx`, `x.spec.ts`.
_TS_TEST = re.compile(r"\.(?:test|spec)\.(?:ts|tsx|js|jsx)$")

_SKIP_PARTS = frozenset({"__pycache__", "node_modules", ".venv", "migrations"})


def _is_test(name: str, runner: str) -> bool:
    if runner in ("jest", "playwright"):
        return bool(_TS_TEST.search(name))
    return bool(_PY_TEST.match(name))


def _is_management_command(path: Path) -> bool:
    """Команда Django `manage.py test_*` — не тест-модуль, хоть имя и похоже (T-1430)."""

    parts = path.parts
    return len(parts) >= 3 and parts[-3:-1] == ("management", "commands")


def discover(env: Environment, root: Path = ROOT) -> list[Unit]:
    """Найти все тест-модули одной среды.

    Args:
        env: описание среды.
        root: корень репозитория.

    Returns:
        Список находок, отсортированный по метке; группа ещё не проставлена.
    """

    base = root if env.root == "." else root / env.root
    found: list[Unit] = []
    for rel_root in env.test_roots:
        start = base / rel_root
        if not start.is_dir():
            continue
        for path in start.rglob("*"):
            if not path.is_file() or _SKIP_PARTS & set(path.parts):
                continue
            if not _is_test(path.name, env.runner):
                continue
            if _is_management_command(path):
                continue
            rel = path.relative_to(base)
            if env.label_style == "django":
                label = ".".join(rel.with_suffix("").parts)
            else:
                label = rel.as_posix()
            found.append(
                Unit(
                    env=env.key,
                    label=label,
                    path=path.relative_to(root).as_posix(),
                    key=normalize(rel.as_posix()),
                    group="",
                )
            )
    return sorted(found, key=lambda u: u.label)


def build(root: Path = ROOT, exceptions: dict[str, str] | None = None) -> list[Unit]:
    """Разложить все среды по группам.

    Returns:
        Все находки со проставленной группой, в порядке сред (дешёвое раньше дорогого).
    """

    units: list[Unit] = []
    for env in ENVIRONMENTS:
        for unit in discover(env, root):
            units.append(
                Unit(
                    env=unit.env,
                    label=unit.label,
                    path=unit.path,
                    key=unit.key,
                    group=classify(unit.key, exceptions),
                )
            )
    return units


def select(
    units: list[Unit],
    envs: list[str] | None = None,
    groups: list[str] | None = None,
    include_optional: bool = False,
) -> list[Unit]:
    """Отобрать подмножество прогона.

    Args:
        units: полная раскладка.
        envs: ограничить средами; None — все.
        groups: ограничить группами; None — все.
        include_optional: включать ли среды, не входящие в полный прогон по умолчанию
            (сейчас это только e2e).
    """

    chosen = units
    if envs:
        chosen = [u for u in chosen if u.env in envs]
    elif not include_optional:
        chosen = [u for u in chosen if ENV_BY_KEY[u.env].default]
    if groups:
        chosen = [u for u in chosen if u.group in groups]
    return chosen


@dataclass(frozen=True)
class DaySelection:
    """Что идёт в прогон после дневного отбора тяжёлых (T-1404, T-1406).

    Attributes:
        units: модули, которые идут.
        heavy: тяжёлые модули со стражами.
        skipped: пути тяжёлых модулей, пропущенных днём.
        pending: пути тестов миграций, которых ещё нет в main (днём идут всегда).
        main_note: чем определена ветка main — для журнала.
        pending_why: почему тесты миграций идут днём — для журнала.
    """

    units: list[Unit]
    heavy: list[Heavy]
    skipped: set[str]
    pending: frozenset[str]
    main_note: str
    pending_why: str


def day_selection(
    units: list[Unit], config: dict, changed: list[str] | None
) -> DaySelection:
    """Применить дневной отбор: тяжёлые без тронутых стражей — мимо.

    Args:
        units: полная раскладка.
        config: конфигурация реестра.
        changed: изменённые пути; None — ночной режим, идёт всё.

    Returns:
        Отобранные модули и пояснения к отбору.
    """

    # Днём тест миграции, которой ещё нет в main, идёт всегда (T-1406). Main не найдена —
    # состояние неизвестно, и тесты миграций идут все: лишний прогон дешевле пропуска.
    pending: frozenset[str] = frozenset()
    main_note = ""
    pending_why = "миграции ещё нет в main"
    if changed is not None:
        migration_tests = [u.path for u in units if migration_guard(u.path)]
        found_pending = pending_migration_tests(migration_tests)
        if found_pending is None:
            pending = frozenset(migration_tests)
            main_note = "ветка main не найдена или история неполная — тесты миграций днём идут все"
            pending_why = "состояние main неизвестно"
        else:
            pending = found_pending
            main_note = f"ветка main: {resolve_main_ref()}"
    heavy = heavy_units(units, config, pending)
    skipped = daytime_skipped(heavy, changed)
    return DaySelection(
        units=[u for u in units if u.path not in skipped],
        heavy=heavy,
        skipped=skipped,
        pending=pending,
        main_note=main_note,
        pending_why=pending_why,
    )


# ------------------------------------------------------------------ группы CI

#: Быстрые группы CI (ADR-117 D2): проверки без сборки образов, идут одним джобом
#: `checks` на каждом пуше. Команды каждой — в `scripts/ci_quick_checks.py`.
CI_QUICK_GROUPS: tuple[str, ...] = ("lint", "saga", "codes", "frontend")

#: Среды, тесты которых идут в джобе `test` одной группой на среду. django-api идёт
#: группами реестра (`django:<группа>`), фронт — быстрой группой `frontend`
#: (jest на хосте), `scripts` — внутри `saga`, e2e — не в CI.
CI_SERVICE_ENVS: tuple[str, ...] = ("ml-llm", "ml-bkt", "web-import")

#: Префикс тестовых групп django-api в именах CI.
CI_DJANGO_PREFIX = "django:"


def ci_groups(units: list[Unit]) -> list[str]:
    """Полный список групп CI: быстрые, затем тестовые.

    Args:
        units: модули, которые идут в прогон (после дневного отбора).

    Returns:
        Имена групп в едином пространстве имён ADR-117 D2. Группа django-api, в
        которой после отбора не осталось модулей, не перечисляется: `manage.py test`
        без меток гонял бы всё подряд.
    """

    django = [
        f"{CI_DJANGO_PREFIX}{name}"
        for name in GROUPS
        if any(u.env == "django-api" and u.group == name for u in units)
    ]
    services = [e for e in CI_SERVICE_ENVS if any(u.env == e for u in units)]
    return [*CI_QUICK_GROUPS, *django, *services]


# ---------------------------------------------------------------------- храповик


def load_config(root: Path = ROOT) -> dict:
    """Прочитать храповик и карту исключений.

    Отсутствие файла — не ошибка: реестр работает и без него, просто ничего не
    зафиксировано. Ошибка — файл, который не разбирается: молчаливо продолжать с
    пустым храповиком значило бы потерять гейт.
    """

    path = root / CONFIG_REL
    if not path.is_file():
        return {"core_ceiling": None, "exceptions": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✗ конфигурация не разбирается: {path} — {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def check(units: list[Unit], config: dict) -> list[str]:
    """Сверка раскладки. Возвращает список нарушений; пустой список — чисто."""

    problems: list[str] = []

    exceptions = config.get("exceptions") or {}
    known_keys = {u.key for u in units}
    for key, group in exceptions.items():
        if group not in GROUPS:
            problems.append(
                f"исключение `{key}` указывает на несуществующую группу `{group}`"
            )
        if key not in known_keys:
            problems.append(
                f"исключение `{key}` не совпало ни с одним тест-модулем — "
                "метка устарела и теперь ничего не значит"
            )

    ceiling = config.get("core_ceiling")
    core = [u for u in units if u.group == CATCH_ALL]
    if ceiling is not None and len(core) > int(ceiling):
        problems.append(
            f"свалка `core` выросла: {len(core)} против зафиксированных {ceiling}. "
            "Новый тест обязан попасть под правило или получить исключение в "
            f"{CONFIG_REL}; храповик может только убывать"
        )

    seen: dict[tuple[str, str], int] = {}
    for unit in units:
        seen[(unit.env, unit.label)] = seen.get((unit.env, unit.label), 0) + 1
    for (env, label), count in seen.items():
        if count > 1:
            problems.append(f"метка встречается дважды в среде {env}: {label}")

    return problems


# --------------------------------------------------------------------------- вывод


def _summary(units: list[Unit]) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = {}
    for unit in units:
        table.setdefault(unit.group, {})
        table[unit.group][unit.env] = table[unit.group].get(unit.env, 0) + 1
    return table


def _print_table(units: list[Unit]) -> None:
    table = _summary(units)
    env_keys = [e.key for e in ENVIRONMENTS]
    width = max(len(g) for g in GROUPS) + 1
    header = f"{'группа':<{width}} {'всего':>6}  " + "  ".join(
        f"{k:>10}" for k in env_keys
    )
    print(header)
    print("-" * len(header))
    for group in GROUPS:
        row = table.get(group, {})
        total = sum(row.values())
        cells = "  ".join(f"{row.get(k, 0):>10}" for k in env_keys)
        print(f"{group:<{width}} {total:>6}  {cells}")
    print("-" * len(header))
    totals = {k: sum(1 for u in units if u.env == k) for k in env_keys}
    cells = "  ".join(f"{totals[k]:>10}" for k in env_keys)
    print(f"{'всего':<{width}} {len(units):>6}  {cells}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="показать раскладку")
    parser.add_argument("--check", action="store_true", help="сверка раскладки")
    parser.add_argument("--envs", action="store_true", help="перечислить среды")
    parser.add_argument("--json", action="store_true", help="машинный вывод")
    parser.add_argument("--env", action="append", help="ограничить средой")
    parser.add_argument("--group", action="append", help="ограничить группой")
    parser.add_argument("--e2e", action="store_true", help="добавить e2e")
    parser.add_argument(
        "--labels",
        nargs=2,
        metavar=("СРЕДА", "ГРУППА"),
        help="выдать метки для раннера",
    )
    parser.add_argument(
        "--groups",
        metavar="СРЕДА",
        help="перечислить непустые группы среды (для цикла в CI)",
    )
    parser.add_argument(
        "--ci-groups",
        action="store_true",
        help="перечислить группы CI всех сред (ADR-117 D2): быстрые и тестовые",
    )
    parser.add_argument("--verbose", action="store_true", help="перечислить модули")
    parser.add_argument("--heavy", action="store_true", help="тяжёлые модули и стражи")
    parser.add_argument(
        "--day",
        metavar="ФАЙЛ",
        help="дневной отбор: файл изменённых путей; тяжёлые без тронутых стражей — мимо",
    )
    args = parser.parse_args()

    config = load_config()
    all_units = build(exceptions=config.get("exceptions") or {})
    fresh_extra = frozenset(config.get("fresh_db_only") or ())
    changed = read_changed(args.day) if args.day else None
    day = day_selection(all_units, config, changed)
    units, heavy, skipped = day.units, day.heavy, day.skipped
    pending, main_note, pending_why = day.pending, day.main_note, day.pending_why

    if args.ci_groups:
        print(" ".join(ci_groups(units)))
        return 0

    if args.heavy:
        if main_note:
            print(f"Тесты миграций (T-1406): {main_note}")
        for path in sorted(pending):
            unit = next(u for u in units if u.path == path)
            print(
                f"[{unit.env}] {unit.label}  (тест миграции) — днём идёт: {pending_why}"
            )
        for item in heavy:
            if changed is None:
                verdict = "идёт (все тяжёлые)"
            elif item.unit.path in skipped:
                verdict = "днём пропущен"
            else:
                hits = item.touched_by(changed)
                verdict = f"днём идёт: тронут {hits[0]}" + (
                    f" и ещё {len(hits) - 1}" if len(hits) > 1 else ""
                )
            print(f"[{item.unit.env}] {item.unit.label}  ({item.why}) — {verdict}")
            for guard in item.guards:
                print(f"    сторожит {guard}")
        return 0

    if args.envs:
        for env in ENVIRONMENTS:
            mark = "" if env.default else "  (по флагу)"
            place = "хост" if env.where == "host" else f"контейнер {env.service}"
            count = sum(1 for u in units if u.env == env.key)
            print(f"{env.key:<12} {count:>4} модулей  {place}, {env.runner}{mark}")
        return 0

    if args.groups:
        if args.groups not in ENV_BY_KEY:
            print(f"неизвестная среда: {args.groups}", file=sys.stderr)
            return 2
        present = [
            name
            for name in GROUPS
            if any(u.env == args.groups and u.group == name for u in units)
        ]
        print(" ".join(present))
        return 0

    if args.labels:
        env_key, group = args.labels
        if env_key not in ENV_BY_KEY:
            print(f"неизвестная среда: {env_key}", file=sys.stderr)
            return 2
        if group not in GROUPS:
            print(f"неизвестная группа: {group}", file=sys.stderr)
            return 2
        chosen = [u for u in units if u.env == env_key and u.group == group]
        print(" ".join(u.label for u in chosen))
        return 0

    chosen = select(units, args.env, args.group, include_optional=args.e2e)

    if args.json:
        print(
            json.dumps(
                {
                    "total": len(chosen),
                    "summary": _summary(chosen),
                    # Списком, а не числом: сводка расхождения меряет длину списков,
                    # а человеку нужно имя модуля, а не «их стало три».
                    "in_dump": [u.label for u in chosen if u.group == CATCH_ALL],
                    "fresh_db_only": [
                        u.label
                        for u in chosen
                        if requires_fresh_database(u.key, fresh_extra)
                    ],
                    "heavy": [
                        {
                            "label": h.unit.label,
                            "path": h.unit.path,
                            "why": h.why,
                            "guards": list(h.guards),
                        }
                        for h in heavy
                    ],
                    "daytime_skipped": sorted(skipped),
                    "units": [
                        {
                            "env": u.env,
                            "group": u.group,
                            "label": u.label,
                            "path": u.path,
                        }
                        for u in chosen
                    ],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.check:
        problems = (
            check(all_units, config)
            + check_heavy(all_units, config, tracked_files())
            + check_wallclock(all_units, config)
        )
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        if problems:
            return 1
        core = sum(1 for u in units if u.group == CATCH_ALL)
        print(
            f"OK: {len(units)} тест-модулей в {len(ENVIRONMENTS)} средах разложены "
            f"по {len(GROUPS)} группам; в свалке {core}"
        )
        return 0

    if args.list:
        _print_table(chosen)
        if args.verbose:
            for group in GROUPS:
                inside = [u for u in chosen if u.group == group]
                if not inside:
                    continue
                print(f"\n{group} ({len(inside)}) — {GROUP_TITLES[group]}")
                for unit in inside:
                    print(f"  [{unit.env}] {unit.label}")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
