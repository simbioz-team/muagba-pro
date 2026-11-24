# Фича 2 (шаг 8, теория ступени): разложение и план, команда B, круг 3

Дата 2026-11-24. Процесс — `design.md` (К и `[T]` параллельно → веер `[V]` → `[H]`). Вход:
`feature-2-description.md`, санированная спека, код и документы на базовом коммите `053602900`
(`git show`). Прошлая версия — `f2-B-r2.md`, замечания — `f2-eval-r2.md` §6 (п. 7–13).
Расчёт: `f2B3/plan3.py` (проба P = W/S, HLFET, событийная модель), прогоны `f2B3/runs3.py`,
`f2B3/extra3.py`. Группы CI: `f2B3/keys.txt` → `f2B3/keys_out.txt` через `classify` из
`evalchk/test_registry_base.py`.

Модель та же, что в круге 2: вес 10 мин × 1.6 (deep) × 1.5 (M); ревью 8 мин; доработка 0.7 веса,
второй круг с вероятностью p/2, предел два круга; разброс 0.7–1.4; 300 прогонов; одна очередь
вливаний у координатора, c = 6 мин, партия до 4 веток за c + 2·(n − 1). **Новое в круге 3:
стека нет нигде.** Каждое ребро снимается вливанием предка. `[T]` ни от чего не зависят и
вливаются в любой момент. `[V]` вливается после `[T]` своей истории.

Бейзлайна я не открывал. Числа бейзлайна (≈ 10–10.5 ч, в среднем 1.48 исполнителя, p = 0.61)
взяты из оценки `f2-eval-r2.md` §0.

## 0. Итог в цифрах

| Мера | Круг 2 | Круг 3 |
|---|---|---|
| Задач | 32 (3 К, 5 T, 23 V, 1 H), deep 10 | **32 (5 К, 5 T, 21 V, 1 H), deep 11** |
| W, S, P = W/S | 550, 78, 7.05 | **569, 78, 7.29** |
| Критический путь | K2 → K3 (стек) → V1 → H1 | **K2 → K4 → V4 (любой deep M) → H1**, без стека |
| Проба P ≥ 2K | норма при K ≤ 3 | норма при K ≤ 3; при K = 4–5 предупреждение (P ≥ K) |
| Фаза К | 11 % W, стек | **16 % W**, глубина 2 только у K4 (по вливанию, `Почему не одна:`) |
| Пересечения `Файлы:` без пути | 0 | 0 (`plan3.py`) |
| Деление «сервер ∥ клиент» при срезах ≥ 2K | 2 | **0** |
| Красные проверки pre-commit, найденные оценщиком | 3 (документы ручек, `TAGS.md`, коды) | **0**, проверено по коду проверок (§2.5) |
| Тест-модули в `core` | 0 | 0 (41 модуль через `classify`) |

**Время веера и срок до приёмки** (срок = веер + последняя проверка CI 15–28 мин + приёмка
последней истории 20–40 мин):

| Сценарий | p = 0.61 (бейзлайн этой фичи) | p = 0.43 (наставник сегодня) | p = 0.15 (цель) |
|---|---|---|---|
| **N = 2, R = 1 (пул общий с шагом 6)** | 565 (p90 615) → **10.0–10.6 ч** | 492 (p90 538) → **8.8–9.3 ч** | 397 → 7.2–7.7 ч |
| N = 2, R = 2 | 523 (p90 570) → 9.3–9.9 ч | 461 (p90 502) → 8.3–8.8 ч | 380 → 6.9–7.5 ч |
| N = 3, R = 2, партии | 385 → 7.0–7.5 ч | 341 → 6.3–6.8 ч | 278 → 5.2–5.8 ч |
| **N = 4, R = 3, партии (пул свой)** | 318 (p90 347) → **5.9–6.4 ч** | 281 (p90 313) → **5.3–5.8 ч** | 230 → 4.4–5.0 ч |
| N = 5, R = 4, партии | 283 (−11 % к N = 4) | 254 (−10 %) | 210 (−9 %) |

**Против бейзлайна ≈ 10–10.5 ч:**
- **Пул свой, N = 4:** при том же p = 0.61 выходит −36…−44 %, при p = 0.43 −42…−50 %.
  Одновременно работают **2.93–2.95 из 4** против 1.48, то есть в 2.0 раза больше.
- **Пул общий, N = 2, R = 1, p = 0.61: выигрыша нет** (−5…+6 %). Ширина плана (P = 7.3) в этом
  режиме не используется: в каждый момент готовы 5–12 задач на 2 слота, занятость 1.64 из 2.
  Выигрыш здесь дают не раскладка, а снижение p (0.61 → 0.43 даёт −13 %) и второй ревьюер
  (R = 2 — ещё −7 %). Оценщик прогнозировал на круг 2 9.2–10.4 ч при p = 0.61. Мой расчёт
  10.0–10.6 ч попадает в его верхнюю половину.
- **Пятый слот** даёт −9…−11 %, и только с партиями. Совет — K = 4: снижение p с 0.43 до 0.15
  даёт −18 %, это вдвое больше пятого слота.

**Цена** (медианы: deep $4.9, обычный $0.94, ревью $1.5, доработка ≈ 0.7 среднего запуска =
$1.61). Первый круг: 11 × 4.9 + 21 × 0.94 = $73.6.

| p | Запусков исполнителя / ревью | Цена |
|---|---|---|
| 0.61 | 57.8 / 57.8 | 73.6 + 25.8 × 1.61 + 57.8 × 1.5 ≈ **$202** |
| 0.43 | 48.8 / 48.8 | ≈ **$174** |
| 0.15 | 37.3 / 37.3 | ≈ **$138** |

Бейзлайн, по оценщику, стоил ≈ $130. План дороже на 34–55 % по деньгам, потому что в нём больше
задач и ревью. Взамен он вдвое быстрее, если пул свой.

## 1. Ответы на замечания круга 2

| # (eval §6) | Замечание | Что сделано |
|---|---|---|
| 7 | K2 заводит 7 маршрутов без описаний, `check_api_doc_coverage` красный на K2; R-19 не описывает никто; `TAGS.md` правят 4 среза | **K2 создаёт 7 заготовок описаний** с frontmatter (`title: "METHOD /path"`, `status: draft`) и заготовку раннбука. Строки `TAGS.md` для всех восьми K2 вносит через `check_docs_index.py --fill`. В `Готово-когда:` K2 стоят `check_api_doc_coverage.py` и `check_docs_index.py`. Тела документов заполняют срезы: R-25 — V2, четыре R-30 — V9, импорт — V9b, **R-19 — V14**, раннбук — V20. Срезы frontmatter не трогают, поэтому строка `TAGS.md` не расходится (проверка 3 сверяет `status`, `updated`, `title`; см. §2.5). Финальные `status: active` и `updated` выставляет H1 вместе с `--fill`. Вдобавок `TAGS.md` объявлен классом `regen` в `pair-rules.txt`: строки берутся из frontmatter дословно, поэтому при конфликте берётся главная ветка и запускается `--fill`, один раз на партию |
| 8 | Коды K2 `active` без употребления | Коды уехали в отдельную **K3** вместе с первым употреблением. `/problems/course-path-not-applicable` и варианты употребляет настоящее тело `pipeline_path.refuse_unless_path` (`Problem.COURSE_PATH_NOT_APPLICABLE`; шаблон употребления `\bProblem\.([A-Z0-9_]+)` вне `tests/` и `problem_types.py`). Четыре кода гейта — это не `codes`, а `gate_blockers`. Их сторож — `test_gate_blockers_closed_list` («код не привязан ни к одному гейту»), а не `check-codes`. Поэтому K3 заводит **четыре правила-заглушки** в `gates/rules_rung_theory.py` (элементы `GateBlocker`, условие без находок) и привязывает их в `gates/registry.py` через `bind_on_path(..., pipeline_v2=True)`. V19a пишет только тела правил и `registry.py` не трогает. Это ещё и снимает пересечение V19a с шагом 6 по `registry.py` |
| 9 | Сервер ∥ клиент при 23 срезах ≥ 2K; `[T]` только серверные | **Деления по сторонам больше нет.** V2 = R-25 + вкладка; V9 = четыре ручки R-30 + кнопка «Добавить теорию» и обёртки; V9b = импорт + обёртка; V10 = правила разделов + выбор знаний раздела в редакторе; V11 = форк и пересборка + текст `force`. V3 и V22 упразднены. Общий JSON-образец (второй вариант оценщика) **в этом проекте не работает без правки инфраструктуры**: контейнер `django-api` монтирует только `./services/django-api:/app` (`docker-compose.yml:212`), а jest идёт в контейнере `frontend`. Файл, который читают оба теста, ни в одном прогоне не виден обоим. Остаточный риск расхождения сторон — в типах клиента K5 против сериализации K2. Обе К пишутся по одной строке `contracts.md` (C13/C17), и обе стороны каждой ручки после этого заполняет один исполнитель в одном срезе |
| 10 | `ac_pending` в К; K3 стеком от K2; `[T]` стеком от K2 | **Помощника нет.** `[T]` помечают методы `test_ac<N>_*` штатным `@unittest.expectedFailure` (раннер — `manage.py test`), на фронте — `test.failing`. Отличать «упал на импорте» от «упал на проверке» больше не нужно. Тест, который ничего не держит, ловится в другом месте: срез обязан снять отметки **всех** методов своих AC, и тогда они обязаны быть зелёными на коде среза и красными на `hold`. Отметка, не снятая до конца фичи, — красное в `Готово-когда:` H1 («в модулях `[T]` фичи ноль `expectedFailure`»). Поэтому `[T]` ни от чего не зависят, стартуют в минуту 0 и вливаются когда угодно. **K4 (бывшая K3) стартует от влитой K2.** Предложение «стек К → К» я снимаю расчётом: при широкой фазе К стек даёт 280 мин против 281 при N = 4 и 493 против 492 при N = 2 (§8 п. 1) |
| 11 | p = 0.61 не посчитан | Посчитан во всех сценариях (§0) |
| 12 | Место `[T]` по `check_test_location` | Сторож смотрит только тест-модули **уровня приложения** (`courses/tests/**`, функция `app_level_tests`). Модули внутри подпакета он не проверяет вовсе. Поэтому **каждая `[T]` лежит в `tests/` своего главного подпакета** (§4, фаза `[T]`), а в `courses/tests/acceptance/` нет ни одной. Ни одна `[T]` не попадает под правило «один подпакет — лежи в нём», и `test-location.json` никто не правит. Проверено и обратное: `check_module_boundaries` тесты не считает (строки 146–148) |
| 13 | CI как общий ресурс двух фич | §7 п. 4: вливание не ждёт CI. Пуш идёт не чаще одного раза за прогон и общий для обеих фич. Посчитано число пушей |
| 4.4 | IE-9/IE-10 в `models.py` | Оценщик подтвердил, что у B это верно: V12a правит `models.py` после K1 |

## 2. Как получена ширина

### 2.1. Решения планирования (из кругов 1–2, в силе)

1. **Окна в фазе К вместо общих гигантов.** `topic_content/services.py` (2 703 строки), `views.py`
   (1 503), `generation/services.py` (1 221) получают от K4 по одной строке вызова на место, тело
   уходит в новый файл одного среза. На фронте то же делает K5 с `ContentEditorDrawer.tsx`
   (1 572 строки) и `ContentTab.tsx`: ветка по флагу и источник данных по id материала.
2. **Инвариант в модели** (K1): `clean()`/`save()` отказывает носителю ступени флагового курса с
   `topic ≠ NULL`, а `course` ставит сама.
3. **Подмена состава** `rung_theory/testing.py::patch_course_theory` (K2): потребители состава не
   ждут V1.
4. **Тонкая ручка, тело в сервисе** (новое). K2 пишет пять ручек R-30 целиком по контракту
   (разбор тела, вызов сервиса, сериализация ответа), а сервисы `rung_material.py` и
   `passthrough_rung.py` — заглушками. Срезы V9 и V9b пишут сервисы и `rung_views.py` не
   трогают. Файл ручек меняет ещё только V7, и только декоратором пути.

### 2.2. Направление импортов (круг 2, проверено по `check_module_boundaries.py`)

`rung_theory` — ярус 3: над `topic_content` и `task_classes`, под `course_pipeline`, `lesson`,
`dialogue`. Циклы П-8 круга 1 разобраны окном `topic_content/rung_listeners.py` по образцу
`phase_listeners.py`. Откат лежит в `course_pipeline/rung_reopen.py`, `sections_for_knowledge` —
в `topic_content/rung_sections.py`. Направление `course_pipeline → rung_theory` единственное.

### 2.3. Почему К пять, а не три

Правило `design.md` §3.2 п. 3 — «К 1–3». Я его нарушаю и называю почему. Три проверки проекта
требуют, чтобы ключ и его первое употребление появились в одном коммите:
- `check_api_doc_coverage` — маршрут и описание;
- `check-codes` и `test_gate_blockers_closed_list` — код и употребление или привязка;
- `check_docs_index` — документ и строка индекса.

Поэтому каждая К тянет за собой и употребления. В трёх К это даёт K2 ≈ 650 строк кода. Это
больше M, то есть по правилу §4 её надо резать. Разрез идёт по подсистемам, по 1–2 в каждой:

| К | Подсистема | Строк кода (оценка) | Риск |
|---|---|---|---|
| K1 | схема `topic_content`, писатель, фикстуры | ~330 | deep |
| K2 | пакет `rung_theory`, маршруты, ручки, документы-заготовки | ~350 + 8 заготовок | обычный |
| K3 | реестры кодов, правила-заглушки гейта, отказ по пути, выведение R-24 | ~220 + JSON | обычный |
| K4 | окно и вызовы в горячих файлах сервера | ~300 | deep |
| K5 | клиент по контракту и окна фронта | ~220 | обычный |

Глубина 1 у всех, кроме K4 → K2 (по вливанию, `Почему не одна:`). Вес фазы К — 16 % W при
пределе 20 %. На ширину это работает: в минуту 0 готовы девять задач (K1, K2, K3, K5 и пять
`[T]`) на 4 слота, провал занятости в фазе К исчез (§5).

### 2.4. Тест-группы без исключений

Как в круге 2: группа вычисляется `classify` по имени модуля, `test-registry.json` не правится,
в `core` ноль модулей. Новые имена прогнаны (`f2B3/keys_out.txt`). Одно имя пришлось сменить:
`test_access_pipeline_path` уходит в `structure` (слово `pipeline` стоит раньше `access`),
поэтому тест K3 называется `test_access_path_refusal_codes` → `platform`.

### 2.5. Скрытые красные проверки: что проверено по коду

| Проверка (на `053602900`) | Что требует | Где закрыто |
|---|---|---|
| `scripts/check_api_doc_coverage.py` | у маршрута есть документ с `title: "METHOD /path"` (сверка по пути, метод и имя параметра стираются) | K2: 7 заготовок; 5 путей R-30 различны |
| `scripts/check_docs_index.py` | документ с frontmatter ↔ строка `TAGS.md`; `status`/`updated`/`title` совпадают | K2 `--fill`; срезы frontmatter не трогают; H1 `--fill` в конце |
| `.claude/check-codes.py` | новая запись `active` и с употреблением, `unreviewed` запрещён | K3: употребление в `pipeline_path.py` |
| `test_api_error_registry.test_gate_blockers_closed_list` | каждый `GateBlocker` привязан к гейту; код в правилах — только элементом | K3: правила-заглушки и привязка |
| `test_api_error_registry.test_every_rule_and_gate_is_in_registry` | правило `rules_*` без привязки — мёртвое | K3 привязывает все четыре; V19b удаляет правило вместе с привязкой |
| `scripts/check_problem_catalog.py` | у `active` кода и у каждого варианта `detail_variants` есть текст в `locale/ru/problems.json`; у кода причины — `gate-blocked.<код>` | K3 |
| `check_problem_responses.py` + `response-codes.nastavnik.json` | класс отказа разрешён владельцу (`courses.access_registry`: 422 есть) | K3: владелец кода — `courses.access_registry` |
| `scripts/check_test_location.py` | только тесты уровня приложения | `[T]` в подпакетах (§1 п. 12) |
| `test_enum_is_fresh` | `problem_types.py` сгенерирован из реестра | K3 перегенерирует; класс `regen` при конфликте с шагом 6 |

**R-24** (выведение `reading-material-outdated`). У `gate_blockers` нет поля `state`:
генератор (`gen_problem_types.py:104`) поддерживает выведение только у `action_hints`. Поэтому
K3 добавляет `state: deprecated`, `replaced_by`, `deprecated_since`, `remove_after` в разбор
`gate_blockers`. Выведенный элемент остаётся в `GateBlocker`. Сторож закрытого списка не
требует привязки у выведенного кода. Сам код при этом остаётся привязанным, пока V19b не снимет
флаговое правило. Между вливаниями K3 и V19b проверки зелёные: выведенный код употреблять
разрешено до `remove_after`.

## 3. Карта швов (`contracts.md`)

| C | Шов | Владелец | Потребители |
|---|---|---|---|
| C1 | `TopicContent.carrier_purpose` (`theory` \| NULL) и инварианты R-2 | K1 | V4 V5 V9 V9b V10 V11 V12a V12b V13 V14 V17b V19a V19b V19c V20, все `[T]` |
| C2 | `TopicContent.topic`, `TopicContentGenerationError.topic` → `null=True`; на флаге носитель ступени с `topic ≠ NULL` — отказ `clean()`, без флага `topic = NULL` — отказ (AC-14) | K1 | все писатели |
| C3 | `TopicContent.course` (FK PROTECT, `null=True`, `related_name="course_materials"`), ставится в `save()`; миграция заполняет все строки | K1 | V7 V11 V12a V12b V13 V20 |
| C4 | `section_type='approach_map'` (только `choices`); `TopicContentSection.understanding_step` 1…5 \| NULL | K1 | V4 V5 V10 V11 V13 V14 V19a |
| C5 | `RungTheoryMigrationRecord` в `topic_content/models.py`, `record(...)` | K1 | V20 |
| C6 | Миграции `0307_rung_theory_schema`, `0308_rung_theory_migration_record` (номер — при вливании); тест обратной миграции с строками после переноса | K1 | V20 |
| C7 | Фикстуры `topic_content/tests/rung_fixtures.py::flag_course_with_ladder`, `legacy_course_with_reading` | K1 | все backend `[V]` и `[T]` |
| C8 | Писатель `topic_content/rung_writer.py`; строки `WRITER_FILES` для `rung_writer.py`, `generation/rung_theory_units.py`, `generation/rung_theory_merge.py`, `rung_material.py`, `rung_theory_migration.py` | K1 → шаг 4 Lexical дописывает V4 | V5 V9 V9b V20 |
| C9 | Пакет `rung_theory` (ярус 3), `AGENTS.md`, `README.md` с полной публичной поверхностью | K2 | все |
| C10 | `rung_theory/types.py` (`TheoryState`, `RungTheory`, `CourseTheory`, `TheoryBlock`), `rung_theory/testing.py::patch_course_theory` | K2 | все |
| C11 | `rung_theory/needs.py`: `course_theory`, `rung_composition`, `serving_version`, `primary_carrier` — сигнатуры, тело `NotImplementedError` | K2 → тело V1 | V2 V14 V19a V19c, окно C14 |
| C12 | Коды: `/problems/course-path-not-applicable` (422, владелец `courses.access_registry`), варианты `rung-material`, `topic-material`; `gate_blockers`: `rung-theory-knowledge-missing`, `rung-theory-section-unmarked`, `rung-theory-outdated`, `rung-approach-map-missing`; тексты каталога; строки `api-problems.json`; R-24 — выведение `reading-material-outdated`; `access_registry/pipeline_path.py::refuse_unless_path(course, *, v2: bool, variant)` (настоящее тело); `gates/rules_rung_theory.py` — четыре правила-заглушки, привязанные в `gates/registry.py` | **K3** | V7 V19a V19b |
| C13 | Маршруты: R-30 ×5 → `topic_content/rung_views.py` (полные ручки поверх сервисов-заглушек `topic_content/rung_material.py`: `add_theory`, `list_versions`, `switch_current`, `update_carrier`; `topic_content/passthrough_rung.py::populate_rung_carrier`); R-25 → `rung_theory/api.py`; R-19 `GET /api/v1/courses/{c}/task-classes/{tc}/theory/read` → `lesson/mode_a/theory_read.py`; строки реестра доступа; **7 заготовок `docs/api/endpoints/*.md` и заготовка раннбука, строки `TAGS.md`** | K2 | V2 V7 V9 V9b V14 V20 |
| C14 | Окно `topic_content/rung_listeners.py`: `validate_section`, `on_serving_change`, `compose_rung_theory`; регистрация в `CoursesConfig.ready()`; вызовы в `create/update_topic_content_section`, после утверждения, переключения, отклонения и удаления версии; `course_pipeline/rung_reopen.py` (заглушка) | K4 | V4 V5 V10 V11 V19c |
| C15 | `regenerate-content`: `theory_mode` (`generate`/`complete`/`map`) в `RegenerateCourseContentView` (`views.py:1229`, разбор JSON внутри `View`); на старом пути 422 `not-applicable`; переход в `generation/services.py` на заглушки `rung_theory_units.plan_generate`, `rung_theory_merge.plan_complete/plan_map` | K4 | V2 V4 V5 |
| C16 | Контракт ml-llm `kind=rung_theory` — **только `contracts.md`**; JSON-схему заводит V6, тип на стороне django — V4, сверку держит TB | `contracts.md` | V4 V6 |
| C17 | Фронт: `utils/rungTheory.ts` (R-25, `theory_mode`), `utils/rungMaterial.ts` (R-30 ×4), `utils/rungPopulate.ts` (импорт) — типы по `contracts.md`, тела `throw notImplemented('<срез>')`; ветка по флагу в `ContentTab.tsx` → `content/rung/RungContentTab.tsx` (заглушка); `content/rung/AddRungTheoryButton.tsx` (заглушка); источник данных в `ContentEditorDrawer.tsx` при `topicId == null`; `content/rung/knowledge.ts::rungKnowledgeCandidates` (заглушка `[]`) | **K5** | V2 V9 V9b V10 V11 |
| C18 | Отметка `[T]`: каждый метод `test_ac<N>_*` помечен `@unittest.expectedFailure` (jest — `test.failing`); импорт кода К и срезов — внутри тела теста. **Только текст в `contracts.md`, кода нет** | `contracts.md` | все `[T]`, все `[V]` |

## 4. Задачи

Общее для всех `[V]`: сдача — `check.sh` зелёный; сняты **все** отметки методов `test_ac<N>_*`
своих AC, и эти методы зелёные; вывод `hold` (откат не-тестовых `Файлы:` к базе краснит тесты
`Готово-когда:` и снятые AC). Вес: S = 10, M = 15, deep ×1.6. `Тест-группа:` — по `classify`.
`Зависит от:` снимается вливанием предка; стека нет.

### Фаза К (все, кроме K4, — с минуты 0)

- [ ] K1 [K] Схема материала ступени, инварианты, журнал, писатель, фикстуры
  Контракт: C1–C8
  Файлы: courses/topic_content/models.py (поля, `clean/save`, `__str__` без темы, модель журнала; IE-9/IE-10 не трогать — V12a), courses/migrations/0307_*.py, courses/migrations/0308_*.py, courses/topic_content/rung_writer.py, scripts/check_topic_content_writes.py (только `WRITER_FILES`), courses/topic_content/AGENTS.md (строка о писателе), courses/topic_content/tests/rung_fixtures.py, courses/topic_content/tests/test_content_rung_carrier_invariants.py, courses/topic_content/tests/test_migration_0307_rung_theory_schema.py
  Зависит от: —
  Приёмка: **AC-14 целиком — тесты K1** (§8 п. 2); AC-13 (столбцы старого пути, `course = topic.course`)
  Готово-когда: test_carrier_purpose_invariants, test_course_filled_by_save_with_and_without_topic, test_topic_null_refused_off_flag, test_topic_set_refused_on_flag_rung_carrier, test_writer_writes_blocks_with_step_and_knowledge, test_migration_fills_course, test_reverse_migration_restores_topic, test_reverse_migration_after_transfer_rows зелёные; `check_topic_content_writes.py` зелёный
  Риск: deep · Размер: M (24) · Тест-группа: content
  Внешний конфликт: цепочка миграций шага 6 (`serial: migrations`), номер ставится при вливании

- [ ] K2 [K] Пакет `rung_theory`, ярус, маршруты, ручки поверх заглушек, заготовки документов
  Контракт: C9–C11, C13
  Файлы: courses/rung_theory/{__init__,types,testing,needs,section_rules,api}.py, courses/rung_theory/AGENTS.md, courses/rung_theory/README.md, docs/engineering/module-tiers.json, courses/urls.py, courses/topic_content/urls.py, courses/topic_content/rung_views.py, courses/topic_content/rung_material.py (заглушки), courses/topic_content/passthrough_rung.py (заглушка), courses/lesson/mode_a/theory_read.py (заглушка), реестр доступа (строки семи ручек), docs/api/endpoints/{get-course-rung-theory,post-course-task-class-theory,get-course-topic-content-versions,post-course-topic-content-switch-current,patch-course-topic-content-carrier,post-course-topic-content-populate-from-documents,get-course-task-class-theory-read}.md (заготовки: frontmatter, заголовок `METHOD /path`, разделы «Запрос/Ответ/Ошибки/Доступ» с пометкой «заполняет <срез>»), docs/meta/process/rung-theory-migration-runbook.md (заготовка), docs/TAGS.md (только `--fill`), courses/rung_theory/tests/test_content_rung_contracts.py
  Зависит от: —
  Приёмка: —
  Готово-когда: test_routes_resolve_to_views, test_rung_views_parse_and_serialize_per_contract, test_service_stub_gives_501, test_theory_read_route_registered зелёные; `check_module_boundaries.py`, `gen_module_map.py --check`, `check_module_readme.py`, `check_module_coverage.py`, **`check_api_doc_coverage.py`, `check_docs_index.py`** зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
  Внешний конфликт: шаг 6 правит `module-tiers.json`, реестр доступа, `TAGS.md` (`regen`) — дописывание в свои разделы; пробное слияние со всеми ветками шага 6 в полёте

- [ ] K3 [K] Коды, правила-заглушки гейта, отказ по пути, выведение R-24
  Контракт: C12
  Файлы: services/django-api/config/response-codes.json, config/api-problems.json, config/locale/ru/problems.json, config/gen_problem_types.py (`state` у `gate_blockers`), config/problem_types.py (сгенерирован), courses/tests/test_api_error_registry.py (выведенный код привязки не требует), courses/access_registry/pipeline_path.py, courses/course_pipeline/gates/rules_rung_theory.py (четыре правила без находок), courses/course_pipeline/gates/registry.py (четыре привязки `bind_on_path(..., pipeline_v2=True)`), courses/access_registry/tests/test_access_path_refusal_codes.py, courses/course_pipeline/tests/test_gate_rung_theory_stub_rules.py
  Зависит от: —
  Приёмка: AC-9 (часть «`check-codes.py` зелёный»), AC-15 (часть «коды в реестре»)
  Готово-когда: test_refuse_unless_path_variants (422, `type`, `variant`, текст из каталога), test_stub_rules_bound_and_silent, test_deprecated_gate_blocker_kept_in_enum зелёные; `check-codes.py`, `check_problem_catalog.py`, `check_problem_responses.py`, `test_api_error_registry` целиком зелёные; у `reading-material-outdated` `state: deprecated`, `replaced_by: ["rung-theory-outdated"]`, `remove_after` = вливание + 3 мес.
  Риск: обычный · Размер: M (15) · Тест-группа: platform, saga
  Внешний конфликт: шаг 6 правит `response-codes.json`, `api-problems.json`, `registry.py`. Записи — только дописыванием в конец своих разделов, `problem_types.py` — класс `regen`

- [ ] K4 [K] Окно и вызовы в горячих файлах сервера
  Контракт: C14, C15
  Файлы: courses/topic_content/rung_listeners.py, courses/topic_content/services.py (только вызовы окна), courses/topic_content/views.py (только `theory_mode` в `RegenerateCourseContentView`), courses/topic_content/generation/services.py (только переход), courses/topic_content/generation/rung_theory_units.py (заглушка), courses/topic_content/generation/rung_theory_merge.py (заглушка), courses/course_pipeline/rung_reopen.py (заглушка), courses/apps.py (регистрация в `ready()`), courses/tests/test_handler_registration.py, courses/topic_content/tests/test_content_rung_hooks.py
  Зависит от: K2
  Почему не одна: K4 регистрирует обработчики пакета K2 (`section_rules`, `needs`) и без пакета не соберётся. Вместе K2 и K4 — около 650 строк при одном риске на всё; разрез отделяет механику (обычный) от горячих файлов (deep). Ребро снимается вливанием K2, стек не нужен: расчёт в §8 п. 1
  Приёмка: AC-15 (часть `theory_mode` → 422 `not-applicable`) — тестом K4
  Готово-когда: test_theory_mode_refused_off_flag, test_listeners_registered_web_and_celery, test_hooks_noop_on_legacy, test_unregistered_listener_fails_loud зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content, platform

- [ ] K5 [K] Клиент по контракту и окна фронта
  Контракт: C17
  Файлы: services/frontend/utils/rungTheory.ts, services/frontend/utils/rungMaterial.ts, services/frontend/utils/rungPopulate.ts, …/tabs/ContentTab.tsx (ветка по флагу), …/content/rung/RungContentTab.tsx (заглушка), …/content/rung/AddRungTheoryButton.tsx (заглушка), …/content/ContentEditorDrawer.tsx (источник данных при `topicId == null`: версии, переключение, импорт, создание, носитель; кандидаты знаний из `knowledge.ts`), …/content/rung/knowledge.ts (заглушка), __tests__/components/contentEditorRungSource.test.tsx
  Зависит от: — (по `contracts.md`)
  Приёмка: —
  Готово-когда: contentEditorRungSource.test (без флага редактор зовёт прежние функции `utils/auth.ts` с прежними аргументами; на флаге — обёртки `rungMaterial`/`rungPopulate` по id материала) зелёный; `tsc`, `/frontend-style` пройдены; `utils/auth.ts` не тронут
  Риск: обычный · Размер: M (15) · Тест-группа: content

### Фаза `[T]` (с минуты 0, зависимостей нет, вливание — когда угодно)

Каждая `[T]` пишет тесты по спеке и `contracts.md`. Каждый метод `test_ac<N>_*` помечен
`@unittest.expectedFailure` (C18), импорт кода — внутри тела. Модуль лежит в `tests/` своего
главного подпакета, поэтому `check_test_location` его не проверяет (§1 п. 12). До вливания К
тесты падают на импорте и считаются ожидаемой неудачей, так что `[T]` зелёная на любой вершине.
Неожиданный успех `unittest` засчитывает провалом. Первым тестом TAC идёт зонд: метод с
`expectedFailure`, который проходит, обязан покраснить прогон `manage.py test` проекта.

`[T]` не дублирует AC, которые целиком закрывает К (AC-14 — K1, `theory_mode` из AC-15 — K4,
реестровые части AC-9 и AC-15 — K3): иначе вливание К зависело бы от вливания `[T]` (§8 п. 2).

| T | Модуль | AC | Размер | Группа |
|---|---|---|---|---|
| TAC | courses/rung_theory/tests/test_content_ac_composition.py | AC-1 (пример Пр §2), AC-2 (через R-25), AC-16, AC-18 (серверная цепочка) | M (15) | content |
| TB | courses/topic_content/generation/tests/test_content_ac_rung_generation.py | AC-3, AC-6 (побайтность, правка двумя потоками), AC-8 (ноль вызовов без нажатия, резерв ≥ факт, отказ учёта), AC-19; сверка схемы C16 | M (15) | content |
| TC1 | courses/access_registry/tests/test_access_ac_rung_material.py | AC-4, AC-13, AC-15 (12 ручек), AC-17 (пять ролей на каждой ручке) | M (15) | platform |
| TDE | courses/rung_theory/tests/test_content_ac_transfer.py; courses/course_pipeline/tests/test_gate_ac_rung_theory.py | AC-5, AC-13 (дозаполнение); AC-9 (правила), AC-20, AC-21 | M (15) | content, saga |
| TFG | courses/task_classes/tests/test_task_class_ac_rung_structure.py; courses/lesson/mode_a/tests/test_lesson_ac_rung.py | AC-10, AC-11 (ручки); AC-12 | M (15) | banks, lessons |

AC-7 (вживую на `cp-*`) и Playwright из AC-11, AC-18, AC-22 делает `acceptance` по истории.

### Веер `[V]`

История A — состав и «Контент»
- [ ] V1 [V] Состав теории ступени и пакетный загрузчик
  Срез: R-5–R-7, R-9–R-12a · Контракт: C10, C11
  Файлы: courses/rung_theory/needs.py, courses/rung_theory/loader.py, courses/rung_theory/tests/test_content_needs.py, courses/rung_theory/tests/test_content_needs_loader.py
  Зависит от: K1, K2 · Приёмка: AC-1, AC-2 — TAC
  Готово-когда: test_progression_example_pr2, test_entry_point_skill_excluded, test_role_override_changes_need, test_each_knowledge_in_one_rung, test_states_order, test_lag_only_in_ready, test_loader_constant_queries зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content
- [ ] V2 [V] «Контент» по ступеням насквозь: ручка R-25 и вкладка
  Срез: R-25, R-26, R-12 · Контракт: C10, C11, C13, C15, C17
  Файлы: courses/rung_theory/api.py, courses/rung_theory/tests/test_content_rung_theory_api.py, docs/api/endpoints/get-course-rung-theory.md (тело), services/frontend/utils/rungTheory.ts (тела), …/content/rung/RungContentTab.tsx, …/content/rung/RungTheoryBlock.tsx, __tests__/components/rungContentTab.test.tsx
  Зависит от: K1, K2, K5 · Приёмка: AC-2, AC-17 (R-25), AC-22 (юнит; Playwright — acceptance) — TAC, TC1
  Готово-когда: test_rung_theory_payload_shape (ключи и типы — как в C17 `contracts.md`), test_rung_theory_access_5_roles, test_rung_theory_no_llm_calls; rungContentTab.test (шесть состояний с кнопками на ответе той же формы; «Сгенерировать/Дописать/карта» шлют `theory_mode`; после генерации перечитывает; «Редактировать» открывает `ContentEditorDrawer` прежними пропсами) зелёные; `tsc`, `/frontend-style`
  Риск: deep · Размер: M (24) · Тест-группа: content

История B — генерация и деньги
- [ ] V4 [V] `generate`: основной носитель, снимок, пять шагов, план расхода
  Срез: R-13 `generate`, R-8, R-14, шаг 4 R-15 на стороне django · Контракт: C8, C14, C15, C16
  Файлы: courses/topic_content/generation/rung_theory_units.py, courses/topic_content/generation/rung_theory_payload.py, courses/topic_content/generation/units.py, courses/topic_content/generation/tests/test_rung_theory_generate.py
  Зависит от: K1, K2, K4 · Приёмка: AC-3, AC-8 — TB
  Готово-когда: test_generate_creates_primary_carrier_with_snapshot, test_empty_composition_map_only, test_step4_question_rule_two_lexical_nodes, test_reserve_ge_actual, test_billing_refusal_leaves_carrier зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content
- [ ] V5 [V] `complete` и `map`: слияние под замком, подстраховка автопути
  Срез: R-13 `complete`/`map`/«нечего делать», R-14 · Контракт: C8, C14, C15
  Файлы: courses/topic_content/generation/rung_theory_merge.py, courses/course_pipeline/auto_pipeline.py, courses/topic_content/generation/tests/test_rung_theory_merge.py, courses/course_pipeline/tests/test_auto_pipeline_rung_theory.py
  Зависит от: K1, K2, K4 · Приёмка: AC-6, AC-19, AC-8 — TB
  Готово-когда: test_complete_copies_serving_sections_bytewise, test_complete_merges_author_edit_during_generation, test_map_adds_only_map, test_nothing_to_do_200_without_rung, test_backstop_generate_and_map_never_complete зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content, saga
  Внешний конфликт: `auto_pipeline.py` — шаг 6
- [ ] V6 [V] Промпт и схема теории ступени в ml-llm
  Срез: R-15 · Контракт: C16
  Файлы: services/ml-llm/…/prompts/plan_system_rung_theory.md, …/text_system_rung_theory.md, services/ml-llm/…/rung_theory.py, services/ml-llm/…/schemas/rung_theory.json, services/ml-llm/tests/test_rung_theory_prompt.py
  Зависит от: — (по `contracts.md`) · Приёмка: AC-7 — acceptance вживую; сверка схемы — TB
  Готово-когда: test_rung_theory_schema_matches_contract, test_five_steps_in_plan_prompt, test_refs_passed_as_context зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: ml-llm (свой pytest)

История C1 — материал без темы
- [ ] V7 [V] Доступ к материалу без темы и отказы по пути на 12 ручках
  Срез: R-29, R-31, R-34 · Контракт: C3, C12, C13
  Файлы: courses/access_registry/preflight.py, courses/topic_content/views.py (строки доступа 270/1035/1149/1206 и `@refuse_unless_path(v2=False, variant="topic-material")` на семи ручках по теме), courses/topic_content/rung_views.py (только `@refuse_unless_path(v2=True, variant="rung-material")` на пяти ручках), courses/access_registry/tests/test_preflight_rung_material.py, courses/access_registry/tests/test_access_path_refusals.py
  Зависит от: K1, K2, K3, K4 · Приёмка: AC-17, AC-13, AC-15 — TC1
  Готово-когда: test_preflight_course_from_material_field, test_author_2xx_stranger_403_anon_401_without_topic, test_legacy_material_same_course, test_response_topic_id_null_not_string, test_topic_endpoints_422_topic_material_on_flag (7), test_rung_endpoints_422_rung_material_off_flag (5), test_off_flag_unchanged зелёные
  Риск: deep · Размер: M (24) · Тест-группа: platform
- [ ] V12a [V] Вставные вопросы и IE-9/IE-10 без темы
  Срез: R-28 · Контракт: C3
  Файлы: courses/topic_content/models.py (только `EmbeddedItem.clean()` IE-9/IE-10, `:661–676`), courses/topic_content/embedded_items/services.py, courses/topic_content/embedded_items/tests/test_rung_carrier.py
  Зависит от: K1 · Приёмка: AC-4 — TC1
  Готово-когда: test_ie9_no_attribute_error_without_topic, test_ie10_foreign_knowledge_refused_on_rung_carrier, test_embedded_knowledge_from_rung зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: banks
- [ ] V12b [V] Читатели курса материала: покрытие, редактор графа, факты гейта
  Срез: R-28 · Файлы: courses/topic_content/coverage/{check,gate}.py, courses/course_graph_editor/read.py, courses/course_pipeline/gates/facts.py, courses/task_classes/gate_rules.py, courses/topic_content/coverage/tests/test_coverage_without_topic.py
  Зависит от: K1 · Приёмка: AC-4 — TC1
  Готово-когда: test_coverage_check_course_from_material, test_graph_editor_keys_not_none_bucket, test_facts_without_topic зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: content

История C2 — материал ступени (сервер и клиент вместе)
- [ ] V9 [V] Добавить теорию, версии, переключение, носитель — насквозь
  Срез: R-30 (4 из 5), R-32 (создание), R-33 (версии в редакторе) · Контракт: C8, C13, C17
  Файлы: courses/topic_content/rung_material.py, courses/topic_content/tests/test_rung_material_endpoints.py, services/frontend/utils/rungMaterial.ts (тела), …/content/rung/AddRungTheoryButton.tsx, __tests__/components/contentRungVersions.test.tsx, __tests__/components/contentRungAddTheory.test.tsx, docs/api/endpoints/{post-course-task-class-theory,get-course-topic-content-versions,post-course-topic-content-switch-current,patch-course-topic-content-carrier}.md (тела)
  Зависит от: K1, K2, K5 · Приёмка: AC-18, AC-17 — TAC, TC1
  Готово-когда: test_add_theory_creates_empty_draft_group, test_double_click_serialized, test_versions_by_group_no_topic, test_switch_current_by_group_calls_window, test_carrier_rename_place, test_access_5_roles; contentRungVersions.test (редактор на флаге: список версий и переключение по id материала, ответ той же формы, что в серверном тесте), contentRungAddTheory.test зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V9b [V] Импорт документа в носитель ступени — насквозь
  Срез: R-30 `populate-from-documents`, R-32 (импорт) · Контракт: C8, C13, C17
  Файлы: courses/topic_content/passthrough_rung.py, courses/topic_content/tests/test_rung_populate.py, services/frontend/utils/rungPopulate.ts (тело), __tests__/components/contentRungPopulate.test.tsx, docs/api/endpoints/post-course-topic-content-populate-from-documents.md (тело)
  Зависит от: K1, K2, K5 · Приёмка: AC-18 — TAC
  Готово-когда: test_populate_passthrough_into_carrier_topic_null, test_populate_llm_generate_group_from_carrier, contentRungPopulate.test зелёные; запись — только через `rung_writer`, `check_topic_content_writes.py` зелёный
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V10 [V] Разделы ступени: карта и знания раздела — насквозь
  Срез: R-4, R-32 (разметка), R-33 (выбор знаний, «Карта подхода», шаги) · Контракт: C4, C14, C17
  Файлы: courses/rung_theory/section_rules.py, courses/topic_content/serializers.py, courses/rung_theory/tests/test_section_rules.py, …/content/rung/knowledge.ts (тело, читает `rungTheory.ts`), …/content/SectionKnowledgePicker.tsx, …/content/SectionsList.tsx, …/content/SectionsRail.tsx, __tests__/components/contentSectionKnowledgeRung.test.tsx
  Зависит от: K1, K2, K4, K5 · Приёмка: AC-16 — TAC
  Готово-когда: test_second_map_already_taken, test_map_on_backing_not_applicable, test_section_knowledge_ids_validated_not_knowledge, test_map_payload_is_block_array; contentSectionKnowledgeRung.test (сверху C(R), поиск; OCC `expected_updated_at`; «Карта подхода»; шаги нумерованы) зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content
- [ ] V11 [V] Форк, пересборка и читатели в `services.py`; текст `force`
  Срез: R-32 (форк, пересборка), R-28 (`services.py:606/835/879/1416/1497/1637`) · Контракт: C3, C4, C14
  Файлы: courses/topic_content/services.py, courses/topic_content/tests/test_fork_rebuild_rung.py, …/content/ContentEditorDrawer.tsx (только текст `force` пересборки), __tests__/components/contentEditorRebuildForce.test.tsx
  Зависит от: K1, K4, K5 · Приёмка: AC-16, AC-4 — TAC, TC1
  Готово-когда: test_fork_keeps_knowledge_ids_both_paths, test_rebuild_keeps_map_and_uses_course_discipline, test_confirm_without_topic_no_doesnotexist, test_reject_and_delete_by_id_pass_course_and_replaced_version, contentEditorRebuildForce.test зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content

История D — перенос
- [ ] V20 [V] Перенос «Теорий» на ступени, удаление оболочек, дозаполнение `course`, отчёт, раннбук
  Срез: R-21 пп. 1–9 · Контракт: C1–C8
  Файлы: courses/topic_content/rung_theory_migration.py, courses/rung_theory/transfer.py, courses/rung_theory/course_fill.py, courses/rung_theory/report.py, courses/management/commands/migrate_rung_theory.py, courses/rung_theory/tests/test_content_transfer.py, courses/rung_theory/tests/test_content_course_fill.py, docs/meta/process/rung-theory-migration-runbook.md (тело)
  Зависит от: K1, K2 · Приёмка: AC-5, AC-13 — TDE
  Готово-когда: test_dry_run_writes_nothing, test_apply_moves_versions_sections_bytewise, test_shells_deleted_with_snapshot_logged, test_second_apply_zero_changes, test_course_with_student_refused, test_no_llm_no_ledger, test_course_fill_only_null_rows, test_report_from_journal, test_journal_dump_count_matches зелёные
  Риск: deep · Размер: M (24; больше ~300 строк — `course_fill` и `report` отдельной задачей) · Тест-группа: content
  Примечание: оболочки удаляет вызовом писателя `course_structure/deletion.py`, файл не правит (его правит V17b)

История E — гейты
- [ ] V19a [V] Четыре правила гейта 2 на флаге (тела)
  Срез: R-22 · Контракт: C11, C12
  Файлы: courses/course_pipeline/gates/rules_rung_theory.py, courses/course_pipeline/tests/test_rules_rung_theory.py
  Зависит от: K1, K2, K3 · Приёмка: AC-9 — TDE
  Готово-когда: test_knowledge_missing_blocker_by_C0, test_deleted_section_blocks_despite_snapshot, test_unmarked_section_warning_except_intro_and_map, test_outdated_warning_not_blocking_moderation, test_map_missing_blocker зелёные; `registry.py` не тронут
  Риск: обычный · Размер: M (15) · Тест-группа: saga
- [ ] V19b [V] Снятие правил «Теории» на флаге, `ksa-task-class-inadequate`
  Срез: R-23 «снимаются», AC-21; привязка `reading-material-outdated` снимается вместе с правилом
  Файлы: courses/graph_invariants/structure_gate.py, courses/course_pipeline/gates/rules_content.py, courses/course_pipeline/gates/rules_topic_content.py, courses/course_pipeline/gates/rules_structure.py (`READING_MATERIAL_OUTDATED` `:485`, `_ksa_task_class_inadequate_check` `:662–772`), courses/course_pipeline/gates/registry.py (только снятие привязки `:220`), courses/task_classes/readiness.py, courses/task_classes/predicates.py, courses/course_pipeline/tests/test_reading_rules_off_on_flag.py
  Зависит от: K1, K3 · Приёмка: AC-9 (снятые правила), AC-21 — TDE
  Готово-когда: test_reading_rules_silent_on_flag_fire_off_flag, test_a_lines_missing_reading_not_applied_on_flag, test_ksa_inadequate_silent_for_S_or_jit зелёные; `test_api_error_registry` зелёный (выведенный код без привязки)
  Риск: обычный · Размер: M (15) · Тест-группа: saga
  Внешний конфликт: **сильный** (шаг 6 правит `structure_gate.py`, `rules_structure.py`, `registry.py`). Брать, когда задача шага 6 на этих файлах не в полёте
- [ ] V19c [V] Откат гейта 2 по условию блокера
  Срез: R-23 «откат» · Контракт: C11, C14
  Файлы: courses/course_pipeline/rung_reopen.py, courses/saga/gate_backing.py, courses/saga/reopen.py, courses/course_pipeline/gating.py, courses/saga/tests/test_reopen_rung_theory.py
  Зависит от: K1, K2, K4 · Приёмка: AC-20 — TDE
  Готово-когда: test_complete_approval_no_reopen, test_other_rung_edit_no_reopen, test_delete_or_reject_covering_version_reopens, test_approved_fork_without_section_reopens, test_backing_lost_predicate_false_on_flag, test_off_flag_unchanged зелёные
  Риск: deep · Размер: M (24) · Тест-группа: saga
  Внешний конфликт: `saga/` — шаг 6

История F — структура и окно ступени
- [ ] V17a [V] Нет «Теории» как класса на флаге: сервер и окно
  Срез: R-1, R-27
  Файлы: courses/task_classes/services.py (`kind`), courses/task_classes/rung_layout.py, courses/structure_gen/skeleton.py, …/structure/TaskClassModal.tsx, …/structure/TopicTreePanel.tsx, courses/task_classes/tests/test_no_reading_kind_on_flag.py, __tests__/components/taskClassModalNoKind.test.tsx
  Зависит от: K1 · Приёмка: AC-11 — TFG
  Готово-когда: test_kind_content_reading_422_not_applicable, test_skeleton_no_reading_on_flag, taskClassModalNoKind.test зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: banks
  Внешний конфликт: **сильный** (`TaskClassModal.tsx`, `task_classes/services.py` у шага 6). Брать после вливания задачи шага 6 на этих файлах
- [ ] V17b [V] Перегенерация и удаление ступени с теорией
  Срез: R-16, R-17, R-17a, R-28 (`rung_layout_db.py:1137`, `parent_deletion.py:130`)
  Файлы: courses/task_classes/rung_regen.py, courses/task_classes/rung_layout_db.py, courses/course_structure/deletion.py, courses/topic_content/parent_deletion.py, …/structure/<окно удаления ступени>.tsx (одна строка текста), courses/task_classes/tests/test_regen_delete_rung_theory.py
  Зависит от: K1 · Приёмка: AC-10 — TFG
  Готово-когда: test_kept_key_keeps_theory, test_gone_rung_with_theory_parked, test_no_reading_match_on_flag, test_delete_rung_with_approved_theory_parks, test_unapproved_theory_deleted_with_rung зелёные; `check_course_structure_writes.py` зелёный
  Риск: deep · Размер: M (24) · Тест-группа: banks
  Внешний конфликт: `course_structure/` — шаг 6

История G — уроки и трек
- [ ] V13 [V] Теория нужных ступеней для урока Б, контекста генерации задач и банка диагностики
  Срез: R-20, R-28 (контекст, банк) · Контракт: C3, C4
  Файлы: courses/topic_content/rung_sections.py, courses/dialogue/material_b.py, courses/topic_content/generation/context.py, courses/topic_content/generation/dispatch.py, courses/diagnostic_bank/payload.py, courses/dialogue/tests/test_material_b_rung_theory.py, courses/topic_content/generation/tests/test_context_rung_theory.py, courses/diagnostic_bank/tests/test_payload_rung_material.py
  Зависит от: K1 · Приёмка: AC-12 (урок Б), AC-4 (контекст) — TFG, TC1
  Готово-когда: test_source2_sections_by_task_knowledge, test_map_always_included, test_backing_source_unchanged, test_supportive_sections_from_rung_theory, test_diagnostic_payload_course_from_material, test_dispatch_without_topic_order зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: lessons, content, banks
  Внешний конфликт: шаг 6 переводит `dialogue/` на читателя задач курса — пробное слияние
- [ ] V14 [V] Урок А по ступени, «Опирается на», чтение теории учеником — насквозь
  Срез: R-18, R-19 · Контракт: C11, C13
  Файлы: courses/lesson/mode_a/services.py, courses/lesson/mode_a/theory_read.py (тело), courses/topic_content/lesson_modes.py, courses/lesson/serializers.py, services/frontend/utils/lessons.ts, …/mode-a/LessonModeA.tsx, …/mode-a/LessonDependsOn.tsx, courses/lesson/mode_a/tests/test_mode_a_rung.py, __tests__/components/lessonDependsOn.test.tsx, **docs/api/endpoints/get-course-task-class-theory-read.md (тело)**
  Зависит от: K1, K2 · Приёмка: AC-12 (урок А) — TFG
  Готово-когда: test_lesson_a_by_rung_no_fallbacks_on_flag, test_refs_block, test_student_read_theory_without_credit, test_no_lesson_a_when_only_map, lessonDependsOn.test зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: lessons
  Внешний конфликт: шаг 6 снимает проверки режимов в `mode_a`
- [ ] V16 [V] Трек: урок А ступени перед практикой
  Срез: R-20a · Файлы: courses/track_manage/services.py, courses/track_manage/planner.py, courses/track_manage/tests/test_track_rung_theory.py
  Зависит от: K1, K2 · Приёмка: AC-12 (трек) — TFG
  Готово-когда: test_lesson_a_before_practice_by_carrier, test_no_lesson_a_goes_to_practice, test_no_user_task_class_for_reading_on_flag зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: graph

### Хвост

- [ ] H1 [H] Реестры документов, статусы, свежесть, хвосты ревью
  Файлы: docs/INDEX.md, docs/TAGS.md (`check_docs_index.py --fill`), frontmatter восьми документов фичи (`status: active`, `updated`), CHANGELOG, журнал концепции, ADR-099 (D9 на флаге — О-6), статус спеки, docs/engineering/module-map.md (финальная пересборка), courses/rung_theory/README.md (сверка с фактом), дословные находки «можно сливать, хвост»
  Зависит от: все
  Готово-когда: `check.sh`, `gen_module_map.py --check`, `check-codes.py`, `check_api_doc_coverage.py`, `check_docs_index.py`, `check_doc_freshness`, проверки ссылок зелёные; **в модулях `[T]` фичи ноль `expectedFailure`** (иначе — доклад с именем AC); каждая находка «хвост» закрыта или перенесена задачей
  Риск: обычный · Размер: M (15) · Тест-группа: governance

### Покрытие требований

R-1 V17a · R-2 K1 · R-3 K1 + писатели · R-4 V10 · R-5–R-7 V1 · R-8 V4/V5 · R-9–R-12a V1 + V2 ·
R-13 K4/V4/V5 · R-14 V4/V5 · R-15 V6 + V4 · R-16/R-17/R-17a V17b · R-18/R-19 V14 · R-20 V13 ·
R-20a V16 · R-21 V20 · R-22 K3 + V19a · R-23 V19b/V19c · R-24 K3 + V19b · R-25 K2 + V2 ·
R-26 K5 + V2 · R-27 V17a · R-28 K1 + V7 V11 V12a V12b V13 V14 V17b · R-29 V7 · R-30 K2 + V9/V9b ·
R-31 K3 + V7 · R-32 K1 + V4 V5 V9 V9b V10 V11 V20 · R-33 K5 + V9 V10 V11 · R-34 K3 + V7.
AC-1…AC-22: у каждого есть `[T]`, тест К (AC-14, части AC-9 и AC-15) или `acceptance` (AC-7 и
Playwright).

## 5. Карта владения горячими и общими файлами

Внутри фичи каждый общий файл переходит от владельца к владельцу только по ребру. Проба:
**0 пересечений `Файлы:` без пути** (`plan3.py overlaps()`).

| Файл | Цепочка владельцев |
|---|---|
| `topic_content/models.py` | K1 → V12a |
| `topic_content/services.py` | K4 → V11 |
| `topic_content/views.py` | K4 → V7 |
| `topic_content/rung_views.py` | K2 → V7 (только декораторы) |
| `topic_content/rung_material.py`, `passthrough_rung.py` | K2 → V9; K2 → V9b |
| `rung_theory/needs.py`, `section_rules.py`, `api.py` | K2 → V1; K2 → V10; K2 → V2 |
| `lesson/mode_a/theory_read.py` | K2 → V14 |
| `generation/rung_theory_units.py`, `rung_theory_merge.py` | K4 → V4; K4 → V5 |
| `course_pipeline/rung_reopen.py` | K4 → V19c |
| `gates/rules_rung_theory.py`; `gates/registry.py` | K3 → V19a; K3 → V19b |
| `config/response-codes.json`, `api-problems.json`, `locale/ru/problems.json`, `problem_types.py` | только K3 |
| `utils/rungTheory.ts`, `rungMaterial.ts`, `rungPopulate.ts` | K5 → V2; K5 → V9; K5 → V9b |
| `ContentTab.tsx`; `RungContentTab.tsx`; `AddRungTheoryButton.tsx`; `knowledge.ts` | K5; K5 → V2; K5 → V9; K5 → V10 |
| `ContentEditorDrawer.tsx` | K5 → V11 (только текст `force`) |
| 7 документов ручек, раннбук | K2 (заготовка) → V2, V9, V9b, V14, V20 (тело) → H1 (frontmatter) |
| `docs/TAGS.md`, `docs/INDEX.md` | K2 (`--fill`) → H1; `TAGS.md` — класс `regen` |
| `module-map.md`, `module-graph.json` | класс `regen`, финал — H1 |
| `utils/auth.ts`, `test-registry.json`, `test-location.json` | никто |

## 6. Расписание (N = 4, партии, без шума и доработок, HLFET)

```
слот1: K2[0-15]  TAC[15-30] TFG[30-45]  V17b[45-69] V12a[69-84] V10[84-108] V14[108-123] V11[123-138]
слот2: K3[0-15]  TB[15-30]  V6[30-45]   V2[45-69]   V9b[69-84]  V7[84-108]  V17a[108-123] V19b[123-138]
слот3: K5[0-15]  TC1[15-30] K4[30-54]   V20[54-78]  V4[78-102]  V19c[102-126] V12b[126-136] V16[136-146]
слот4: K1[0-24]  TDE[24-39] ··· V1[43-67] V9[67-82] V5[82-106]  V13[106-121] V19a[121-136]  ···  H1[168-183]
```

Без шума — 197 мин, занятость 2.89. С шумом и p = 0.43 средняя занятость по получасам:
**4.0 / 3.8 / 3.5 / 3.8 / 4.0 / 3.8** / 2.6 / 1.0 / 0.5 / 0.2. Провал фазы К на 60–90-й минуте
стал мельче (3.5 против 2.8 в круге 2): ожидание K4 закрывают пять `[T]` и три К, стартующие
в минуту 0. Остался один провал — **хвост доработок после ~180-й минуты**. Слоты его не лечат,
лечат снижение p и вливание партиями.

Чувствительность к размеру К (N = 4 / N = 2, p = 0.43):

| | S | P | N = 4 | N = 2 |
|---|---|---|---|---|
| План | 78 | 7.29 | 281 | 492 |
| K2 ×3 | 108 | 5.55 | 300 (+7 %) | 515 (+5 %) |
| K4 ×2 | 102 | 5.81 | 298 (+6 %) | 510 (+4 %) |
| K3 ×2 или K5 ×2 | 78 | 7.49 | 284–285 (+1 %) | 504 (+2 %) |

## 7. Ревью, доработки, вливания, CI

1. **Сдача освобождает слот.** Перед ревью скрипт делает пробное слияние со всеми ветками обеих
   фич в полёте, `hold` и `check.sh`. Конфликт или красная проверка — `доработка` без ревьюера.
2. **Ревью** — пул R ≥ K − 1, при N = 2 — R = 1–2 (R = 2 даёт −6…−7 %). Линзы: `[K]` — «хватит
   ли срезам» и для K1/K4 — «тест К держит свой AC»; `[T]` — «каждый AC покрыт, тест бьёт обе
   стороны»; `[V]` — логика, `Контракт:`, `Готово-когда:`, у срезов насквозь — «обе стороны
   видят одну форму ответа». Вердикт «можно сливать, хвост» уходит в H1. Доработку берёт любой
   свободный, второй круг — по диффу, предел два круга.
3. **Вливание** — одна очередь координатора, партиями до 4. Партия — это rebase всех на
   вершину, одна узкая проверка по объединению `Тест-группа:` и `--ff-only` по очереди. Красная
   партия делится пополам. Вливание по одному при общем с шагом 6 координаторе (c = 12) даёт
   443 мин вместо 308 партиями при N = 4: партии обязательны.
4. **CI как общий ресурс (замечание 13).** «Влита» = локальное вливание с узкой проверкой.
   Вливание CI не ждёт. Пушит один координатор на обе фичи, не чаще одного раза за прогон CI
   (`cicd.yml:70–72`: `cancel-in-progress: true`, пуш во время прогона его отменяет). Расчёт
   при прогоне 21 мин на всех 3 раннерах: шагу 8 нужно в среднем **9.7 пушей при N = 4**
   (26.6 партий за 280 мин) и **15.2 при N = 2** (за 492 мин). Вместе с шагом 6 это больше,
   чем помещается (280 / 21 ≈ 13 прогонов). Поэтому пуш общий: он несёт всё, что влито в
   обе фичи с прошлого зелёного прогона. CI занят на 100 %, но очередь к раннерам не растёт.
   Цена — красный прогон делится по партиям с прошлого зелёного, это до 6 партий двух фич. На
   критическом пути только последний прогон (15–28 мин, уже в сроке §0). В модели CI на
   каждом ребре нет, и по этому правилу его там нет и в процессе.
5. **Слоты делятся между фичами одним `next`** по объединённому графу и общей карте владения
   (правило круга 2, оценщик подтвердил, что эта мера сильнее). Отсюда основной сценарий N ≈ 2.

## 8. Предложения к `design.md` (с расчётом)

1. **Стек К → К не вводить.** В круге 2 стек K3 от K2 давал −8 мин на пути, потому что фаза К
   была узкой (3 К, `[T]` ждали K2). В круге 3 фаза К широкая: 5 К и 5 `[T]` в минуту 0. Тот
   же стек K4 от сданного K2 в той же модели даёт **280 против 281 мин** (N = 4, p = 0.43),
   **313 против 315** (p = 0.61) и **493 против 492** (N = 2). Правило design §2.1 оставить
   как есть. Узкую фазу К лечит ширина (`[T]` без зависимостей), а не стек.
2. **AC, целиком закрытые К, — приёмка тестом К, а не `[T]`.** Если `[T]` покрывает AC-14, а
   K1 его закрывает, то при строгой отметке вливание K1 обязано ждать вливания TAC. Иначе
   неожиданный успех покраснит ветку, и `[T]` фактически становится зависимостью К. Расчёт
   варианта «К ждёт свою `[T]`» (`MODE['kwait']`): S 78 → 93, N = 4: 292 против 281 мин
   (+4 %), N = 2: 495 против 492. Предлагаю п. 7 §1 и строку пробы «покрытие AC → `[T]`»
   дополнить: «или тест К с линзой ревью К».
3. **Предел К — по размеру и подсистемам, а не числом 1–3.** Три проверки проекта требуют
   ключ и первое употребление в одном коммите (§2.3), поэтому К растёт вместе с реестрами. Пять
   К по 1–2 подсистемы на 16 % W дают фазу К шире, а путь не длиннее, чем три К со стеком.
   Формулировка: «К ≤ M каждая, ≤ 20 % W, глубина 1; больше трёх — `Почему не три:`».
4. **Проба на скелете** (замечание оценщика §7, поддерживаю). До старта `architect` собирает
   скелет из `Файлы:` К (пустые модули с импортами из `Контракт:`) и прогоняет пять проверок:
   `check_module_boundaries`, `check-codes`, `check_api_doc_coverage`, `check_docs_index`,
   `check_test_location`. Все находки круга 2 видны так до первой строки кода.
5. **«Общий образец ответа» — только если оба теста видят файл.** В проектах, где сервер и
   клиент тестируются в разных контейнерах (здесь `django-api` монтирует только свой каталог),
   образец не работает. Тогда правило одно: срез насквозь.

## 9. Что проверить после реализации

- Сколько пушей CI пришлось на окно и сколько красных прогонов пришлось делить. Если больше
  одного на фичу — партии крупны или узкая проверка партии слишком узкая.
- Выдержали ли K2 и K4 размер M. При K2 ×3 прогноз +7 %, при K4 ×2 +6 %.
- Сколько отметок `expectedFailure` снял каждый срез и сколько осталось к H1. Если к H1
  осталось больше нуля, значит, отметка `[T]` не привязана к AC среза.
- Доля отказов «расхождение сторон» после склейки срезов. Если она больше 10 % отказов, значит,
  типы K5 расходятся с сериализацией K2, и нужен генерированный клиент из схемы
  `/api/v1/schema/`.
- Фактическое p этой фичи. При p = 0.61 и N = 2 план бейзлайн не обгоняет (§0), и это первое,
  что надо смотреть.

## 10. Открытые места для `architect`

- Адрес чтения теории учеником (R-19): `GET /api/v1/courses/{c}/task-classes/{tc}/theory/read`.
  Подтвердить до старта K2: шов C13 и заготовка документа зависят от него.
- `refuse_unless_path` в `access_registry` (ярус 1) — как предполётная проверка ручки.
  Альтернатива — `course_structure` (ярус 2). Корень запрещён (П-9).
- Ярус 3 для `rung_theory` записать в П-9 `module-rules.md` (делает K2).
- Окно удаления ступени (V17b) — имя файла на фронте не найдено (каталог `structure/`, общий с
  шагом 6).
- `gen_problem_types.py`: поддержку `state` у `gate_blockers` согласовать с шагом 6. Если шаг 6
  тоже выводит код причины, генератор правит один из двух, а второй берёт его вливание.
