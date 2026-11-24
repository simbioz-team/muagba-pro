# Фича 2 (шаг 8, теория ступени): разложение и план, команда B, круг 1

Дата 2026-11-24. Процесс — `design.md` (К → `[T]` в окне К → веер `[V]` → `[H]`).
Вход — `feature-2-description.md`, санированная спека `inputs/feature-2/step8-spec-sanitized.md`,
код и документы на базовом коммите `053602900`. Расчёт: `f2B/plan.py` (проба P = W/S, HLFET,
событийная модель: ревью 8 мин, вливание 2 мин одной очередью, доработка 0.7 веса, второй
круг с вероятностью p/2, предел два круга, разброс 0.7–1.4, 300 прогонов).

**Честная пометка.** Когда я искал скрипт групп CI, `git show 053602900:<путь>` вывел
сам базовый коммит, а в его диффе `docs/TAGS.md` есть строка-сводка спеки шага 8 с фразой
«Нарезка — 22 задачи в двенадцать уровней, четыре — implementer-deep». Это базовый коммит,
читать его разрешено, но фраза описывает бейзлайн. Видел я только эти числа. Ни задач, ни
графа бейзлайна я не открывал. Разложение ниже построено из требований R и критериев AC
спеки, а 38 задач и 9 deep получились по своим правилам.

## 0. Итог в цифрах

| Мера | Значение |
|---|---|
| Задач | 38: 3 `[K]`, 8 `[T]`, 26 `[V]`, 1 `[H]`. Из них deep — 9 |
| W (сумма весов) | 563 мин |
| S (критический путь) | 63 мин: `K1 → V1 (или любой deep M среза) → H1` |
| Параллельность P = W/S | **8.9**: при K = 3 и K = 4 это ≥ 2K (норма), при K = 5 — предупреждение (нужно 10) |
| Фаза К | 49 мин = 9 % W, глубина 1 |
| Пересечения `Файлы:` без пути между задачами | 0 (проба `plan.py`), с оговорками §5 |
| Модель, N = 4, R = 3 | p = 0.43: **266 мин** (p90 293); p = 0.30: 242; p = 0.15: 216 |
| Модель, N = 5, R = 4 | p = 0.43: 234 мин; p = 0.30: 210; p = 0.15: 186 |
| Без шума и доработок, N = 4 | 178 мин; N = 5 — 151 мин |
| Занятость слотов | вся фича — 3.0–3.1 из 4 (3.5 из 5); середина веера — 3.6–4.0 из 4 |
| Срок до приёмки | ≈ 4.4 ч веера + 15–28 мин последней CI + 20–40 мин приёмки последней истории ≈ **5–5.5 ч** при p = 0.43; ≈ 4.3–4.7 ч при p = 0.15 |
| Запусков исполнителя / ревью | ≈ 58 / 58 при p = 0.43; ≈ 44 / 44 при p = 0.15 |

Чувствительность к пулу ревью (N = 4, p = 0.43): R = 2 → 298 мин, R = 3 → 266, R = 4 → 260.
R = K − 1 достаточно.

## 1. Как получена ширина: три решения планирования

Ширина держится на трёх решениях. Тесты и ревью стоят отдельно (§6).

1. **Хуки в фазе К вместо общих гигантов.** `topic_content/services.py` (2 703 строки),
   `views.py` (1 503), `generation/services.py` (1 221), `utils/auth.ts` (5 259) правят
   по смыслу 8–10 требований. Если каждый срез правит их сам, получаются цепочки по файлу:
   `V11 → V10 → V9a → V19c`, `V7 → V8 → V2`, `V4 → V5`, `V19a → V19b`. Мой
   контрфакт в `plan.py`: S = 108, P = 5.2 (красное при K = 4), время +4.5 % (278 против
   266). Это ещё до текстовых конфликтов, которые в жизни были бы на месте рёбер. Поэтому
   K2 ставит в эти файлы одну строку вызова на каждое место и выносит тело в **новый
   файл**, который принадлежит одному срезу. Срез правит только свой файл. Вес хуков в
   K2 — ~5 мин.
2. **Инвариант в модели вместо дисциплины писателей.** R-32 требует, чтобы *шесть* писателей
   (создание, форк, импорт, генерация, слияние `complete`/`map`, перенос) на флаге писали
   `topic = NULL`. В K1 `clean()`/`save()` отказывает носителю ступени флагового курса с
   `topic ≠ NULL`, а `course` всегда ставит сама. Забывчивый писатель краснеет в тестах
   своего же среза, а не на ревью или приёмке. Это бьёт по причине отказа «расхождение
   сторон (запись/чтение)» — одной из главных в доле 42–44 %.
3. **Подмена состава для потребителей.** Состав теории (`needs.py`, R-5) читают девять
   срезов. K2 даёт типы `CourseTheory`/`RungTheory` и помощник
   `rung_theory/testing.py::patch_course_theory(...)`. Юнит-тесты потребителей не ждут
   V1, связку держат `[T]` истории на настоящем составе. Ребро V1 → потребители не нужно.

## 2. Карта швов (`contracts.md`)

`C<n> | что | владелец | потребители`. Все миграции, сущности, реестры и заглушки — в К.

| C | Шов | Владелец | Потребители |
|---|---|---|---|
| C1 | `TopicContent.carrier_purpose` (`theory` \| NULL) и инварианты R-2: `theory` только на `whole_task` флагового курса; ≤ 1 группа подложки на ступень (`already-taken`); группа не меняет назначения | K1 | V4 V5 V9a V9b V10 V11 V12a–c V13 V14 V17b V19a–c V20b, все `[T]` |
| C2 | `TopicContent.topic` и `TopicContentGenerationError.topic` → `null=True`. На флаге у носителя ступени `topic ≠ NULL` — отказ `clean()`, без флага `topic = NULL` — отказ (AC-14) | K1 | все писатели (§1 п. 2) |
| C3 | `TopicContent.course` (FK PROTECT, `null=True`, `related_name="course_materials"`); `save()` ставит его от темы или от `task_class.topic.course`; миграция заполняет все строки | K1 | V7 (preflight через `Course.objects.filter(course_materials__pk=…)`), V11 V12a–c V19c V20a |
| C4 | `section_type = 'approach_map'` (только `choices`); `TopicContentSection.understanding_step` 1…5 \| NULL | K1 | V4 V5 V10 V11 V13 V14 V19a V22 |
| C5 | Модель `RungTheoryMigrationRecord` (запуск, курс, действие, объект, прежние значения, снимок) и менеджер `record(...)` | K1 | V20a V20b |
| C6 | Миграции `0307_rung_theory_schema` (поля C1–C4; заполнение `course`; обратный ход заполняет `topic` темой ступени и падает списком id без ступени) и `0308_rung_theory_migration_record`. Номера — следующие свободные на момент вливания K1 (шаг 6 идёт одновременно) | K1 | V20b (тест обратной миграции) |
| C7 | Сборщик фикстур `rung_theory/tests/fixtures.py::flag_course_with_ladder(lines, rungs, ksa_graph, tasks, carriers)` и `legacy_course_with_reading(...)` | K1 | все backend `[V]` и `[T]` |
| C8 | `rung_theory/types.py`: `TheoryState` (`no_new_theory`/`theory_missing`/`theory_pending`/`ready`), `RungTheory` (S₀, S, C₀, C, Ref, Cov, state, lag, lag_from_tasks, extra, map_missing), `CourseTheory` (rungs по порядку курса, U), `TheoryBlock` (knowledge_ids, understanding_step, section_type, payload) | K2 | все |
| C9 | `rung_theory/needs.py`: `course_theory(course) -> CourseTheory`, `serving_version(group)`, `primary_carrier(rung)` (сигнатуры, докстринги; тело — `NotImplementedError`) + `testing.patch_course_theory` | K2 → тело V1 | V2 V4 V5 V12a V13 V14 V16 V19a V19c |
| C10 | `rung_theory/sections.py::sections_for_knowledge(course, knowledge_ids)` (заглушка) | K2 → тело V13 | V12c |
| C11 | `rung_theory/writer.py::write_theory_blocks(version, blocks, *, start_index)` — минимальный настоящий: текст, `knowledge_ids`, `understanding_step`, `section_type` | K2 → V4 дописывает шаг 4 (`question`/`rule` → два элемента Lexical) | V5 |
| C12 | Хуки в `topic_content/services.py`: `section_rules.validate_section(data, carrier)` в `create/update_topic_content_section` (заглушка пропускает); сохранение `knowledge_ids` раздела, если оно передано; `rung_theory.reopen.on_serving_change(course, replaced_version_id)` после утверждения, переключения, отклонения и удаления версии (заглушка ничего не делает) | K2 | V10 (тело validate), V19c (тело reopen), V11 (владеет services.py дальше) |
| C13 | Коды: `/problems/course-path-not-applicable` (варианты `rung-material`, `topic-material`, `added_by: T-2268`); `rung-theory-knowledge-missing`, `rung-theory-section-unmarked`, `rung-theory-outdated`, `rung-approach-map-missing`; выведение `reading-material-outdated` (R-24); строки `api-problems.json` для R-25, R-30 ×5 и чтения теории учеником | K2 | V2 V8 V9a V9b V14 V19a |
| C14 | `courses/pipeline_path.py::refuse_unless_path(v2: bool, variant)` — декоратор стоит на всех ручках R-30 и R-31, тело — заглушка «пропустить» | K2 → тело V8 | V9a V9b |
| C15 | Маршруты: R-30 (5 ручек) → `topic_content/rung_views.py` (заглушки 501); R-25 → `rung_theory/api.py` (заглушка); чтение теории учеником R-19 `GET /api/v1/courses/{c}/task-classes/{tc}/theory/read` → `lesson/mode_a/theory_read.py` (заглушка); строки реестра доступа | K2 | V2 V9a V9b V14 |
| C16 | `regenerate-content`: поле `theory_mode` (`generate`/`complete`/`map`), на старом пути — 422 `not-applicable`; переход в `generation/services.py` на `rung_theory_units.plan_generate` (заглушка) и `rung_theory_merge.plan_complete/plan_map` (заглушки) | K2 | V4 V5 |
| C17 | Контракт ml-llm `kind=rung_theory`: запрос (C, Ref, карта предшественника, цели ступени) и ответ (блоки с `knowledge_ids`, `understanding_step`, у шага 4 поля `question` и `rule`, блок `approach_map` абзацами) — JSON-схема в ml-llm и тип на стороне django | K2 | V4 V6 |
| C18 | CLI `migrate_rung_theory [--dry-run (умолч.) \| --apply] [--course] [--backfill-course]`: разбор и отчёт идут в `rung_theory/backfill.py` и `rung_theory/transfer.py` (заглушки) | K2 | V20a V20b |
| C19 | Реестр тестов: исключение `rung_theory → content` (иначе новые тесты уйдут в `core`, а потолок `core_ceiling = 2`); ярус `rung_theory` в `module-tiers.json` | K2 | все backend |
| C20 | Фронт: `content/rung/types.ts` (ответ R-25, состояния); обёртки `utils/auth.ts` для R-25, R-30 ×5, `theory_mode`, `knowledge_ids` раздела, чтения теории учеником; в `ContentTab.tsx` ветка по флагу монтирует `RungContentTab` (заглушка) | K3 | V3 V14 V17a V22 |

Ловушки имён групп, найденные при планировании: имя файла теста с `unit` попадает в группу
`billing` (`rung_theory_units` → `test_rung_theory_generate.py`), с `task_class` — в
`banks`. Поле `Тест-группа:` ниже названо по регулярным выражениям
`scripts/test_registry.py`.

## 3. Задачи

Общее для всех `[V]`: сдача — `check.sh` зелёный, сняты `@expectedFailure` своих `AC-n` в
приёмочных тестах истории, вывод `hold` (откат не-тестовых `Файлы:` к базе краснит тесты
`Готово-когда:`). Импорт из кода К в `[T]` — только внутри тела теста. Иначе модуль не
соберётся, и строгий xfail (`unittest.expectedFailure`, неожиданный успех краснит прогон)
не сработает. Вес: S = 10, M = 15, deep ×1.6.

### Фаза К (старт сразу, параллельно)

- [ ] K1 [K] Схема материала ступени, инварианты модели, журнал переноса, фикстуры
  Контракт: C1–C7
  Файлы: courses/topic_content/models.py (поля, `clean/save`, `__str__` без темы; IE-9/IE-10 не трогать — V12a), courses/migrations/0307_*.py, courses/migrations/0308_*.py, courses/rung_theory/models.py, courses/rung_theory/tests/fixtures.py, courses/rung_theory/tests/test_models.py
  Зависит от: —
  Приёмка: AC-14; AC-13 (столбцы старого пути NULL, `course = topic.course`)
  Готово-когда: test_carrier_purpose_invariants, test_course_filled_by_save_with_and_without_topic, test_topic_null_refused_off_flag, test_topic_set_refused_on_flag_rung_carrier, test_migration_fills_course, test_reverse_migration_restores_topic зелёные
  Риск: deep (миграция, инвариант всех писателей)
  Размер: M (24)
  Тест-группа: content
  Внешний конфликт: цепочка миграций шага 6 — ресурс `serial: migrations`, номер ставится при вливании

- [ ] K2 [K] Швы бэкенда: пакет `rung_theory`, хуки, коды, маршруты, переключатель пути
  Контракт: C8–C19
  Файлы: courses/rung_theory/{__init__,types,needs,sections,writer,testing,reopen,section_rules,api}.py (заглушки), courses/pipeline_path.py, courses/topic_content/services.py (только хуки C12), courses/topic_content/views.py (только `theory_mode`), courses/topic_content/urls.py, courses/urls.py, courses/topic_content/rung_views.py, courses/topic_content/generation/services.py (только переход C16), courses/topic_content/generation/{rung_theory_units,rung_theory_merge}.py, courses/lesson/mode_a/theory_read.py, courses/management/commands/migrate_rung_theory.py, courses/rung_theory/{backfill,transfer}.py, config/response-codes.json, config/api-problems.json, courses/course_pipeline/gates/registry.py (привязка 4 правил к заглушкам `rules_rung_theory.py`), реестр доступа (строки ручек), docs/engineering/test-registry.json, docs/engineering/module-tiers.json, services/ml-llm/…/schemas/rung_theory.json, courses/rung_theory/tests/test_contracts.py
  Зависит от: —
  Приёмка: AC-15 (часть `theory_mode` → 422), AC-9 (часть `check-codes.py`)
  Готово-когда: test_theory_mode_refused_off_flag, test_routes_resolve, test_codes_registered, test_hooks_noop_on_legacy зелёные; `check-codes.py` и `gen_module_map.py --check` зелёные
  Риск: обычный
  Размер: M (15; широкий, но механический — если по диффу выходит больше M, вынести реестры в K4 с `Почему не одна:`)
  Тест-группа: content, saga, codes
  Внешний конфликт: шаг 6 правит `response-codes.json`, `api-problems.json`, реестр гейтов, реестр тестов, карту ярусов. Дописывать только в конец своих разделов, пробное слияние со всеми ветками шага 6 в полёте

- [ ] K3 [K] Швы фронта
  Контракт: C20
  Файлы: services/frontend/utils/auth.ts, …/_components/content/rung/types.ts, …/_components/content/rung/RungContentTab.tsx (заглушка), …/_components/tabs/ContentTab.tsx (только ветка по флагу), services/frontend/__tests__/components/rungSeams.test.ts
  Зависит от: —
  Приёмка: —
  Готово-когда: rungSeams.test (обёртки зовут нужные адреса; флаг монтирует новую вкладку, без флага — прежнюю) зелёный; `tsc` зелёный
  Риск: обычный
  Размер: S (10)
  Тест-группа: frontend

### Приёмочные тесты `[T]` (в окне фазы К, ранг выше срезов)

Каждая `[T]` пишется по спеке и `contracts.md` в `courses/tests/acceptance/rung_theory/test_us_<x>.py`,
каждый тест помечен `@expectedFailure`, у каждого в докстринге — свой `AC-n`. Цель ревью
«каждый AC покрыт, тест бьёт обе стороны (запись и чтение / сервер и ответ)». Ни одна `[T]`
не зависит от кода К.

| T | История | AC | Размер | Группа |
|---|---|---|---|---|
| TA | Состав и «Контент» | AC-1 (пример Пр §2 на фикстуре графа), AC-2 (через ручку R-25) | S | content |
| TB | Генерация и деньги | AC-3, AC-6 (побайтность прежних разделов и одновременная правка), AC-8, AC-19 — с подменой ml-llm и учёта | S | content |
| TC1 | Материал без темы: доступ, читатели, отказы | AC-4, AC-13, AC-15, AC-17 (матрица пяти ролей на ручках по id материала) | M | platform |
| TC2 | Материал ступени: ручки, разделы, редактор (сервер) | AC-14, AC-16, AC-18 (серверная цепочка без Playwright) | S | content |
| TD | Перенос | AC-5, AC-13 (дозаполнение) | S | content |
| TE | Гейты | AC-9, AC-20, AC-21 | S | saga |
| TF | Структура и окно ступени | AC-10, AC-11 (ручки) | S | structure |
| TG | Уроки и трек | AC-12 | S | lessons |

AC-7 (качество вживую на `cp-*`) и Playwright 1200/375 из AC-11, AC-18, AC-22 — у `acceptance`
по истории (§6), не в `[T]`: стенд — общий ресурс, и в срезах его не занимаем.

### Веер `[V]` (старт от **влитого** К — срезов 26 ≥ 2K, стек от К запрещён)

История A — состав и «Контент»
- [ ] V1 [V] Состав теории ступени: `needs.py` и пакетный загрузчик
  Срез: R-5–R-7, состояния R-9–R-12a (Т-1…Т-11)
  Контракт: C8, C9
  Файлы: courses/rung_theory/needs.py, courses/rung_theory/loader.py, courses/rung_theory/tests/test_needs.py, courses/rung_theory/tests/test_loader_queries.py
  Зависит от: K1, K2
  Приёмка: AC-1, AC-2 (юнит) — TA
  Готово-когда: test_progression_example_pr2, test_entry_point_skill_excluded, test_role_override_changes_need, test_each_knowledge_in_one_rung, test_states_order, test_lag_only_in_ready, test_loader_constant_queries (`assertNumQueries` при 3 и 30 ступенях) зелёные
  Риск: deep (алгоритм, на нём держатся гейт и «Контент»)
  Размер: M (24)
  Тест-группа: content
- [ ] V2 [V] Ручка `GET /courses/{c}/rung-theory` (сторона сервера)
  Срез: R-25 · Контракт: C9, C13, C15
  Файлы: courses/rung_theory/api.py, courses/rung_theory/tests/test_api_rung_theory.py, docs/api/endpoints/course-rung-theory.md
  Зависит от: K1, K2
  Приёмка: AC-2 (ручка), AC-17 (rung-theory) — TA, TC1
  Готово-когда: test_rung_theory_payload_shape, test_rung_theory_access_5_roles, test_rung_theory_no_llm_calls зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: content
- [ ] V3 [V] Вкладка «Контент» по ступеням (сторона клиента)
  Срез: R-26, R-12 (пачка «Сгенерировать теорию · N») · Контракт: C20
  Файлы: …/content/rung/RungContentTab.tsx, …/content/rung/RungTheoryBlock.tsx, …/content/rung/rungTheoryLabels.ts, __tests__/components/rungContentTab.test.tsx
  Зависит от: K3
  Приёмка: AC-22 (юнит; Playwright — acceptance)
  Готово-когда: rungContentTab.test (6 состояний с кнопками; после генерации перечитывает) зелёный; `/frontend-style` пройден
  Риск: обычный · Размер: M (15) · Тест-группа: frontend
  Почему по сторонам: V2 + V3 вместе больше M, а склейку держат TA и приёмка

История B — генерация и деньги
- [ ] V4 [V] `generate`: единица основного носителя, снимок, разделы по пяти шагам, план расхода
  Срез: R-13 `generate`, R-8, R-14 (резерв ≥ факт), шаг 4 R-15 на стороне django · Контракт: C11, C16, C17
  Файлы: courses/topic_content/generation/rung_theory_units.py, courses/rung_theory/writer.py, courses/topic_content/generation/units.py, courses/topic_content/generation/tests/test_rung_theory_generate.py
  Зависит от: K1, K2
  Приёмка: AC-3, AC-8 (generate) — TB
  Готово-когда: test_generate_creates_primary_carrier_with_snapshot, test_empty_composition_map_only, test_step4_question_rule_two_lexical_nodes, test_reserve_ge_actual, test_billing_refusal_leaves_carrier зелёные
  Риск: deep (деньги) · Размер: M (24) · Тест-группа: content
- [ ] V5 [V] `complete` и `map`: слияние с действующей версией под замком, подстраховка автопути
  Срез: R-13 `complete`/`map`/«нечего делать», R-14 (автопуть), R-8 · Контракт: C9, C11, C16
  Файлы: courses/topic_content/generation/rung_theory_merge.py, courses/course_pipeline/auto_pipeline.py, courses/topic_content/generation/tests/test_rung_theory_merge.py, courses/course_pipeline/tests/test_auto_pipeline_rung_theory.py
  Зависит от: K1, K2
  Приёмка: AC-6, AC-19, AC-8 — TB
  Готово-когда: test_complete_copies_serving_sections_bytewise, test_complete_merges_author_edit_during_generation (два потока, `select_for_update`), test_map_adds_only_map, test_nothing_to_do_200_without_rung, test_backstop_generate_and_map_never_complete зелёные
  Риск: deep (конкурентность) · Размер: M (24) · Тест-группа: content, saga
  Внешний конфликт: `auto_pipeline.py` — шаг 6 ставит туда раскладку задач банка после гейта 1
- [ ] V6 [V] Промпт теории ступени в ml-llm
  Срез: R-15 · Контракт: C17
  Файлы: services/ml-llm/…/prompts/plan_system_rung_theory.md, …/text_system_rung_theory.md, services/ml-llm/…/rung_theory.py (выбор варианта по `kind`), services/ml-llm/tests/test_rung_theory_prompt.py
  Зависит от: K2
  Приёмка: AC-7 — у acceptance вживую
  Готово-когда: test_rung_theory_schema_roundtrip, test_five_steps_in_plan_prompt, test_refs_passed_as_context зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: ml-llm

История C1 — материал без темы: доступ, читатели, отказы
- [ ] V7 [V] Доступ к материалу без темы
  Срез: R-29; `views.py:1035/1149/1206/270` · Контракт: C3
  Файлы: courses/access_registry/preflight.py, courses/topic_content/views.py, courses/access_registry/tests/test_preflight_rung_material.py
  Зависит от: K1, K2
  Приёмка: AC-17, AC-13 (предполётная проверка старого материала) — TC1
  Готово-когда: test_preflight_course_from_material_field, test_author_2xx_stranger_403_anon_401_without_topic, test_legacy_material_same_course, test_response_topic_id_null_not_string зелёные
  Риск: deep (права) · Размер: S (16) · Тест-группа: platform
- [ ] V8 [V] Отказы по пути
  Срез: R-31, R-34 · Контракт: C13, C14
  Файлы: courses/pipeline_path.py, courses/tests/test_pipeline_path_refusals.py
  Зависит от: K2
  Приёмка: AC-15 — TC1
  Готово-когда: test_topic_endpoints_422_topic_material_on_flag (7 ручек), test_rung_endpoints_422_rung_material_off_flag (5 ручек), test_off_flag_topic_endpoints_unchanged зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: platform
- [ ] V12a [V] Вставные вопросы и IE-9/IE-10 без темы
  Срез: R-28 (группа «topic_content и вопросы») · Контракт: C3, C9
  Файлы: courses/topic_content/models.py (только IE-9/IE-10, после K1), courses/topic_content/embedded_items/services.py, courses/topic_content/embedded_items/tests/test_rung_carrier.py
  Зависит от: K1, K2
  Приёмка: AC-4 (вопросы) — TC1
  Готово-когда: test_ie9_no_attribute_error_without_topic, test_ie10_foreign_knowledge_refused_on_rung_carrier, test_embedded_knowledge_from_rung зелёные; к отчёту приложен список grep из §10 п. 3 спеки
  Риск: обычный · Размер: M (15) · Тест-группа: banks
- [ ] V12b [V] Читатели курса материала в покрытии, редакторе графа и фактах гейта
  Срез: R-28 · Файлы: courses/topic_content/coverage/{check,gate}.py, courses/course_graph_editor/read.py, courses/course_pipeline/gates/facts.py, courses/task_classes/gate_rules.py, courses/topic_content/coverage/tests/test_coverage_without_topic.py
  Зависит от: K1, K2 · Приёмка: AC-4 — TC1
  Готово-когда: test_coverage_check_course_from_material, test_graph_editor_keys_not_none_bucket, test_facts_without_topic зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: content
- [ ] V12c [V] Читатели в контексте генерации задач и банке диагностики
  Срез: R-28, R-20 (потребители `sections_for_knowledge`) · Контракт: C10
  Файлы: courses/topic_content/generation/{context,dispatch}.py, courses/diagnostic_bank/payload.py, courses/topic_content/generation/tests/test_context_rung_theory.py
  Зависит от: K1, K2 · Приёмка: AC-4, AC-12 (контекст) — TC1
  Готово-когда: test_supportive_sections_from_rung_theory, test_diagnostic_payload_course_from_material, test_dispatch_without_topic_order зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: content

История C2 — материал ступени: ручки, разделы, редактор
- [ ] V9a [V] Ручки материала ступени: добавить вручную, версии, переключить, носитель
  Срез: R-30 (4 из 5), R-32 (создание) · Контракт: C13–C15
  Файлы: courses/topic_content/rung_views.py, courses/topic_content/rung_material.py, courses/topic_content/tests/test_rung_material_endpoints.py, docs/api/endpoints/post-course-task-class-theory.md, …/get-course-topic-content-versions.md, …/post-course-topic-content-switch-current.md, …/patch-course-topic-content-carrier.md
  Зависит от: K1, K2 · Приёмка: AC-18, AC-17 (эти ручки) — TC2, TC1
  Готово-когда: test_add_theory_creates_empty_draft_group, test_double_click_serialized, test_versions_by_group_no_topic, test_switch_current_by_group (+ вызов хука reopen), test_carrier_rename_place, test_access_5_roles зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V9b [V] Импорт документа в носитель ступени
  Срез: R-30 `populate-from-documents`, R-32 (импорт) · Файлы: courses/topic_content/passthrough.py, courses/topic_content/tests/test_rung_populate.py, docs/api/endpoints/post-course-topic-content-populate-from-documents.md
  Зависит от: K1, K2 · Приёмка: AC-18 — TC2
  Готово-когда: test_populate_passthrough_into_carrier_topic_null, test_populate_llm_generate_group_from_carrier зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: documents
- [ ] V10 [V] Правила разделов: карта, знания раздела
  Срез: R-4, R-32 («знания раздела правятся автором») · Контракт: C4, C12
  Файлы: courses/rung_theory/section_rules.py, courses/topic_content/serializers.py, courses/rung_theory/tests/test_section_rules.py
  Зависит от: K1, K2 · Приёмка: AC-16 — TC2
  Готово-когда: test_second_map_already_taken, test_map_on_backing_not_applicable, test_section_knowledge_ids_validated_not_knowledge, test_map_payload_is_block_array зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V11 [V] Форк, пересборка и читатели в `topic_content/services.py`
  Срез: R-32 (форк, `knowledge_ids` и `understanding_step` на обоих путях; пересборка без карты), R-28 (`services.py:606/835/879/1416/1497/1637`)
  Файлы: courses/topic_content/services.py, courses/topic_content/tests/test_fork_rebuild_rung.py
  Зависит от: K1, K2 · Приёмка: AC-16, AC-4 (подтверждение, отклонение, удаление без темы) — TC2, TC1
  Готово-когда: test_fork_keeps_knowledge_ids_both_paths, test_rebuild_keeps_map_and_uses_course_discipline, test_confirm_without_topic_no_doesnotexist, test_reject_and_delete_by_id_pass_course_and_replaced_version зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: content
- [ ] V22 [V] Редактор материала без темы
  Срез: R-33, текст `force` пересборки R-32 · Контракт: C20
  Файлы: …/content/ContentEditorDrawer.tsx (ветка по флагу), …/content/SectionsList.tsx, …/content/SectionsRail.tsx, …/content/SectionKnowledgePicker.tsx, __tests__/components/contentEditorRung.test.tsx
  Зависит от: K3 · Приёмка: AC-16 (фронт), AC-18 (Playwright — acceptance)
  Готово-когда: contentEditorRung.test (выбор знаний: сверху C(R), поиск; OCC `expected_updated_at`; подпись «Карта подхода», шаги нумерованы; шаг понимания только подписью; версии через ручки R-30) зелёный
  Риск: deep (форма с несохранёнными правками и OCC) · Размер: M (24) · Тест-группа: frontend

История D — перенос
- [ ] V20a [V] Дозаполнение `course`, отчёт из журнала
  Срез: R-21 п. 7 (отчёт), п. 9 · Контракт: C5, C18
  Файлы: courses/rung_theory/backfill.py, courses/rung_theory/report.py, courses/rung_theory/tests/test_backfill_course.py
  Зависит от: K1, K2 · Приёмка: AC-13 (дозаполнение) — TD
  Готово-когда: test_backfill_only_null_rows_all_courses, test_backfill_dry_run_prints_count, test_backfill_row_without_paths_reported, test_report_from_journal зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: content
- [ ] V20b [V] Перенос «Теорий» на первую ступень пары, удаление оболочек, раннбук
  Срез: R-21 пп. 1–8 · Контракт: C1–C6, C18
  Файлы: courses/rung_theory/transfer.py, courses/topic_content/rung_theory_migration.py (+ строка в `WRITER_FILES` скрипта сторожа), scripts/check_topic_content_writes.py, courses/rung_theory/tests/test_transfer.py, docs/meta/process/rung-theory-migration-runbook.md
  Зависит от: K1, K2 · Приёмка: AC-5 — TD
  Готово-когда: test_dry_run_writes_nothing, test_apply_moves_versions_sections_bytewise, test_shells_deleted_with_snapshot_and_document_task_class_logged, test_second_apply_zero_changes, test_course_with_student_refused, test_no_llm_no_ledger, test_reverse_migration_after_apply, test_journal_dump_count_matches зелёные
  Риск: deep (миграция данных) · Размер: M (24) · Тест-группа: content
  Примечание: оболочки удаляет вызовом существующего писателя `course_structure/deletion.py`, сам файл не правит (его правит V17b). Если понадобится правка — доклад, а не правка

История E — гейты
- [ ] V19a [V] Четыре правила гейта 2 на флаге
  Срез: R-22 · Контракт: C9, C13
  Файлы: courses/course_pipeline/gates/rules_rung_theory.py, courses/course_pipeline/tests/test_rules_rung_theory.py
  Зависит от: K1, K2 · Приёмка: AC-9 — TE
  Готово-когда: test_knowledge_missing_blocker_by_C0, test_deleted_section_blocks_despite_snapshot, test_unmarked_section_warning_except_intro_and_map, test_outdated_warning_not_blocking_moderation, test_map_missing_blocker зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: saga
- [ ] V19b [V] Снятие правил «Теории» на флаге, `ksa-task-class-inadequate`
  Срез: R-23 «снимаются», AC-21 · Файлы: courses/graph_invariants/structure_gate.py, courses/course_pipeline/gates/rules_content.py, courses/course_pipeline/gates/rules_topic_content.py, courses/task_classes/readiness.py, модуль правила `ksa-task-class-inadequate`, courses/course_pipeline/tests/test_reading_rules_off_on_flag.py
  Зависит от: K1, K2 · Приёмка: AC-9 (снятые правила), AC-21 — TE
  Готово-когда: test_reading_rules_silent_on_flag_fire_off_flag, test_a_lines_missing_reading_not_applied_on_flag, test_ksa_inadequate_silent_for_S_or_jit зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: saga
  Внешний конфликт: шаг 6 правит `structure_gate.py` (инвариант «линия А без чтения — одной функцией по флагу») и правила гейтов. Брать, когда соответствующая задача шага 6 не в полёте
- [ ] V19c [V] Откат гейта 2 по условию блокера
  Срез: R-23 «откат» · Контракт: C9, C12
  Файлы: courses/rung_theory/reopen.py, courses/saga/gate_backing.py, courses/saga/reopen.py, courses/course_pipeline/gating.py, courses/saga/tests/test_reopen_rung_theory.py
  Зависит от: K1, K2 · Приёмка: AC-20 — TE
  Готово-когда: test_complete_approval_no_reopen, test_other_rung_edit_no_reopen, test_delete_or_reject_covering_version_reopens, test_approved_fork_without_section_reopens, test_backing_lost_predicate_false_on_flag, test_off_flag_unchanged зелёные
  Риск: deep (сага) · Размер: M (24) · Тест-группа: saga
  Внешний конфликт: `saga/` у шага 6 (гейт 3, недостача)

История F — структура и окно ступени
- [ ] V17a [V] Нет «Теории» как класса на флаге: сервер и окно
  Срез: R-1, R-27 · Файлы: courses/task_classes/services.py (`kind` в создании и правке), courses/task_classes/rung_layout.py (скелет без `content_reading` на флаге), courses/structure_gen/skeleton.py, …/structure/TaskClassModal.tsx, …/structure/TopicTreePanel.tsx, courses/task_classes/tests/test_no_reading_kind_on_flag.py, __tests__/components/taskClassModalNoKind.test.tsx
  Зависит от: K1, K2, K3 · Приёмка: AC-11 — TF
  Готово-когда: test_kind_content_reading_422_not_applicable, test_skeleton_no_reading_on_flag, taskClassModalNoKind.test (нет поля «Тип» и «+ Теория» на флаге, без флага прежнее) зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: banks (имя `task_class`), frontend
  Внешний конфликт: **сильный.** Шаг 6 правит `TaskClassModal.tsx` (режимы) и `task_classes/services.py`. Правка шага 8 — несколько строк. Брать только после вливания задачи шага 6 на этих файлах. Ранг у V17a низкий — не на пути
- [ ] V17b [V] Перегенерация и удаление ступени с теорией
  Срез: R-16, R-17, R-17a; R-28 (`rung_layout_db.py:1137`, `parent_deletion.py:130`)
  Файлы: courses/task_classes/rung_regen.py, courses/task_classes/rung_layout_db.py, courses/course_structure/deletion.py, courses/topic_content/parent_deletion.py, …/structure/<окно удаления ступени>.tsx (одна строка текста), courses/task_classes/tests/test_regen_delete_rung_theory.py
  Зависит от: K1, K2 · Приёмка: AC-10 — TF
  Готово-когда: test_kept_key_keeps_theory, test_gone_rung_with_theory_parked, test_no_reading_match_on_flag, test_delete_rung_with_approved_theory_parks, test_unapproved_theory_deleted_with_rung зелёные; `check_course_structure_writes.py` зелёный
  Риск: deep (данные) · Размер: M (24) · Тест-группа: structure
  Внешний конфликт: `course_structure/` у шага 6 (копия, писатель)

История G — уроки и трек
- [ ] V13 [V] Урок Б: теория нужных ступеней и карта
  Срез: R-20 · Контракт: C10
  Файлы: courses/rung_theory/sections.py, courses/dialogue/material_b.py, courses/dialogue/tests/test_material_b_rung_theory.py
  Зависит от: K1, K2 · Приёмка: AC-12 (урок Б) — TG
  Готово-когда: test_source2_sections_by_task_knowledge, test_map_always_included, test_backing_source_unchanged зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: lessons
  Внешний конфликт: шаг 6 переводит `dialogue/` на читателя задач курса — пробное слияние
- [ ] V14 [V] Урок А по ступени и «Опирается на»
  Срез: R-18, R-19 (сервер и клиент) · Контракт: C9, C15, C20
  Файлы: courses/lesson/mode_a/services.py, courses/lesson/mode_a/theory_read.py, courses/topic_content/lesson_modes.py, courses/lesson/serializers.py, services/frontend/utils/lessons.ts, …/lessons/[lessonId]/_components/mode-a/LessonModeA.tsx, …/mode-a/LessonDependsOn.tsx, courses/lesson/mode_a/tests/test_mode_a_rung.py, __tests__/components/lessonDependsOn.test.tsx
  Зависит от: K1, K2, K3 · Приёмка: AC-12 (урок А) — TG
  Готово-когда: test_lesson_a_by_rung_no_fallbacks_on_flag, test_refs_block, test_student_read_theory_without_credit, test_no_lesson_a_when_only_map, lessonDependsOn.test зелёные
  Риск: обычный · Размер: M (15) · Тест-группа: lessons, frontend
  Внешний конфликт: шаг 6 снимает проверки режимов в `mode_a`
- [ ] V16 [V] Трек: урок А ступени перед практикой
  Срез: R-20a · Файлы: courses/track_manage/services.py, courses/track_manage/planner.py, courses/track_manage/tests/test_track_rung_theory.py
  Зависит от: K1, K2 · Приёмка: AC-12 (трек) — TG
  Готово-когда: test_lesson_a_before_practice_by_carrier, test_no_lesson_a_goes_to_practice, test_no_user_task_class_for_reading_on_flag зелёные
  Риск: обычный · Размер: S (10) · Тест-группа: graph

### Хвост

- [ ] H1 [H] Реестры документов и хвосты ревью
  Файлы: docs/INDEX.md, docs/TAGS.md, CHANGELOG, журнал концепции, ADR-099 (D9 на флаге — О-6), статус спеки, docs/engineering/module-map.md (финальная пересборка), дословные находки «можно сливать, хвост»
  Зависит от: все
  Готово-когда: `check.sh` зелёный, `gen_module_map.py --check`, `check-codes.py`, проверки ссылок документов зелёные; каждая находка «хвост» закрыта или перенесена задачей
  Риск: обычный · Размер: M (15) · Тест-группа: governance

### Покрытие требований

R-1 V17a · R-2 K1 · R-3 K1 + писатели · R-4 V10 · R-5–R-7 V1 · R-8 V4/V5 · R-9–R-12a V1
(расчёт) + V3 (показ) · R-13 K2/V4/V5 · R-14 V4/V5 · R-15 V6 + V4 · R-16/R-17/R-17a V17b ·
R-18/R-19 V14 · R-20 V13 + V12c · R-20a V16 · R-21 V20a/V20b · R-22 V19a · R-23 V19b/V19c ·
R-24 K2 · R-25 V2 · R-26 V3 · R-27 V17a · R-28 K1 + V7 V11 V12a–c V14 V17b · R-29 V7 ·
R-30 K2 + V9a/V9b · R-31 K2 + V8 · R-32 K1 + V4 V5 V9a V9b V10 V11 V20b + V22 · R-33 V22 ·
R-34 K2 + V8. AC-1…AC-22 — у каждого есть `[T]` (таблица выше) или `acceptance` (AC-7 и
Playwright).

## 4. Расписание по слотам (N = 4, без шума и доработок, HLFET)

```
слот1: K3[0-10]  TB[10-20]  TE[20-30]  V3[30-45]   V5[45-69]   V7[69-85]   V10[85-100]  V17a[100-115] V2[115-125]  V13[125-135]
слот2: TA[0-10]  TC2[10-20] TF[20-30]  V22[30-54]  V17b[54-78] V6[78-93]   V12a[93-108] V19b[108-123] V12b[123-133] V20a[133-143]
слот3: K2[0-15]  TD[15-25]  TG[25-35]  V1[35-59]   V19c[59-83] V9a[83-98]  V14[98-113]  V8[113-123]   V12c[123-133] H1[153-168]
слот4: K1[0-24]  TC1[24-39] V4[39-63]  V20b[63-87] V11[87-102] V19a[102-117] V9b[117-127] V16[127-137]
```

Что видно в расписании:
- **Окно К (0–35 мин) занято полностью.** Пока K1 (deep M) пишется и проходит ревью, три
  других слота делают K2, K3 и все восемь `[T]` (110 слот-минут на три слота). Ради этого
  `[T]` и задуманы.
- Веер стартует, как только влит K1 (≈ 35 мин). V3 и V22 ждут только K3 и начинают раньше.
- Deep M (ранг 39) идут первыми, S-задачи (ранг 25) — в конце. Поэтому хвост веера
  составляют короткие задачи, а не длинные.
- По модели с доработками (p = 0.43) слоты заняты на 4.0 до ~180 мин и на 3.6–3.9 в
  интервале 40–100 мин, где идут ревью K и первые сдачи. После ~190 мин занятость падает
  до 1.3 → 0.3: работы нет, а вторые круги доработок и ревью тянут хвост. Этот хвост
  (~70 мин из 266) — главный простой фичи. Слотами его не лечить, лечить снижением p (§7).
- При N = 5 детерминированно выходит 151 мин против 178 (−15 %), в модели — −12 %. Правило
  design §1.11 («пятый — только если P ≥ 5») выполнено, но порог 2K = 10 не набран.
  Рекомендация — **K = 4**, пятого брать, только если пул не делится с шагом 6 (§5 п. 5).

## 5. Конфликты и простой

1. **Текст внутри фичи.** Проба даёт 0 пересечений `Файлы:` у задач без пути. Каждый общий
   файл передаётся по ребру К → V: `models.py` K1 → V12a, `services.py` K2 → V11,
   `writer.py` K2 → V4. Названный предел — три места, где «0» неправда:
   - **`docs/engineering/module-map.md` — генерируемый файл, и он считает места импорта
     между модулями.** Любой срез, который впервые импортирует `rung_theory` из нового
     места, меняет подпись стрелки. Значит, его правит почти каждый backend-срез. Правило:
     генерируемые файлы — класс `regen` в `pair-rules.txt`. Конфликт в них при rebase не
     правится руками: берётся сторона главной ветки и запускается генератор, `check.sh`
     проверяет `--check`. Пробное слияние конфликтом это не считает.
   - Поправка контракта добавлением (новый код ошибки, найденный в срезе) — правка
     `response-codes.json` вне К. Два таких среза столкнутся в одном JSON. Пробное слияние
     при сдаче это поймает → `доработка` без ревью (~3 мин).
   - `urls.py` и реестр доступа: все маршруты заводит K2, поэтому срезы их не трогают. Если
     срезу понадобился ещё маршрут, это поправка контракта.
2. **Миграции.** Их пишет только K1, две штуки. Шаг 6 пишет свои одновременно, а цепочка
   линейна. Ресурс `serial: migrations` общий для двух планов. Номер ставится при
   вливании K1. Если шаг 6 влил миграцию раньше, K1 перед вливанием перенумеровывает свою
   (≈ 2 мин). После K1 ни один срез шага 8 миграций не пишет.
3. **Пересечения с шагом 6** (он идёт одновременно в той же ветке плана). Сильные:
   V17a (`TaskClassModal.tsx`, `task_classes/services.py`), K2 (реестры кодов, гейтов,
   тестов, ярусов). Средние: V19b (`structure_gate.py`, правила гейтов), V19c и V5 (`saga/`,
   `auto_pipeline.py`), V17b (`course_structure/`), V14 (`mode_a`), V13 (`dialogue/`), H1
   (INDEX, TAGS, CHANGELOG). Правило B: **один `next` на объединённый граф двух фич**. Карта
   владения общая, задача не стартует, пока задача другой фичи на её файле в полёте.
   Ранги у V17a, V13, V16 низкие, им проще всего ждать. K2 ждать нельзя (ранг 54), поэтому
   его правки реестров — только дописывание в конец своих разделов, и при сдаче он проходит
   пробное слияние с ветками шага 6.
4. **Тесты и CI.**
   - Полный `courses` (30 мин, 11 тыс.) срез не гоняет. Ему хватает узкой проверки и групп
     из `Тест-группа:`.
   - Отпечаток CI грубый: любая правка `services/` сбрасывает все группы django. Поэтому
     собирать партии без пересечения групп пока бесполезно. Партия собирается **по
     времени**, а не по группам.
   - Найдено при планировании: в `cicd.yml` стоит `concurrency: cicd-${ref}` с
     `cancel-in-progress: true`. Пуш ветки плана, пока идёт прогон, **отменяет** этот прогон.
     При вливании раз в ~7 мин (38 вливаний за ~266 мин) и прогоне 15–28 мин CI без партий
     не завершился бы ни разу. Отсюда правило координатора: пуш не чаще одного раза за
     длительность CI. На наших темпах это 3–4 вливания на партию, на две фичи — 6–8.
     Пушит один координатор за обе фичи.
   - Итог: ~10–12 партий; на пути только последняя, +15–28 мин.
   - Ловушки групп: имена с `unit` уходят в `billing`, с `task_class` — в `banks`,
     `rung_theory` без исключения K2 — в `core` (потолок 2).
5. **Пул исполнителей.** Если лимит 4–5 — на сессию, а не на фичу, шаги 6 и 8 делят его. Тогда
   прогноз §0 оптимистичен ровно на долю слотов шага 6. Именно поэтому нужен один `next` на
   объединённый граф: HLFET по объединению отдаёт слоты задачам с большим рангом, кто бы их
   ни нёс. Две очереди «по фиче» дали бы тот же простой, что сегодня.
6. **Стенды.** e2e на `cc-*` и живая генерация на `cp-*` — последовательные ресурсы. В срезах
   их нет совсем: Playwright 1200/375 и `/lesson-qa` делает `acceptance` по истории, как только
   влиты её срезы. Истории вливаются в разное время, поэтому приёмки идут внахлёст с веером.
   На пути только приёмка последней истории (обычно B или C2 — у них deep M и живая
   генерация AC-7), ~20–40 мин.
7. **Документы.** Каждый срез пишет свой файл: документы ручек — V2, V9a, V9b; раннбук —
   V20b; ADR-099, INDEX, TAGS, CHANGELOG, журнал — только H1. V20a в раннбук не пишет: шаг
   дозаполнения описан в C18, и V20b вписывает его по контракту.

## 6. Ревью, доработки, вливания

- Сдача освобождает слот. Перед ревью скрипт делает пробное слияние со всеми ветками обеих
  фич в полёте, проверяет `hold` и `check.sh`. Конфликт → `доработка` без ревью.
- Ревью — пул R = 3, одна линза на вид задачи:
  - `[K]` — «хватит ли срезам»: каждый шов C-n из таблицы на месте, заглушки вызываемы,
    типы полны;
  - `[T]` — «каждый AC-n покрыт, тест бьёт обе стороны»;
  - `[V]` — логика, `Контракт:`, `Готово-когда:`/`AC-n`; механику ревьюер не повторяет.
- Вердикт «можно сливать, хвост» уходит в H1 и не даёт второго круга. Доработку берёт любой
  свободный исполнитель новым запуском. Предел — два круга, дальше человек.
- Вливание: срез вливается после своих К и `[T]` истории; rebase, `--ff-only`, генерируемые
  файлы пересобираются (§5 п. 1); пуш партиями по времени (§5 п. 4).
- Приёмка `acceptance` по истории: A (AC-22 Playwright), B (AC-7 вживую на `cp-*`, AC-6 один
  прогон), C1, C2 (AC-18 Playwright), D (AC-5 на копии курса), E, F (AC-11 Playwright), G
  (`/lesson-qa`). Плюс прогон описи шага Р — после H1.

## 7. Прогноз и чем его улучшить

| Сценарий (N = 4, R = 3) | Веер | + CI + приёмка | Запусков исп./ревью |
|---|---|---|---|
| p = 0.43 (сегодня) | 266 мин (p90 293) | ≈ 5–5.5 ч | 58 / 58 |
| p = 0.30 | 242 | ≈ 4.6–5 ч | 51 / 51 |
| p = 0.15 (цель) | 216 | ≈ 4.2–4.6 ч | 44 / 44 |

Цена по медианам наблюдений (deep $4.9, обычный $0.94, ревью $1.5). Первый круг:
9 × 4.9 + 29 × 0.94 ≈ $71. Доработки при p = 0.43 добавляют ≈ $25–30. Ревью: 58 × 1.5
≈ $87. Итого ≈ $180–190 на фичу. При p = 0.15 — ≈ $140.

Что даёт больше всего (по модели):
1. **Снижение p сильнее пятого слота.** Переход с 0.43 на 0.15 даёт −19 %, пятый слот при
   p = 0.43 — −12 %. План бьёт три причины отказов:
   - «расхождение сторон» — инвариантом K1 (§1 п. 2) и `[T]`, которые бьют обе стороны;
   - «незакрытый пункт» — `Готово-когда:` с именами тестов и снятием `@expectedFailure`
     своих AC;
   - «тест, который ничего не держит» — `hold`.
   Четвёртая причина, «пересечение с соседней задачей» (16 из 19 отказов при 4
   исполнителях), закрыта картой владения и пробным слиянием с ветками шага 6.
2. **Хвост доработок.** Это ~70 мин в конце, слотами он не лечится. Помогает только ранний
   старт deep M (уже так по HLFET) и «хвост» вместо второго круга для мелочей.
3. **R = K − 1.** R = 2 стоит +32 мин.

## 8. Что проверить после реализации (для сравнения с бейзлайном)

- Сколько отказов ревью пришлось на «расхождение сторон» и «пересечение». Если после
  инварианта K1 и общей карты с шагом 6 их всё ещё > 15 % отказов, правило «один `next` на
  обе фичи» не работает на деле.
- q — доля отказов K2 со сменой смысла шва. K2 на пути (ранг 54), и от него зависят 24
  среза. Отказ K2 по смыслу C9/C11/C16 останавливает веер целиком.
- Выдержал ли K2 размер M. Если вышло больше 300 строк, в следующей фиче реестры уходят
  в отдельную K4 (глубина остаётся 1).
- Действительно ли V5 обошёлся без V4: шов C11 (минимальный писатель в K2) против ребра
  `V4 → V5`. Если TB нашла расхождение писателя, правило «порт с минимальным настоящим
  телом в К» надо пересмотреть.
- Сколько раз CI отменялся `cancel-in-progress` на ветке плана.

## 9. Открытые места для `architect` (на круг 2)

- Адрес чтения теории учеником (R-19) спека не задаёт. В C15 предложен
  `GET /api/v1/courses/{c}/task-classes/{tc}/theory/read`. Нужно подтверждение, иначе шов
  поменяет смысл после старта.
- Не нарушит ли импорт `rung_theory` из `topic_content/services.py` и `models.py` правила
  ярусов (`module-rules.md`, сторож границ). Если да, хуки C12 переезжают в
  `topic_content/rung_hooks.py`, а `rung_theory` получает ярус ниже `topic_content`.
- Окно удаления ступени (V17b) — имя файла на фронте. Одна строка текста, но это общий с
  шагом 6 каталог `structure/`.
