# Фича 2 (шаг 8, теория ступени): разложение и план, команда B, круг 2

Дата 2026-11-24. Процесс — `design.md` (К → `[T]` в окне К → веер `[V]` → `[H]`). Вход —
`feature-2-description.md`, санированная спека, код и документы на базовом коммите `053602900`.
Прошлая версия — `f2-B-r1.md`. Расчёт — `f2B2/plan2.py` (проба P = W/S, HLFET, событийная
модель), прогоны — `f2B2/runs.py`, `f2B2/runs2.py`, раскладка тестов по группам CI — `f2B2/keys.txt`
через `classify` из `evalchk/test_registry_base.py`.

Модель: вес 10 мин × 1.6 (deep) × 1.5 (M); ревью 8 мин; доработка 0.7 веса, второй круг с
вероятностью p/2, предел — два круга; разброс 0.7–1.4; 200–300 прогонов. **Новое в круге 2:
вливание идёт одной очередью координатора, c = 6 мин на вливание.** Вариант «партия» — до 4
готовых веток за c + 2·(n − 1) (rebase всех, один прогон проверки, `--ff-only`). Стек: задача
стартует от сданного коммита предка, а вливается только после него.

Честная пометка из круга 1 остаётся в силе: из диффа базового коммита в `docs/TAGS.md` я видел
только сводную фразу бейзлайна с числами задач, уровней и deep. Задач и графа бейзлайна я не
открывал.

## 0. Итог в цифрах

| Мера | Круг 1 | Круг 2 |
|---|---|---|
| Задач | 38 (3 К, 8 T, 26 V, 1 H) | **32** (3 К, 5 T, 23 V, 1 H), deep — 10 |
| W, S, P = W/S | 563, 63, 8.9 | **550, 78, 7.05** |
| Критический путь | K1 → deep M → H1 | **K2 → K3 (стек) → V1 (любой deep M) → H1** |
| Проба P ≥ 2K | норма при K ≤ 4 | норма при K ≤ 3; при K = 4 предупреждение (нужно 8), при K = 5 — тоже |
| Фаза К | 9 % W | 11 % W, глубина 2 только у пары K2 → K3 (стек, `Почему не одна:`) |
| Пересечения `Файлы:` без пути | 0 | 0 (`plan2.py`), с названными пределами §5 |
| Задачи с тестами в `core` | ≥ 9 (замечание оценщика) | **0** (все 36 имён прогнаны через `classify`) |

**Основной сценарий — пул делится с шагом 6, на шаг 8 приходится N ≈ 2.**

| Сценарий (вливание c = 6) | p = 0.43 (сегодня) | p = 0.15 (цель) | Срок до приёмки при p = 0.43 |
|---|---|---|---|
| **N = 2, R = 1 (основной)** | **495 мин** (p90 543) | 398 (p90 425) | **≈ 8.8–9.4 ч**, p90 ≈ 9.9 ч |
| N = 2, R = 2 | 450 (p90 482) | 372 | ≈ 8.1–8.6 ч |
| N = 3, R = 2, партии | 331 (p90 366) | 274 | ≈ 6.1–6.6 ч |
| N = 4, R = 3, по одному | 293 (p90 317) | 265 | ≈ 5.5–6.0 ч |
| N = 4, R = 3, **партии** | **278** (p90 308) | 229 | ≈ 5.2–5.8 ч |
| N = 5, R = 4, по одному | 284 (−3 % к N = 4) | 265 (0 %) | ≈ 5.3–5.8 ч |
| N = 5, R = 4, партии | 251 (−10 % к N = 4) | 210 (−8 %) | ≈ 4.8–5.3 ч |

Срок до приёмки = веер + последняя проверка ветки в CI (15–28 мин) + приёмка последней истории
(20–40 мин).

Что изменилось в прогнозе по сравнению с кругом 1:
- **Очередь вливаний — второе узкое место после слотов.** При c = 6 и вливании по одному
  координатор занят 66–73 % времени веера, ветка ждёт вливания в среднем 17–24 мин при N = 4 и
  27–35 мин при N = 5. Занятость исполнителей падает до 2.4–2.7 из 4, и пятый слот даёт −3 % при
  p = 0.43 и 0 % при p = 0.15. Это подтверждает замечание оценщика. Снижение p при вливании по
  одному почти не помогает (293 → 265): работа упирается в очередь.
- **Партии вливания возвращают отдачу.** Ожидание падает до 7–10 мин, занятость поднимается до
  2.8–3.2, пятый слот даёт −8…−10 %. Партия — не новая сущность: это та же партия CI из
  `design.md` §1.10, которую сдвинули на шаг раньше, к вливанию (§6).
- **Если координатор общий для двух фич** (эквивалент c = 12), вливание по одному даёт при N = 4
  **469 мин**: слоты стоят, а занятость падает до 1.7. Партиями — 306 мин. Без партий общий
  координатор съедает весь выигрыш плана.
- **При N ≈ 2 решают слоты, а не очередь** (партии ничего не меняют: 495 = 495). Занятость 1.6
  из 2. Ширина плана (P = 7) в этом режиме не используется: узкое место — число исполнителей.
- **Чувствительность к K2 ×3** (реестры вышли втрое дольше): S = 108, P = 5.4. N = 4 с партиями —
  311 мин (+12 %), N = 2 — 513 (+4 %).

Сравнение с бейзлайном я не делаю: бейзлайн мне закрыт. По оценке оценщика, N ≈ 2 даёт к
бейзлайну −5…−20 %. Мои 8.8–9.4 ч попадают в его диапазон 8.4–9.9 ч.

Цена по медианам наблюдений (deep $4.9, обычный $0.94, ревью $1.5). Первый круг:
10 × 4.9 + 22 × 0.94 ≈ $70. При p = 0.43 модель даёт 49 запусков исполнителя и 49 ревью:
доработки ≈ $26, ревью ≈ $74, итого **≈ $170**. При p = 0.15 — 37 / 37, **≈ $133**.

## 1. Ответы на замечания круга 1

| # | Замечание | Что сделано |
|---|---|---|
| 1 | Нет очереди вливаний, c = 6 | Очередь в модели (`sim(..., c=6, batch=...)`), §0 и §7. Вывод: вливание партиями обязательно (§6) |
| 2 | Прогноз на 4 своих слота, а пул делится | Основной сценарий — N = 2, первая строка §0. N = 4 и N = 5 оставлены как «пул свой» |
| 3 | C19 не работает: исключения по точному ключу, 10–15 задач правят один JSON | Исключений нет совсем, `test-registry.json` никто не правит. **Имена тестов подобраны под правила групп**, все 36 модулей проверены `classify` (§2.3). Поле `Тест-группа:` исправлено у TA (теперь TAC), TD (теперь TDE), V1, V2, V20 (бывшие V20a/V20b): было `core`, стало `content`. У V17b — `banks` (имя `task_class` ловится раньше `structure`), у V9b — `content`, а не `documents` |
| 4 | Новые писатели `TopicContent` вне `WRITER_FILES`; `rung_theory/writer.py` вне пакета писателя | Писатель переехал в `topic_content/rung_writer.py`. **K1 вносит в `WRITER_FILES` все пять будущих файлов писателя сразу**: `rung_writer.py`, `generation/rung_theory_units.py` (V4), `generation/rung_theory_merge.py` (V5), `rung_material.py` (V9a), `rung_theory_migration.py` (V20). Скрипт сторожа больше никто не правит. V9b пишет только через `rung_writer` (§4) |
| 5 | Скрытое ребро K2 → K1 по ярусу; `pipeline_path.py` в корне нарушает П-9 | Проверено по `check_module_boundaries.py`. Пакет вне карты ярусов — ошибка, лишняя запись в карте — тоже (строки 421–428). Значит, **пакет `rung_theory` и его ярус заводит одна задача — K2**. K1 в `rung_theory` ничего не кладёт: журнал переноса — модель в `topic_content/models.py` (писатель журнала — тот же пакет, П-11), фикстуры — `topic_content/tests/rung_fixtures.py`. Корень = ярус 4 (`ROOT_TIER`), импорт корня пакетом — новый ключ П-9, проверка краснеет (строки 455–461). Поэтому `pipeline_path.py` переехал в `access_registry/` (ярус 1, импортирует только `models` и `problem_details` нижнего ядра). Попутно найдены три цикла П-8 (§2.2) |
| 6 | K2 перегружена, ~30 файлов, обычный M, от неё 24 среза | Разрезана: **K2 — пакет, ярус, коды, маршруты, заглушки (обычный)**; **K3 — окно и вызовы в горячих файлах (deep)**. Фронтовая К упразднена: фронт оказался резом по файлам, а не швом (§2.4). Всего К — три. Прогноз при K2 ×3 — в §0 |
| 7 | 38 задач — слишком много для очереди | 32 задачи. Слиты: V8 → V7; V12c + V13 → V13 (одно требование R-20); V20a → V20; TA + TC2 → TAC; TF + TG → TFG; TD + TE → TDE |
| 8 | TB недооценена; линза `[T]` не отличает тест от падающего на импорте | TB — M. Добавлен помощник `ac_pending` и строгая проверка причины ожидаемой неудачи при вливании `[T]` (§4, «Фаза `[T]`») |
| 9 | `ksa-task-class-inadequate` — в `gates/rules_structure.py` | Внесено в `Файлы:` V19b вместе с `task_classes/predicates.py`. Пересечение с шагом 6 — в §5 |

## 2. Как получена ширина

### 2.1. Три решения планирования (из круга 1, уточнены)

1. **Окно в фазе К вместо общих гигантов.** `topic_content/services.py` (2 703 строки), `views.py`
   (1 503), `generation/services.py` (1 221) по смыслу правят 8–10 требований. K3 ставит в них по
   одной строке вызова на каждое место и выносит тело в новый файл, которым владеет один срез.
   Контрфакт круга 1: без этого S = 108, P = 5.2.
2. **Инвариант в модели вместо дисциплины писателей** (K1). `clean()`/`save()` отказывает
   носителю ступени флагового курса с `topic ≠ NULL`, `course` ставит сама. Забывчивый писатель
   краснеет в тестах своего среза. Так закрывается причина отказа «расхождение запись/чтение».
3. **Подмена состава для потребителей.** `rung_theory/testing.py::patch_course_theory` (K2).
   Юнит-тесты потребителей состава не ждут V1, связку держат `[T]` на настоящем составе.

### 2.2. Направление импортов (новое в круге 2)

Проверено по `module-rules.md` (П-8, П-9, П-11) и `module-tiers.json` на базовом коммите.
`rung_theory` получает **ярус 3** и стоит над `topic_content` и `task_classes`, но под
`course_pipeline`, `lesson`, `dialogue`. Все рёбра идут в одну сторону. Без этого план круга 1
содержал три цикла П-8, и каждый был бы скрытым ребром между срезами:

| Цикл в круге 1 | Решение в круге 2 |
|---|---|
| `topic_content.services` → `rung_theory.reopen` → `course_pipeline`/`saga` → … → `topic_content` | Окно `topic_content/rung_listeners.py` по образцу существующего `phase_listeners.py`. Слушатель отката — `course_pipeline/rung_reopen.py`, регистрирует `CoursesConfig.ready()`. Незарегистрированный слушатель — громкий отказ, как в образце. Проверка регистрации — `courses/tests/test_handler_registration.py` (П-16) |
| `topic_content.generation` (V4, V5) → `rung_theory.needs` → `topic_content` | Тот же приём: окно даёт `compose_rung_theory(course, task_class)`, `rung_theory` регистрирует в нём `needs.rung_composition`. Генерация получает состав через окно (П-9, разворот) |
| `topic_content.generation.context` (V13) → `rung_theory.sections` → `topic_content` | `sections_for_knowledge` состав не читает: это запрос по разделам действующих версий курса. Поэтому он живёт в `topic_content/rung_sections.py` и принадлежит V13. Заглушка в К больше не нужна |
| `course_pipeline` (V19a) → `rung_theory` и `rung_theory.reopen` → `course_pipeline` | Откат перенесён в `course_pipeline` (см. первую строку). Теперь `course_pipeline → rung_theory` — единственное направление |

### 2.3. Тест-группы без исключений

`classify` смотрит исключения только по точному ключу и берёт первое совпавшее правило. Поэтому
модуль `courses/rung_theory/tests/test_needs.py` уходит в `core`, а потолок `core` — 2. Вместо
исключений имя каждого тест-модуля содержит слово своей группы. Важен порядок правил: `billing`
(`unit`, `money`, `cost`) идёт раньше `content`, `graph` (`topic`) — раньше `platform`,
`structure` (`pipeline`) — раньше `platform`, `banks` (`task_class`) — раньше `structure`. Слово
`backfill` в имени требует свежей базы (`_FRESH_DB`), поэтому его в именах нет. Результат прогона
(`f2B2/keys.txt`):

| Группа | Модули |
|---|---|
| content | `topic_content/tests/test_content_rung_carrier_invariants`, `test_migration_0307_rung_theory_schema`, `test_content_rung_hooks`, `test_rung_material_endpoints`, `test_rung_populate`, `test_fork_rebuild_rung`; `rung_theory/tests/test_content_rung_contracts`, `test_content_needs`, `test_content_needs_loader`, `test_content_rung_theory_api`, `test_section_rules`, `test_content_transfer`, `test_content_course_fill`; `topic_content/generation/tests/test_rung_theory_generate`, `test_rung_theory_merge`, `test_context_rung_theory`; `topic_content/coverage/tests/test_coverage_without_topic`; acceptance `test_content_composition_material`, `test_content_rung_generation`, `test_content_rung_transfer` |
| saga | `course_pipeline/tests/test_auto_pipeline_rung_theory`, `test_rules_rung_theory`, `test_reading_rules_off_on_flag`; `saga/tests/test_reopen_rung_theory`; acceptance `test_gate_rung_theory` |
| platform | `access_registry/tests/test_preflight_rung_material`, `test_access_path_refusals`; acceptance `test_access_rung_material` |
| banks | `topic_content/embedded_items/tests/test_rung_carrier`, `diagnostic_bank/tests/test_payload_rung_material`, `task_classes/tests/test_no_reading_kind_on_flag`, `test_regen_delete_rung_theory` |
| lessons | `dialogue/tests/test_material_b_rung_theory`, `lesson/mode_a/tests/test_mode_a_rung`; acceptance `test_lesson_structure_rung` |
| graph | `track_manage/tests/test_track_rung_theory` |
| фронт | `rungContentTab.test.tsx`, `contentEditorRung.test.tsx` → content; `taskClassModalNoKind.test.tsx` → banks; `lessonDependsOn.test.tsx` → lessons. Проверено: имена вида `rungMaterialApi.test.ts` или `rungDeleteDialog.test.tsx` ушли бы в `core`, поэтому их нет |

Правило для `architect` и проба: **поле `Тест-группа:` вычисляется скриптом из имён тестов в
`Готово-когда:`, а не пишется руками.** Ручное поле ошиблось у шести задач круга 1.
Тест-модуль, попавший в `core`, — красное в пробе плана. Для базы это строка в
`task_pairs.py plan`: проект даёт команду классификации, и проба её вызывает.

### 2.4. Почему упразднена фронтовая К

В круге 1 K3 заводил обёртки в `utils/auth.ts` (5 259 строк), типы и ветку в `ContentTab.tsx`. У
проекта уже есть доменные файлы обёрток: `utils/courseGoal.ts`, `topicKsa.ts`, `tracks.ts`,
`lessons.ts`. Поэтому каждый фронтовой срез заводит свой файл обёрток: V3 — `utils/rungTheory.ts`
(R-25 и `theory_mode`), V22 — `utils/rungMaterial.ts` (R-30 и `knowledge_ids` раздела), V14 —
`utils/lessons.ts`. `auth.ts` не правит никто. Редактор V3 открывает существующим
`ContentEditorDrawer` с уже имеющимися пропсами (`courseId`, `taskClassId`, `topicContentId`,
`contentTopicGroup` — проверено на базовом коммите), а ветку по флагу внутри редактора делает V22.
Ребро V3 → V22 не нужно. Итог: V3, V22 и V6 стартуют в минуту 0 и заполняют окно К.

## 3. Карта швов (`contracts.md`)

| C | Шов | Владелец | Потребители |
|---|---|---|---|
| C1 | `TopicContent.carrier_purpose` (`theory` \| NULL) и инварианты R-2 | K1 | V4 V5 V9a V9b V10 V11 V12a V12b V13 V14 V17b V19a V19b V19c V20, все `[T]` |
| C2 | `TopicContent.topic`, `TopicContentGenerationError.topic` → `null=True`. На флаге у носителя ступени `topic ≠ NULL` — отказ `clean()`, без флага `topic = NULL` — отказ (AC-14) | K1 | все писатели |
| C3 | `TopicContent.course` (FK PROTECT, `null=True`, `related_name="course_materials"`), `save()` ставит его сам; миграция заполняет все строки | K1 | V7 V11 V12a V12b V13 V20 |
| C4 | `section_type='approach_map'` (только `choices`); `TopicContentSection.understanding_step` 1…5 \| NULL | K1 | V4 V5 V10 V11 V13 V14 V19a V22 |
| C5 | Модель журнала `RungTheoryMigrationRecord` **в `topic_content/models.py`**, менеджер `record(...)` | K1 | V20 |
| C6 | Миграции `0307_rung_theory_schema`, `0308_rung_theory_migration_record` (номера — следующие свободные при вливании K1); тест обратной миграции, **включая строки после переноса** (`topic = NULL` с `task_class`), — `topic_content/tests/test_migration_0307_rung_theory_schema.py` (правило жизни тестов миграций: откат схемы — только в модуле `test_migration_<NNNN>`) | K1 | V20 |
| C7 | Фикстуры `topic_content/tests/rung_fixtures.py::flag_course_with_ladder(...)`, `legacy_course_with_reading(...)` | K1 | все backend `[V]` и `[T]` |
| C8 | Писатель `topic_content/rung_writer.py`: `create_rung_carrier_version(...)`, `write_theory_blocks(version, blocks, *, start_index)` — минимальное настоящее тело (текст, `knowledge_ids`, `understanding_step`, `section_type`); строки `WRITER_FILES` для пяти файлов писателя | K1 → шаг 4 Lexical дописывает V4 | V5 V9a V9b V20 |
| C9 | Пакет `rung_theory` (ярус 3 в `module-tiers.json`), `AGENTS.md`, `README.md` с полной публичной поверхностью по этой таблице | K2 | все |
| C10 | `rung_theory/types.py`: `TheoryState`, `RungTheory`, `CourseTheory`, `TheoryBlock`; `rung_theory/testing.py::patch_course_theory` | K2 | все |
| C11 | `rung_theory/needs.py`: `course_theory(course)`, `rung_composition(course, task_class)`, `serving_version(group)`, `primary_carrier(rung)` — сигнатуры, тело `NotImplementedError` | K2 → тело V1 | V2 V14 V19a V19c, окно C14 |
| C12 | Коды: `/problems/course-path-not-applicable` (`rung-material`, `topic-material`), `rung-theory-knowledge-missing`, `rung-theory-section-unmarked`, `rung-theory-outdated`, `rung-approach-map-missing`; выведение `reading-material-outdated` (R-24); строки `api-problems.json` | K2 | V7 V9a V9b V14 V17a V19a |
| C13 | Маршруты и заглушки: R-30 ×5 → `topic_content/rung_views.py` (501, с декоратором пути); R-25 → `rung_theory/api.py`; R-19 `GET /api/v1/courses/{c}/task-classes/{tc}/theory/read` → `lesson/mode_a/theory_read.py`; строки реестра доступа; `access_registry/pipeline_path.py::refuse_unless_path(v2, variant)` (заглушка «пропустить») | K2 | V2 V7 V9a V9b V14 |
| C14 | Окно `topic_content/rung_listeners.py`: `validate_section` (регистрирует `rung_theory.section_rules`), `on_serving_change` (регистрирует `course_pipeline.rung_reopen`), `compose_rung_theory` (регистрирует `rung_theory.needs`); регистрация в `CoursesConfig.ready()`; вызовы в `create/update_topic_content_section`, после утверждения, переключения, отклонения и удаления версии; `course_pipeline/rung_reopen.py` (заглушка) | K3 | V10 V19c V4 V5 V11 |
| C15 | `regenerate-content`: поле `theory_mode` (`generate`/`complete`/`map`), на старом пути — 422 `not-applicable`; переход в `generation/services.py` на заглушки `generation/rung_theory_units.py::plan_generate` и `generation/rung_theory_merge.py::plan_complete/plan_map`; декоратор пути на семи ручках по теме в `views.py` | K3 | V3 V4 V5 V7 |
| C16 | Контракт ml-llm `kind=rung_theory` (запрос и ответ, шаг 4 — `question`/`rule`, карта абзацами). **Только в `contracts.md`**: JSON-схему в ml-llm заводит V6, тип на стороне django — V4, сверку держит TB | `contracts.md` | V4 V6 |
| C17 | Фронт: форма ответа R-25, состояния, ответы R-30 — **только в `contracts.md`**, файлы типов у срезов | `contracts.md` | V3 V22 V14 |
| C18 | Помощник `courses/tests/acceptance/rung_theory/pending.py::ac_pending("AC-n")` (§4, фаза `[T]`) | K2 | все `[T]` |

## 4. Задачи

Общее для всех `[V]`: сдача — `check.sh` зелёный, сняты `ac_pending` своих `AC-n` в приёмочных
тестах, вывод `hold` (откат не-тестовых `Файлы:` к базе краснит тесты `Готово-когда:`). Вес:
S = 10, M = 15, deep ×1.6. `Тест-группа:` вычислена `classify`.

### Фаза К

- [ ] K1 [K] Схема материала ступени, инварианты, журнал, писатель, фикстуры
  Контракт: C1–C8
  Файлы: courses/topic_content/models.py (поля, `clean/save`, `__str__` без темы, модель журнала; IE-9/IE-10 не трогать — V12a), courses/migrations/0307_*.py, courses/migrations/0308_*.py, courses/topic_content/rung_writer.py, scripts/check_topic_content_writes.py (только `WRITER_FILES`), courses/topic_content/AGENTS.md (строка о писателе), courses/topic_content/tests/rung_fixtures.py, courses/topic_content/tests/test_content_rung_carrier_invariants.py, courses/topic_content/tests/test_migration_0307_rung_theory_schema.py
  Зависит от: —
  Приёмка: AC-14; AC-13 (столбцы старого пути, `course = topic.course`)
  Готово-когда: test_carrier_purpose_invariants, test_course_filled_by_save_with_and_without_topic, test_topic_null_refused_off_flag, test_topic_set_refused_on_flag_rung_carrier, test_writer_writes_blocks_with_step_and_knowledge, test_migration_fills_course, test_reverse_migration_restores_topic, test_reverse_migration_after_transfer_rows зелёные; `check_topic_content_writes.py` зелёный
  Риск: deep · Размер: M (24) · Тест-группа: content
  Внешний конфликт: цепочка миграций шага 6 (`serial: migrations`), номер ставится при вливании

- [ ] K2 [K] Пакет `rung_theory`, ярус, коды, маршруты, заглушки
  Контракт: C9–C13, C18
  Файлы: courses/rung_theory/{__init__,types,testing,needs,section_rules,api}.py, courses/rung_theory/AGENTS.md, courses/rung_theory/README.md, docs/engineering/module-tiers.json, courses/access_registry/pipeline_path.py, config/response-codes.json, config/api-problems.json, courses/urls.py, courses/topic_content/urls.py, courses/topic_content/rung_views.py, courses/lesson/mode_a/theory_read.py, реестр доступа (строки ручек), courses/tests/acceptance/rung_theory/pending.py, courses/rung_theory/tests/test_content_rung_contracts.py
  Зависит от: —
  Приёмка: AC-9 (часть `check-codes.py`)
  Готово-когда: test_routes_resolve_to_stubs, test_codes_registered, test_stub_views_501_and_path_decorator_present зелёные; `check_module_boundaries.py`, `gen_module_map.py --check`, `check-codes.py`, `check_module_readme.py`, `check_module_coverage.py` зелёные
  Риск: обычный · Размер: M (15)
  Тест-группа: content
  Внешний конфликт: шаг 6 правит `response-codes.json`, `api-problems.json`, `module-tiers.json`, реестр доступа. Только дописывание в конец своих разделов; пробное слияние со всеми ветками шага 6 в полёте

- [ ] K3 [K] Окно и вызовы в горячих файлах материала
  Контракт: C14, C15
  Файлы: courses/topic_content/rung_listeners.py, courses/topic_content/services.py (только вызовы окна), courses/topic_content/views.py (только `theory_mode` и декоратор пути на семи ручках), courses/topic_content/generation/services.py (только переход), courses/topic_content/generation/rung_theory_units.py (заглушка), courses/topic_content/generation/rung_theory_merge.py (заглушка), courses/course_pipeline/rung_reopen.py (заглушка), courses/apps.py (регистрация в `ready()`), courses/tests/test_handler_registration.py, courses/topic_content/tests/test_content_rung_hooks.py
  Зависит от: K2 (стек)
  Почему не одна: K2 и K3 вместе — около 30 файлов при одном риске на всё; разрез по риску отделяет механику (K2, обычный) от горячих файлов (K3, deep). K3 регистрирует обработчики из пакета K2 и без пакета не соберётся. Стек от сданного K2 стоит ~15 мин на пути вместо 23 при ребре по вливанию. Отказ K2 по смыслу шва останавливает K3 одним сообщением
  Приёмка: AC-15 (часть `theory_mode` → 422)
  Готово-когда: test_theory_mode_refused_off_flag, test_listeners_registered_web_and_celery, test_hooks_noop_on_legacy, test_unregistered_listener_fails_loud, test_topic_endpoints_carry_path_decorator зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content

### Фаза `[T]` (стек от сданного K2, вливание — после K1, K2, K3)

Каждая `[T]` пишет тесты в `courses/tests/acceptance/rung_theory/<имя по §2.3>.py` по спеке и
`contracts.md`. Каждый тест помечен `@ac_pending("AC-n")`. Импорт кода К и срезов — только внутри
тела теста.

**Помощник `ac_pending` (C18) отвечает на замечание 8.** Сам по себе `expectedFailure` засчитывает
`ImportError` как ожидаемую неудачу, поэтому до вливания К тест «ничего не держит» неотличим от
осмысленного. `ac_pending` различает причины:
- ожидаемая неудача засчитывается только для `AssertionError`, `NotImplementedError` (заглушки К)
  и ответа 501 заглушечной ручки;
- `ImportError`, `AttributeError`, `FieldError`, `TypeError` — ошибка, если не выставлена
  `ACCEPTANCE_PRE_K=1`; так `[T]` прогоняет себя на своей ветке до вливания К;
- неожиданный успех — ошибка.

Вливание `[T]` идёт после K1–K3 и без `ACCEPTANCE_PRE_K`. Скрипт при вливании прогоняет модуль
`[T]` строго: тест, который падает на импорте или на имени поля, краснеет и уходит в
`доработка` без ревьюера. Линза ревью `[T]` ловит смысл («каждый AC покрыт, тест бьёт обе
стороны»). Механику ловит строгий прогон при вливании, и ревьюер её не проверяет.

| T | Истории | AC | Размер | Группа |
|---|---|---|---|---|
| TAC | A (состав, «Контент»), C2 (материал ступени, сервер) | AC-1 (пример Пр §2), AC-2 (через R-25), AC-14, AC-16, AC-18 (серверная цепочка) | M (15) | content |
| TB | B (генерация и деньги) | AC-3, AC-6 (побайтность, одновременная правка двумя потоками), AC-8 (ноль вызовов без нажатия, резерв ≥ факт для трёх режимов, отказ учёта), AC-19 | **M (15)** | content |
| TC1 | C1 (материал без темы) | AC-4, AC-13, AC-15, AC-17 (пять ролей на каждой ручке) | M (15) | platform |
| TDE | D (перенос), E (гейты) | AC-5, AC-13 (дозаполнение), AC-9, AC-20, AC-21 | M (15) | content, saga (два файла) |
| TFG | F (структура), G (уроки и трек) | AC-10, AC-11 (ручки), AC-12 | M (15) | lessons |

AC-7 (вживую на `cp-*`) и Playwright из AC-11, AC-18, AC-22 делает `acceptance` по истории.

### Веер `[V]` (backend — от влитых K1–K3; V3, V6, V22 — с минуты 0)

История A — состав и «Контент»
- [ ] V1 [V] Состав теории ступени и пакетный загрузчик
  Срез: R-5–R-7, R-9–R-12a · Контракт: C10, C11
  Файлы: courses/rung_theory/needs.py, courses/rung_theory/loader.py, courses/rung_theory/tests/test_content_needs.py, courses/rung_theory/tests/test_content_needs_loader.py
  Зависит от: K1, K2, K3 · Приёмка: AC-1, AC-2 — TAC
  Готово-когда: test_progression_example_pr2, test_entry_point_skill_excluded, test_role_override_changes_need, test_each_knowledge_in_one_rung, test_states_order, test_lag_only_in_ready, test_loader_constant_queries зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content
- [ ] V2 [V] Ручка `GET /courses/{c}/rung-theory` (сервер)
  Срез: R-25 · Контракт: C11, C13
  Файлы: courses/rung_theory/api.py, courses/rung_theory/tests/test_content_rung_theory_api.py, docs/api/endpoints/course-rung-theory.md
  Зависит от: K1, K2, K3 · Приёмка: AC-2, AC-17 — TAC, TC1
  Готово-когда: test_rung_theory_payload_shape, test_rung_theory_access_5_roles, test_rung_theory_no_llm_calls зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: content
- [ ] V3 [V] Вкладка «Контент» по ступеням (клиент)
  Срез: R-26, R-12 · Контракт: C17, C15 (`theory_mode`)
  Файлы: …/content/rung/RungContentTab.tsx, …/content/rung/RungTheoryBlock.tsx, …/content/rung/types.ts, services/frontend/utils/rungTheory.ts, …/tabs/ContentTab.tsx (ветка по флагу), __tests__/components/rungContentTab.test.tsx
  Зависит от: — (по `contracts.md`) · Приёмка: AC-22 (юнит; Playwright — acceptance) — TAC
  Готово-когда: rungContentTab.test (шесть состояний с кнопками; после генерации перечитывает; «Редактировать» открывает `ContentEditorDrawer` прежними пропсами) зелёный; `tsc`, `/frontend-style` пройдены
  Риск: обычный · Размер: M (15) · Тест-группа: content

История B — генерация и деньги
- [ ] V4 [V] `generate`: основной носитель, снимок, пять шагов, план расхода
  Срез: R-13 `generate`, R-8, R-14, шаг 4 R-15 на стороне django · Контракт: C8, C14, C15, C16
  Файлы: courses/topic_content/generation/rung_theory_units.py, courses/topic_content/generation/rung_theory_payload.py (тип ответа C16, Lexical шага 4), courses/topic_content/generation/units.py, courses/topic_content/generation/tests/test_rung_theory_generate.py
  Зависит от: K1, K2, K3 · Приёмка: AC-3, AC-8 — TB
  Готово-когда: test_generate_creates_primary_carrier_with_snapshot, test_empty_composition_map_only, test_step4_question_rule_two_lexical_nodes, test_reserve_ge_actual, test_billing_refusal_leaves_carrier зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content
- [ ] V5 [V] `complete` и `map`: слияние под замком, подстраховка автопути
  Срез: R-13 `complete`/`map`/«нечего делать», R-14 · Контракт: C8, C14, C15
  Файлы: courses/topic_content/generation/rung_theory_merge.py, courses/course_pipeline/auto_pipeline.py, courses/topic_content/generation/tests/test_rung_theory_merge.py, courses/course_pipeline/tests/test_auto_pipeline_rung_theory.py
  Зависит от: K1, K2, K3 · Приёмка: AC-6, AC-19, AC-8 — TB
  Готово-когда: test_complete_copies_serving_sections_bytewise, test_complete_merges_author_edit_during_generation, test_map_adds_only_map, test_nothing_to_do_200_without_rung, test_backstop_generate_and_map_never_complete зелёные
  Риск: deep · Размер: M (24) · Тест-группа: content, saga
  Внешний конфликт: `auto_pipeline.py` — шаг 6
- [ ] V6 [V] Промпт и схема теории ступени в ml-llm
  Срез: R-15 · Контракт: C16
  Файлы: services/ml-llm/…/prompts/plan_system_rung_theory.md, …/text_system_rung_theory.md, services/ml-llm/…/rung_theory.py, services/ml-llm/…/schemas/rung_theory.json, services/ml-llm/tests/test_rung_theory_prompt.py
  Зависит от: — (по `contracts.md`) · Приёмка: AC-7 — acceptance вживую; сверка схемы — TB
  Готово-когда: test_rung_theory_schema_matches_contract, test_five_steps_in_plan_prompt, test_refs_passed_as_context зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: ml-llm

История C1 — материал без темы
- [ ] V7 [V] Доступ к материалу без темы и отказы по пути
  Срез: R-29, R-31, R-34 · Контракт: C3, C12, C13
  Файлы: courses/access_registry/preflight.py, courses/access_registry/pipeline_path.py (тело), courses/topic_content/views.py (только строки доступа 270/1035/1149/1206), courses/access_registry/tests/test_preflight_rung_material.py, courses/access_registry/tests/test_access_path_refusals.py
  Зависит от: K1, K2, K3 · Приёмка: AC-17, AC-13, AC-15 — TC1
  Готово-когда: test_preflight_course_from_material_field, test_author_2xx_stranger_403_anon_401_without_topic, test_legacy_material_same_course, test_response_topic_id_null_not_string, test_topic_endpoints_422_topic_material_on_flag (7 ручек), test_rung_endpoints_422_rung_material_off_flag (5 ручек), test_off_flag_unchanged зелёные
  Риск: deep · Размер: M (24) · Тест-группа: platform
- [ ] V12a [V] Вставные вопросы и IE-9/IE-10 без темы
  Срез: R-28 · Контракт: C3
  Файлы: courses/topic_content/models.py (только IE-9/IE-10, после K1), courses/topic_content/embedded_items/services.py, courses/topic_content/embedded_items/tests/test_rung_carrier.py
  Зависит от: K1, K2, K3 · Приёмка: AC-4 — TC1
  Готово-когда: test_ie9_no_attribute_error_without_topic, test_ie10_foreign_knowledge_refused_on_rung_carrier, test_embedded_knowledge_from_rung зелёные; список grep из §10 п. 3 спеки в отчёте
  Риск: обычный · Размер: M (15) · Тест-группа: banks
- [ ] V12b [V] Читатели курса материала: покрытие, редактор графа, факты гейта
  Срез: R-28 · Файлы: courses/topic_content/coverage/{check,gate}.py, courses/course_graph_editor/read.py, courses/course_pipeline/gates/facts.py, courses/task_classes/gate_rules.py, courses/topic_content/coverage/tests/test_coverage_without_topic.py
  Зависит от: K1, K2, K3 · Приёмка: AC-4 — TC1
  Готово-когда: test_coverage_check_course_from_material, test_graph_editor_keys_not_none_bucket, test_facts_without_topic зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: content

История C2 — материал ступени
- [ ] V9a [V] Ручки материала ступени: добавить, версии, переключить, носитель
  Срез: R-30 (4 из 5), R-32 (создание) · Контракт: C8, C12, C13
  Файлы: courses/topic_content/rung_views.py, courses/topic_content/rung_material.py, courses/topic_content/tests/test_rung_material_endpoints.py, docs/api/endpoints/{post-course-task-class-theory,get-course-topic-content-versions,post-course-topic-content-switch-current,patch-course-topic-content-carrier}.md
  Зависит от: K1, K2, K3 · Приёмка: AC-18, AC-17 — TAC, TC1
  Готово-когда: test_add_theory_creates_empty_draft_group, test_double_click_serialized, test_versions_by_group_no_topic, test_switch_current_by_group_calls_window, test_carrier_rename_place, test_access_5_roles зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V9b [V] Импорт документа в носитель ступени
  Срез: R-30 `populate-from-documents`, R-32 (импорт) · Контракт: C8
  Файлы: courses/topic_content/passthrough.py, courses/topic_content/tests/test_rung_populate.py, docs/api/endpoints/post-course-topic-content-populate-from-documents.md
  Зависит от: K1, K2, K3 · Приёмка: AC-18 — TAC
  Готово-когда: test_populate_passthrough_into_carrier_topic_null, test_populate_llm_generate_group_from_carrier зелёные; запись — только через `rung_writer`, `check_topic_content_writes.py` зелёный
  Риск: обычный · Размер: S (10) · Тест-группа: content
- [ ] V10 [V] Правила разделов: карта, знания раздела
  Срез: R-4, R-32 · Контракт: C4, C14
  Файлы: courses/rung_theory/section_rules.py, courses/topic_content/serializers.py, courses/rung_theory/tests/test_section_rules.py
  Зависит от: K1, K2, K3 · Приёмка: AC-16 — TAC
  Готово-когда: test_second_map_already_taken, test_map_on_backing_not_applicable, test_section_knowledge_ids_validated_not_knowledge, test_map_payload_is_block_array зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V11 [V] Форк, пересборка и читатели в `topic_content/services.py`
  Срез: R-32 (форк, пересборка), R-28 (`services.py:606/835/879/1416/1497/1637`) · Контракт: C3, C4, C14
  Файлы: courses/topic_content/services.py, courses/topic_content/tests/test_fork_rebuild_rung.py
  Зависит от: K1, K2, K3 · Приёмка: AC-16, AC-4 — TAC, TC1
  Готово-когда: test_fork_keeps_knowledge_ids_both_paths, test_rebuild_keeps_map_and_uses_course_discipline, test_confirm_without_topic_no_doesnotexist, test_reject_and_delete_by_id_pass_course_and_replaced_version зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V22 [V] Редактор материала без темы
  Срез: R-33, текст `force` пересборки R-32 · Контракт: C17
  Файлы: …/content/ContentEditorDrawer.tsx (ветка по флагу внутри), …/content/SectionsList.tsx, …/content/SectionsRail.tsx, …/content/SectionKnowledgePicker.tsx, services/frontend/utils/rungMaterial.ts, __tests__/components/contentEditorRung.test.tsx
  Зависит от: — (по `contracts.md`) · Приёмка: AC-16 (фронт), AC-18 (Playwright — acceptance) — TAC
  Готово-когда: contentEditorRung.test (выбор знаний: сверху C(R), поиск; OCC `expected_updated_at`; «Карта подхода»; шаги нумерованы; версии через R-30) зелёный
  Риск: deep · Размер: M (24) · Тест-группа: content

История D — перенос
- [ ] V20 [V] Перенос «Теорий» на ступени, удаление оболочек, дозаполнение `course`, отчёт, раннбук
  Срез: R-21 пп. 1–9 · Контракт: C1–C8
  Файлы: courses/topic_content/rung_theory_migration.py, courses/rung_theory/transfer.py, courses/rung_theory/course_fill.py, courses/rung_theory/report.py, courses/management/commands/migrate_rung_theory.py, courses/rung_theory/tests/test_content_transfer.py, courses/rung_theory/tests/test_content_course_fill.py, docs/meta/process/rung-theory-migration-runbook.md
  Зависит от: K1, K2, K3 · Приёмка: AC-5, AC-13 — TDE
  Готово-когда: test_dry_run_writes_nothing, test_apply_moves_versions_sections_bytewise, test_shells_deleted_with_snapshot_logged, test_second_apply_zero_changes, test_course_with_student_refused, test_no_llm_no_ledger, test_course_fill_only_null_rows, test_report_from_journal, test_journal_dump_count_matches зелёные. Откат схемы проверяет K1 (C6), здесь его нет
  Риск: deep · Размер: M (24; если дифф больше ~300 строк — `course_fill` и `report` выносятся отдельной задачей, `Почему не срез:` не нужен) · Тест-группа: content
  Примечание: оболочки удаляет вызовом писателя `course_structure/deletion.py`, сам файл не правит (его правит V17b)

История E — гейты
- [ ] V19a [V] Четыре правила гейта 2 на флаге
  Срез: R-22 · Контракт: C11, C12
  Файлы: courses/course_pipeline/gates/rules_rung_theory.py, courses/course_pipeline/gates/registry.py (привязка четырёх правил), courses/course_pipeline/tests/test_rules_rung_theory.py
  Зависит от: K1, K2, K3 · Приёмка: AC-9 — TDE
  Готово-когда: test_knowledge_missing_blocker_by_C0, test_deleted_section_blocks_despite_snapshot, test_unmarked_section_warning_except_intro_and_map, test_outdated_warning_not_blocking_moderation, test_map_missing_blocker зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: saga
  Внешний конфликт: `registry.py` — шаг 6
- [ ] V19b [V] Снятие правил «Теории» на флаге, `ksa-task-class-inadequate`
  Срез: R-23 «снимаются», AC-21
  Файлы: courses/graph_invariants/structure_gate.py, courses/course_pipeline/gates/rules_content.py, courses/course_pipeline/gates/rules_topic_content.py, **courses/course_pipeline/gates/rules_structure.py** (`_ksa_task_class_inadequate_check`, строки 662–772), courses/task_classes/readiness.py, courses/task_classes/predicates.py, courses/course_pipeline/tests/test_reading_rules_off_on_flag.py
  Зависит от: K1, K2, K3 · Приёмка: AC-9 (снятые правила), AC-21 — TDE
  Готово-когда: test_reading_rules_silent_on_flag_fire_off_flag, test_a_lines_missing_reading_not_applied_on_flag, test_ksa_inadequate_silent_for_S_or_jit зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: saga
  Внешний конфликт: **сильный.** Шаг 6 правит `structure_gate.py`, `rules_structure.py`, правила гейтов. Брать, когда задача шага 6 на этих файлах не в полёте
- [ ] V19c [V] Откат гейта 2 по условию блокера
  Срез: R-23 «откат» · Контракт: C11, C14
  Файлы: courses/course_pipeline/rung_reopen.py, courses/saga/gate_backing.py, courses/saga/reopen.py, courses/course_pipeline/gating.py, courses/saga/tests/test_reopen_rung_theory.py
  Зависит от: K1, K2, K3 · Приёмка: AC-20 — TDE
  Готово-когда: test_complete_approval_no_reopen, test_other_rung_edit_no_reopen, test_delete_or_reject_covering_version_reopens, test_approved_fork_without_section_reopens, test_backing_lost_predicate_false_on_flag, test_off_flag_unchanged зелёные
  Риск: deep · Размер: M (24) · Тест-группа: saga
  Внешний конфликт: `saga/` — шаг 6

История F — структура и окно ступени
- [ ] V17a [V] Нет «Теории» как класса на флаге: сервер и окно
  Срез: R-1, R-27 · Контракт: C12
  Файлы: courses/task_classes/services.py (`kind`), courses/task_classes/rung_layout.py, courses/structure_gen/skeleton.py, …/structure/TaskClassModal.tsx, …/structure/TopicTreePanel.tsx, courses/task_classes/tests/test_no_reading_kind_on_flag.py, __tests__/components/taskClassModalNoKind.test.tsx
  Зависит от: K1, K2, K3 · Приёмка: AC-11 — TFG
  Готово-когда: test_kind_content_reading_422_not_applicable, test_skeleton_no_reading_on_flag, taskClassModalNoKind.test зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: banks
  Внешний конфликт: **сильный** (`TaskClassModal.tsx`, `task_classes/services.py` у шага 6). Брать после вливания задачи шага 6 на этих файлах
- [ ] V17b [V] Перегенерация и удаление ступени с теорией
  Срез: R-16, R-17, R-17a, R-28 (`rung_layout_db.py:1137`, `parent_deletion.py:130`)
  Файлы: courses/task_classes/rung_regen.py, courses/task_classes/rung_layout_db.py, courses/course_structure/deletion.py, courses/topic_content/parent_deletion.py, …/structure/<окно удаления ступени>.tsx (одна строка текста), courses/task_classes/tests/test_regen_delete_rung_theory.py
  Зависит от: K1, K2, K3 · Приёмка: AC-10 — TFG
  Готово-когда: test_kept_key_keeps_theory, test_gone_rung_with_theory_parked, test_no_reading_match_on_flag, test_delete_rung_with_approved_theory_parks, test_unapproved_theory_deleted_with_rung зелёные; `check_course_structure_writes.py` зелёный
  Риск: deep · Размер: M (24) · Тест-группа: **banks** (в круге 1 ошибочно `structure`)
  Внешний конфликт: `course_structure/` — шаг 6

История G — уроки и трек
- [ ] V13 [V] Теория нужных ступеней для урока Б, контекста генерации задач и банка диагностики
  Срез: R-20, R-28 (контекст, банк) · Контракт: C3, C4
  Файлы: courses/topic_content/rung_sections.py, courses/dialogue/material_b.py, courses/topic_content/generation/context.py, courses/topic_content/generation/dispatch.py, courses/diagnostic_bank/payload.py, courses/dialogue/tests/test_material_b_rung_theory.py, courses/topic_content/generation/tests/test_context_rung_theory.py, courses/diagnostic_bank/tests/test_payload_rung_material.py
  Зависит от: K1, K2, K3 · Приёмка: AC-12 (урок Б), AC-4 (контекст) — TFG, TC1
  Готово-когда: test_source2_sections_by_task_knowledge, test_map_always_included, test_backing_source_unchanged, test_supportive_sections_from_rung_theory, test_diagnostic_payload_course_from_material, test_dispatch_without_topic_order зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: lessons, content, banks
  Внешний конфликт: шаг 6 переводит `dialogue/` на читателя задач курса — пробное слияние
- [ ] V14 [V] Урок А по ступени и «Опирается на»
  Срез: R-18, R-19 · Контракт: C11, C13, C17
  Файлы: courses/lesson/mode_a/services.py, courses/lesson/mode_a/theory_read.py, courses/topic_content/lesson_modes.py, courses/lesson/serializers.py, services/frontend/utils/lessons.ts, …/mode-a/LessonModeA.tsx, …/mode-a/LessonDependsOn.tsx, courses/lesson/mode_a/tests/test_mode_a_rung.py, __tests__/components/lessonDependsOn.test.tsx
  Зависит от: K1, K2, K3 · Приёмка: AC-12 (урок А) — TFG
  Готово-когда: test_lesson_a_by_rung_no_fallbacks_on_flag, test_refs_block, test_student_read_theory_without_credit, test_no_lesson_a_when_only_map, lessonDependsOn.test зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: lessons
  Внешний конфликт: шаг 6 снимает проверки режимов в `mode_a`
- [ ] V16 [V] Трек: урок А ступени перед практикой
  Срез: R-20a · Файлы: courses/track_manage/services.py, courses/track_manage/planner.py, courses/track_manage/tests/test_track_rung_theory.py
  Зависит от: K1, K2, K3 · Приёмка: AC-12 (трек) — TFG
  Готово-когда: test_lesson_a_before_practice_by_carrier, test_no_lesson_a_goes_to_practice, test_no_user_task_class_for_reading_on_flag зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: graph

### Хвост

- [ ] H1 [H] Реестры документов, свежесть README, хвосты ревью
  Файлы: docs/INDEX.md, docs/TAGS.md, CHANGELOG, журнал концепции, ADR-099 (D9 на флаге — О-6), статус спеки, docs/engineering/module-map.md (финальная пересборка), courses/rung_theory/README.md (сверка с фактом), дословные находки «можно сливать, хвост»
  Зависит от: все
  Готово-когда: `check.sh`, `gen_module_map.py --check`, `check-codes.py`, `check_doc_freshness`, проверки ссылок зелёные; каждая находка «хвост» закрыта или перенесена задачей
  Риск: обычный · Размер: M (15) · Тест-группа: governance

### Покрытие требований

R-1 V17a · R-2 K1 · R-3 K1 + писатели · R-4 V10 · R-5–R-7 V1 · R-8 V4/V5 · R-9–R-12a V1 + V3 ·
R-13 K3/V4/V5 · R-14 V4/V5 · R-15 V6 + V4 · R-16/R-17/R-17a V17b · R-18/R-19 V14 · R-20 V13 ·
R-20a V16 · R-21 V20 · R-22 V19a · R-23 V19b/V19c · R-24 K2 · R-25 V2 · R-26 V3 · R-27 V17a ·
R-28 K1 + V7 V11 V12a V12b V13 V14 V17b · R-29 V7 · R-30 K2 + V9a/V9b · R-31 K2/K3 + V7 ·
R-32 K1 + V4 V5 V9a V9b V10 V11 V20 + V22 · R-33 V22 · R-34 K2 + V7. AC-1…AC-22 — у каждого
есть `[T]` или `acceptance` (AC-7 и Playwright).

## 5. Расписание (N = 4, партии вливания c = 6, без шума и доработок, HLFET)

```
слот1: K2[0-15]  TAC[15-30] TDE[30-45] ·· V4[53-77]  V17b[77-101] V11[101-116] V17a[116-131] V12b[131-141]
слот2: V3[0-15]  K3[15-39]  TFG[39-54]    V5[54-78]  V9a[78-93]   V10[93-108]  V14[108-123]  V2[123-133]  H1[169-184]
слот3: K1[0-24]  TB[24-39]  V6[39-54]     V7[54-78]  V20[78-102]  V13[102-117] V19b[117-132] V16[132-142]
слот4: V22[0-24] TC1[24-39] ··········    V1[53-77]  V19c[77-101] V12a[101-116] V19a[116-131] V9b[131-141]
```

Без шума — 198 мин, занятость 2.78. С шумом и p = 0.43 занятость по получасам такая: 4.0 / 3.8 /
**2.8** / 3.7 / 4.0 / 3.8 / 2.6 / 1.0 / 0.5 / 0.2. Провалов два:
- **60–90 мин — ожидание вливания K3.** K3 сделан стеком от K2 и стоит на пути. Пока его
  ревьюют, остаются только `[T]` и три фронтовых или ml-llm задачи, а их меньше слотов. Это цена
  разреза K2/K3 по риску. Без разреза пустым было бы то же окно, только вокруг одной K2 deep ~32
  мин.
- **После 210 мин — хвост доработок и вливаний.** Он не лечится слотами, только снижением p и
  партиями.

При N = 2 расписание просто вдвое длиннее. Ширина плана (P = 7) остаётся недоиспользованной: в
каждый момент готовы 5–12 задач.

## 6. Конфликты и простой

1. **Текст внутри фичи.** Проба — 0 пересечений. Общие файлы передаются только по рёбрам
   К → V: `models.py` K1 → V12a, `services.py` K3 → V11, `views.py` K3 → V7, `rung_views.py`
   K2 → V9a, `needs.py` K2 → V1, `section_rules.py` K2 → V10, `pipeline_path.py` K2 → V7,
   `rung_reopen.py` K3 → V19c, `rung_theory_units.py` и `rung_theory_merge.py` K3 → V4/V5,
   `theory_read.py` K2 → V14, `api.py` K2 → V2. Названные пределы:
   - `docs/engineering/module-map.md` и `module-graph.json` генерируются и меняются у каждого
     среза с новым импортом. Класс `regen` в `pair-rules.txt`: при конфликте берётся главная
     ветка и запускается генератор, в партии — один раз на партию.
   - Новый код ошибки в срезе — поправка контракта в `response-codes.json`. Пробное слияние при
     сдаче ловит её → `доработка` без ревью.
   - `rung_theory/README.md` K2 пишет с полной поверхностью из `contracts.md`. Если срез
     добавил публичное имя вне контракта, это поправка контракта, а не правка README; сверку
     делает H1.
2. **Миграции** — только K1, ресурс `serial: migrations`, общий с шагом 6.
3. **Шаг 6 одновременно.** Сильные пересечения: V17a, V19b (`rules_structure.py`,
   `structure_gate.py`), K2 (коды, ярусы, реестр доступа). Средние: V19a (`registry.py`), V19c,
   V5, V17b, V14, V13, H1, а также `apps.py` у K3, если шаг 6 регистрирует свои окна. Правило:
   **один `next` на объединённый граф двух фич и общая карта владения.** HLFET по объединению
   отдаёт слоты задачам с большим рангом, кто бы их ни нёс. Именно поэтому основной сценарий —
   N ≈ 2 (§0).
4. **Тесты и CI.** Исключений в `test-registry.json` нет, сам файл не правится (§2.3). Отпечаток
   CI грубый: правка `services/` сбрасывает все группы django. Партии собираются по времени.
   `cicd.yml`: `concurrency` с `cancel-in-progress: true` — пуш, пока идёт прогон, отменяет его.
   Пушит один координатор, одной партией.
5. **Очередь вливаний (новое).** 32 вливания по 6 мин — это 192 мин работы координатора на веер
   длиной ~280 мин. Вливание по одному держит его занятым на 66–73 %, и ветка ждёт 17–24 мин.
   Решение (§7, правило 1) — **вливание партиями**: координатор берёт до 4 готовых веток, делает
   rebase всех на вершину, один прогон узкой проверки по объединению `Тест-группа:`, затем
   `--ff-only` по очереди. Красная партия делится пополам. Механика уже есть: пробное слияние
   со всеми ветками в полёте при сдаче (`design.md` §3, шаг 9) заранее снимает текстовые
   конфликты, поэтому в партии остаётся только проверка. Это «Refinery» Gas Town и merge queue
   GitHub из `research.md`.
6. **Стенды.** Playwright и `/lesson-qa` — у `acceptance` по истории, внахлёст с веером. На пути
   только приёмка последней истории, 20–40 мин.
7. **Документы.** Документы ручек пишут V2, V9a, V9b; раннбук — V20; README и паспорт пакета —
   K2; строку о писателе в паспорте `topic_content` — K1; реестры — только H1.

## 7. Ревью, доработки, вливания

- Сдача освобождает слот. Перед ревью скрипт делает пробное слияние со всеми ветками обеих фич
  в полёте и проверяет `hold` и `check.sh`. Для `[T]` вместо `hold` идёт строгий прогон
  `ac_pending` (только после вливания К).
- Ревью — пул R ≥ K − 1 (при N = 2 — R = 1–2; R = 2 даёт −9 %: 450 против 495). Одна линза на
  вид задачи: `[K]` — «хватит ли срезам»; `[T]` — «каждый AC покрыт, тест бьёт обе стороны»;
  `[V]` — логика, `Контракт:`, `Готово-когда:`.
- «Можно сливать, хвост» уходит в H1. Доработку берёт любой свободный исполнитель. Предел — два
  круга.
- **Правило 1 (новое): вливание партиями до 4**, c + 2·(n − 1). Без него пятый слот бесполезен
  (−3 %), а при общем координаторе N = 4 даёт 469 мин вместо 306.
- **Правило 2 (новое): слоты делятся между фичами одним `next`.** Прогноз и пятый слот считаются
  от фактической доли шага 8 в пуле, а не от лимита сессии.

## 8. Что проверить после реализации

- Сколько вливаний пришлось на партию и сколько партий покраснело. Если доля красных больше
  25 %, партия 4 слишком велика — взять 2–3.
- Фактическое c: время координатора на одно вливание и на партию. Модель взяла 6 и 6 + 2(n − 1).
- Ловил ли строгий прогон `ac_pending` при вливании `[T]` тесты, падающие на импорте. Если ни
  разу за фичу, линзу `[T]` можно оставить без механики.
- Доля отказов «расхождение сторон» и «пересечение». Если после инварианта K1, окна K3 и общей
  карты с шагом 6 она больше 15 % отказов, правило «один `next` на обе фичи» на деле не работает.
- Выдержали ли K2 и K3 размер M. Если K2 вышла втрое дольше, прогноз +12 % (§0).
- Стоял ли кто-то в окне 60–90 мин из-за ревью K3. Если да, в следующей фиче ревью K3 идёт
  первым в очереди ревью (ранг K3 уже наибольший после K2).

## 9. Открытые места для `architect`

- Адрес чтения теории учеником (R-19): предложен
  `GET /api/v1/courses/{c}/task-classes/{tc}/theory/read`. Без подтверждения шов C13 может
  поменять смысл после старта.
- Место `refuse_unless_path`: `access_registry` (ярус 1) выбран, потому что это предполётная
  проверка ручки, как доступ. Альтернатива — `course_structure` (ярус 2). Корень запрещён (П-9).
- Ярус 3 для `rung_theory` и порядок внутри яруса (`topic_content`, `task_classes` <
  `rung_theory` < `course_pipeline`, `lesson`, `dialogue`) надо записать в П-9
  `module-rules.md` вместе с картой — это делает K2.
- Окно удаления ступени (V17b) — имя файла на фронте не найдено; это каталог `structure/`, общий
  с шагом 6.
