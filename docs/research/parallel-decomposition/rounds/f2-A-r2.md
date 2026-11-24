# Фича 2 (шаг 8, теория ступени): разложение команды A, круг 2

Дата: 2026-11-24. Процесс описан в `design.md`: K → веер `[V]` → `[H]`, `[T]` идёт параллельно с K.
Входные данные: `feature-2-description.md`, `step8-spec-sanitized.md`, код `nastavnik_stage_1` на коммите `053602900`,
замечания оценщика к `f2-A-r1.md`.
Проверки лежат в `simF2A_r2/`:
- `plan.py` — граф;
- `probe.py` — проба §5;
- `sim.py` — событийная модель с очередью вливаний координатора;
- `trace.py` — детерминированное расписание;
- `calib.py` — калибровка по плану r1;
- `cls.py` + `names.txt` — группы тестов по `test_registry.classify` базового коммита.

## 0. Итог в цифрах

| Мера | r1 | **r2** |
|---|---|---|
| Задач | 43 (K 4, `[T]` 8, `[V]` 25, `[S]` 5, `[H]` 1) | **32** (K 5, `[T]` 6, `[V]` 18, `[S]` 2, `[H]` 1) |
| Задач deep | 18 | **10** |
| W (сумма весов) | 718 мин | **550 мин** (−23 %) |
| S (критический путь) | 89 (99 строго) | **69** (то же со строгим ребром `[T]` → срез) |
| P = W/S | 8.1 / 7.3 | **7.97**: при K = 4 это **предупреждение** (< 2K = 8), при K ≤ 3 — норма |
| Фаза K | 78 мин, 11 % | 102 мин, **18.5 %** W; глубина 2 только у T005 (`Почему не одна:`) |
| Вливаний (очередь координатора) | 43 | **32** |
| Слияние только по вливанию (вне формы §4) | 6 срезов ждут T013 | **нет** |
| Пары «сервер ∥ клиент» | 4 | **0**: каждый срез идёт насквозь по сценарию |
| Тестов в `core` (реестр, `core_ceiling = 2`) | 4+ | **0** (проверено `cls.py`, §6) |

Прогноз (`sim.py`, 400 прогонов; ревью 8 мин; вливание c = 6 мин, последовательная очередь;
CI последней партии +21 и приёмка +30 включены, как в `evsim2.py`):

| Слоты фичи N / ревьюеры R | p = 0.43 | p = 0.61 (бейзлайн ф. 2) | занято из N | $ (p = 0.43 / 0.61) |
|---|---|---|---|---|
| **N = 4, R = 3** | **326 мин (5.4 ч)**, p90 354 | 356 (5.9 ч), p90 387 | 2.87 / 2.96 | 180 / 213 |
| N = 4, вливания партией (4 + 2n мин) | 320 | 351 | 2.93 / 3.00 | то же |
| N = 3, R = 2 | 377 (6.3 ч) | 421 (7.0 ч) | 2.43 / 2.45 | то же |
| **N = 2, R = 2 (делёж со шагом 6)** | **497 (8.3 ч)**, p90 539 | **559 (9.3 ч)**, p90 600 | 1.77 | то же |
| N = 5, R = 4 | 310 (−5 % к N = 4) | 327 (−8 %) | 3.06 / 3.26 | то же |

Калибровка: план r1 в моей модели даёт 406 / 441 мин и $271 при N = 4, c = 6. У `evsim2.py` оценщика
на тех же данных 412 / 448. Значит, модели совпадают в пределах 2 %, и расхождение r1 → r2
объясняется планом, а не моделью.

**Совет.** Если шаг 6 не занимает слоты, K = 4, R = 3. Если шаг 6 идёт одновременно, считать N = 2–3:
план для этого и сделан, при K ≤ 3 он в норме по P. Пятого исполнителя не ставить. При c = 6
он даёт −5…−8 %, а при последовательной очереди и p = 0.25 почти ничего (294 против 302).
Сначала нужно снять очередь вливаний (§8, п. 1).

## 1. Ответы на замечания оценщика

| # | Замечание | Что сделано | Проверка |
|---|---|---|---|
| 1 | Нет очереди вливаний координатора | В модель добавлена последовательная очередь c = 6 мин. Задача, которая ждёт ворот, координатора не занимает. 32 вливания вместо 43 | N = 4: 300 → 326 мин (+9 %, у r1 +13 %). Детерминированно 173 → 241, а партиями 196 (§7) |
| 2 | Нет сценария N ≈ 2 | Посчитан. W уменьшен на 23 %, deep сокращены с 18 до 10 | N = 2: 559 мин при p = 0.61 (доля отказов бейзлайна) против ~600–630: **−7…−11 %**. При p = 0.43 497 мин (−17…−21 %). Выигрыш небольшой, но он есть. Цена $180–212 против ~$133, то есть **×1.35–1.6** (у r1 ×1.8–2.0) |
| 3 | Скрытые общие файлы без владельцев | Таблица §6: реестр тестов, карта ярусов, `AGENTS.md`/`README.md` пакета, `module-map.md`, `TAGS.md`, `api-doc-coverage`, `WRITER_FILES`, `rules_structure.py`, `apps.py`, `courses/models.py` (потолок строк) | имена тестов прогнаны через `classify`, в `core` ноль |
| 4 | Пакет `rung_theory/__init__.py` создают две K | Пакет создаёт только T002. Модель журнала переноса лежит в `topic_content/models.py`, поэтому T001 в пакет не пишет | §4, карта владения |
| 5 | T002 перегружена | Разрезана на T003 (реестры, маршруты, заглушки ручек и документов; обычная) и T004 (точки вызова в горячих файлах; deep) | ×3 и отказ T004: 326 → 370 мин (N = 4), 497 → 550 (N = 2); обе (T003 и T004): 384 / 582. Запасной разрез T004 на a/b: 342 / 539 (§9) |
| 6 | Деление по сторонам | Убрано. Срез идёт по сценарию насквозь: «Контент» (T012), кнопки генерации (T017), редактор (T019), разделы с выбором знаний (T020), урок А (T026), окно ступени (T029). Клиентские обёртки лежат в своих файлах `utils/rung*.ts` среза, а не в общем `auth.ts` | 0 пар |
| 7 | Слишком много мелких задач | 43 → 32. Слиты T037+T038, T031+T032, T033+T034, T026→T018, T022+T025→T022, T040+T041, T015→T017, T042→`[H]`; `[T]` US1 и US2 объединены | ни одной задачи S среди `[V]` |
| 8 | 18 deep | Оставлено 10 deep: схема, чистая функция, хуки в горячих файлах, запись под замком, деньги, доступ, ручки материала с замком, перегенерация структуры, перенос, удаление оболочек | $240 → $180 при p = 0.43 |
| 9 | P = 7.3 — предупреждение, K = 5 не подтверждён | P = 7.97, при K = 4 названо предупреждением. От K = 5 отказался по расчёту | таблица §0 |
| 10 | Ребро «только вливание» на T013 | Убрано. Загрузчик стал K глубины 2 (T005) с полем `Почему не одна:` (§3.2 п. 3 и §2.4 design). Потребители **стартуют** после его вливания | отказ T005 на ревью: ±0 мин (N = 4: 325 против 326) и +4 мин (N = 2): 7 потребителей ждут, остальные 13 срезов занимают слоты |
| 11 | `cancel-in-progress`, `auto_pipeline.py`, `gate_backing.py` | CI идёт на отдельных ссылках партий. Пересечения названы | §8 |
| 12 | Форма xfail, имена тестов, `Тест-группа:` | Django: `@unittest.expectedFailure`; jest: `test.failing`; Playwright: `test.fail()`. В `Готово-когда:` стоят имена тестов. `Тест-группа:` у каждой задачи посчитана через `classify` | §4, §5 |

## 2. Как резал (позиция A, что изменилось)

1. **Контракт вместо кода, и контракт целиком в K.** Всё, во что упираются два среза и больше,
   лежит в K. Это схема (T001), чистая функция и DTO (T002), реестры и маршруты с документами
   ручек (T003), точки вызова в горячих файлах (T004). Срез заполняет **только свои новые файлы**
   и свою запись в заранее заведённом месте.
2. **Загрузчик — K глубины 2, а не срез с ребром «только вливание».** `course_theory(course)` читают
   семь срезов: генерация запроса, кнопки, гейты, откат, урок А, урок Б и вкладка. Им нужны поля
   T001 и функция T002. Есть три варианта:
   - (а) ребро «вливание после соседа» — вне формы §4, срезы стоят готовыми;
   - (б) одна K, в которой T001 + T002 + загрузчик — это L, а «больше M — резать»;
   - (в) K → K с `Почему не одна:`.

   Выбран (в), цена посчитана. Фаза K заканчивается на 116-й минуте вместо 94-й при c = 0. Но
   отказ T005 почти ничего не стоит (325 против 326 мин), потому что 13 из 20 срезов от T005 не зависят. В r1 шесть
   принятых срезов стояли и ждали вливания T013.
3. **Срез идёт по сценарию насквозь.** Срезов 20 ≥ 2K, поэтому деления по сторонам нет (§3.2 п. 5).
   Чтобы срез «сервер + клиент» укладывался в M, клиентский контракт не собран в отдельную K
   (в r1 это была T004). Каждый срез держит свой файл обёрток `utils/rung<Имя>.ts`, как уже сделано
   в проекте (`courseGoal.ts`, `topicKsa.ts`), и свои типы. Общий `utils/auth.ts` не трогает никто.
4. **Генерация остаётся разрезанной по швам конвейера, а не по режимам** (довод r1 в силе). Добавлен
   срез-вход T017: кнопка → ручка `regenerate-content` с `theory_mode` → `rung_modes.respond`
   (заглушку ставит T004) → конвейер. Это сценарий «автор нажал», и он идёт насквозь.
5. **Перенос — два параллельных среза, а не цепочка `[S]` из трёх.** T003 ставит каркас команды
   `migrate_rung_theory`: разбор флагов и вызовы `rung_theory_transfer.run`,
   `rung_theory_cleanup.remove_shells`, `backfill_course` и `export_journal`, которые пока
   заглушки. Перенос (T030) и оболочки с дозаполнением (T031) правят разные модули. Так
   критический путь сократился с 89 до 69 мин.
6. **`services.py` в `topic_content` остаётся одной цепочкой:** T004 (4 вызова) → T020 → T021 (стек).

## 3. Карта швов (`contracts.md`)

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| C1 | `TopicContent.carrier_purpose` (`theory`/NULL), инварианты R-2 в `clean()`/`save()` | T001 | T015 T018 T019 T020 T022 T028 T030 T031 |
| C2 | `TopicContent.topic` и `TopicContentGenerationError.topic` → `null=True` | T001 | T015 T018 T019 T022 T030 |
| C3 | `TopicContent.course` FK PROTECT, заполнение в миграции, `save()` берёт курс от темы или ступени | T001 | T005 T018 T019 T022 T029 T030 T031 |
| C4 | `section_type='approach_map'`, `TopicContentSection.understanding_step` (1…5/NULL), снимок состава версии R-8 `composition_snapshot` | T001 | T005 T014 T015 T020 T021 |
| C5 | `RungTheoryMigrationRecord` **в `topic_content/models.py`** (в `apps.py` ничего не добавляется); две миграции, номер берётся на вливании | T001 | T030 T031 |
| C6 | `rung_theory/types.py` (`CourseTheoryInputs`, `RungTheory`, `CourseTheory`), `needs.compute`, `versions.active_version`, `testing.fake_course_theory` (без БД) | T002 | T005 T014 T023 T025 T026 T027 |
| C7 | `rung_theory/service.course_theory(course) -> CourseTheory`, пакетный загрузчик | T005 | T012 T014 T017 T023 T025 T026 T027 |
| C8 | `GET /api/v1/courses/{c}/rung-theory`: маршрут-заглушка 501, строка доступа, заготовка документа ручки | T003 | T012 |
| C9 | Ручки R-30 (5 шт.) и импорт в носитель: маршруты-заглушки, строки доступа, заготовки документов | T003 | T019 T022 |
| C10 | Чтение теории ступени учеником: маршрут в `lesson/urls.py`, строка доступа, заготовка документа | T003 | T026 |
| C11 | Коды: `/problems/course-path-not-applicable` (`rung-material`, `topic-material`, `content-reading`), коды гейта `rung-theory-knowledge-missing`, `rung-theory-section-unmarked`, `rung-theory-outdated`, `rung-approach-map-missing`, выведение `reading-material-outdated` (R-24) | T003 | T018 T019 T023 T024 T029 |
| C12 | Конвейер: `generation/rung_pipeline.run(unit)`, `rung_request.build(unit, theory) -> MlRequest`, `rung_draft_writer.write(unit, draft, mode)`, `rung_billing.plan(unit, mode)`; DTO `RungUnit` (со снимком состава) и `RungTheoryDraft`; одна ветка в `generation/services.py` | T004 | T014 T015 T016 |
| C13 | Образец запроса и ответа `ml-llm` `kind=rung_theory`: один JSON-файл в обоих сервисах | T004 | T013 T014 |
| C14 | `topic_content/rung_rollback.on_material_change(tc, replaced_version_id)`: 4 вызова в `services.py`, заглушка повторяет прежнее поведение | T004 | T025 |
| C15 | `gates/rules_rung_theory.py`: 4 правила-заглушки, зарегистрированы с `bind_on_path(pipeline_v2=True)` | T004 | T023 |
| C16 | `WRITER_FILES` сторожа `check_topic_content_writes.py`: `rung_draft_writer.py`, `rung_material.py`, `rung_theory_transfer.py`, `rung_theory_cleanup.py` (это frozenset путей, отсутствие файла не ошибка) | T004 | T015 T019 T030 T031 |
| C17 | `theory_mode` в сериализаторе `regenerate-content`; ветка вида `rung_modes.respond(request, tc, mode)` (заглушка); на старом пути 422 `not-applicable` | T004 | T017 |
| C18 | Каркас `migrate_rung_theory` (`--dry-run` по умолчанию, `--apply`, `--course`, `--backfill-course`, `--export-journal`) и заглушки двух модулей | T003 | T030 T031 |

## 4. Задачи

Вес считается так: 10 мин × 1.6 (deep) × 1.5 (M). Ранг — HLFET с ребром «`[T]` → срезы истории».
**Форма приёмочных тестов.**
- **Django:** `@unittest.expectedFailure` на каждом методе AC (проект гоняет `manage.py test`).
  Данные создаются **внутри метода**, потому что ошибка в `setUp` под декоратор не попадает.
- **Jest:** `test.failing(...)`.
- **Playwright:** `test.fail()` в теле теста.
- **Кто снимает отметку.** Её снимает срез, на ветке которого тест начал проходить: unittest
  считает «unexpected success» провалом, и `check.sh` краснеет. Это первая проверка T006:
  тест-зонд с `expectedFailure`, который проходит, обязан вернуть ненулевой код у
  `manage.py test` на версии Django проекта.

Общий шаблон для всех `[V]`/`[S]`: тесты среза зелёные и **краснеют на откате кода среза**
(вывод `hold` приложен), отметки своих AC сняты там, где тест стал проходить, `check.sh` зелёный.

### Фаза K (T001–T004 стартуют сразу, T005 — после вливания T001 и T002)

- [ ] **T001 [K] Носитель теории: схема, миграции, инварианты, журнал** — deep, M, 24
  Контракт: C1–C5. Файлы: `topic_content/models.py`, `migrations/<N>_rung_theory_carrier.py`,
  `migrations/<N+1>_rung_theory_migration_record.py`, `topic_content/tests/test_carrier_invariants.py`,
  `topic_content/tests/test_migration_<N>_rung_carrier.py`. **Не трогает** `courses/models.py`
  (потолок 7138 строк) и `apps.py`.
  Приёмка: AC-14 (своими тестами). Готово-когда: `test_carrier_theory_requires_rung`,
  `test_carrier_topic_null_on_flag`, `test_course_filled_from_topic`, `test_migration_backward_restores_topic`
  зелёные и краснеют на откате `clean()`; `makemigrations --check` пуст.
  Тест-группа: content. Номер миграции берётся после голов шага 6 и переименовывается на вливании.
- [ ] **T002 [K] Пакет `rung_theory`: чистая функция состава** — deep, M, 24
  Контракт: C6. Файлы: `rung_theory/__init__.py`, `types.py`, `needs.py`, `versions.py`, `testing.py`,
  `AGENTS.md` (6 обязательных разделов `module-coverage`), `README.md`, `tests/test_knowledge_needs.py`,
  `tests/test_knowledge_versions.py`, `docs/engineering/module-tiers.json` (`rung_theory` на ярус 3:
  загрузчику T005 нужен `topic_content`), `docs/engineering/module-map.md` (пересобирается).
  Приёмка: AC-1, юнит-часть AC-2. Готово-когда: `test_progression_example_pr2` (K1 → 1; K2, K5 → 2;
  K6 → 3; K3 jit — нигде; ссылка 2 → 1), `test_entry_point_knowledge_excluded`, `test_role_override_moves_need`,
  `test_exactly_one_rung_per_knowledge`, `test_active_version_rule` зелёные, без БД, краснеют на откате `needs.py`.
  Тест-группа: graph.
- [ ] **T003 [K] Регистрация: коды, доступ, маршруты-заглушки, документы ручек, каркас команды** — обычный, M, 15
  Контракт: C8–C11, C18. Файлы: `config/response-codes.json`, `.claude/response-codes.json`,
  `config/api-problems.json`, `access_registry/registry.py`, `topic_content/urls.py`,
  `topic_content/views_rung_theory.py`, `views_rung_material.py`, `views_rung_import.py` (заглушки 501),
  `lesson/urls.py`, `lesson/views_rung_theory.py` (заглушка), `topic_content/rung_material.py`,
  `rung_theory_transfer.py`, `rung_theory_cleanup.py` (заглушки),
  `management/commands/migrate_rung_theory.py` (каркас), 8 заготовок `docs/api/endpoints/*.md`
  (заголовок `METHOD /path` и frontmatter, тело — «заполняет T0xx»),
  `docs/meta/process/rung-theory-migration-runbook.md` (заготовка), строки этих 9 документов в `docs/TAGS.md`,
  `topic_content/tests/test_rung_routes_access.py`.
  Готово-когда: `test_every_rung_route_resolves_501`, `test_every_rung_route_has_access_row` зелёные;
  `check_codes.py`, `check_api_doc_coverage.py`, `check_docs_index.py` зелёные; `migrate_rung_theory --dry-run`
  выходит с 0. Тест-группа: content.
  *Почему не одна с T004:* реестры и маршруты механичны (Sonnet). Хуки в горячих файлах требуют суждения (Opus).
- [ ] **T004 [K] Точки вызова в горячих файлах** — deep, M, 24
  Контракт: C12–C17. Файлы: `generation/services.py` (одна ветка), `generation/rung_pipeline.py`,
  `rung_request.py`, `rung_draft_writer.py`, `rung_billing.py` (заглушки и DTO), `topic_content/services.py`
  (только 4 вызова C14), `topic_content/rung_rollback.py` (заглушка), `topic_content/serializers.py`
  (`theory_mode`), `topic_content/views.py` (ветка `rung_modes.respond` в `regenerate-content`),
  `topic_content/rung_modes.py` (заглушка), `gates/registry.py`, `gates/rules_rung_theory.py` (заглушки),
  `scripts/check_topic_content_writes.py` (`WRITER_FILES`), образец C13 в
  `django-api/courses/topic_content/generation/fixtures/rung_theory_ml.json` и `ml-llm/tests/fixtures/rung_theory_ml.json`,
  `topic_content/tests/test_rung_hooks_content.py`, `generation/tests/test_rung_pipeline_stub.py`,
  `course_pipeline/tests/test_rules_rung_theory_registry.py`.
  Готово-когда: `test_hooks_keep_old_behaviour` (старые тесты `services.py` зелёные), `test_theory_mode_old_path_422`,
  `test_rung_rules_bound_only_on_flag`, `test_pipeline_stub_roundtrip_c13` зелёные.
  Тест-группа: content, saga. Линза ревью: «в заглушках нет логики, сигнатуры хватит срезам».
- [ ] **T005 [K] Загрузчик курса `course_theory(course)`** — обычный, M, 15 · Зависит от: T001, T002
  *Почему не одна:* нужны поля T001 и функция T002, а слитая K вышла бы размера L. Ребро «только вливание»
  (r1) хуже: 7 срезов стояли бы готовыми. Отказ T005 стоит 0…+4 мин (`sim.py`, force).
  Контракт: C7. Файлы: `rung_theory/loader.py`, `rung_theory/service.py`, `rung_theory/tests/test_knowledge_loader.py`,
  `rung_theory/README.md` (раздел загрузчика). Готово-когда: `test_loader_query_count_flat` (`assertNumQueries`
  не растёт с числом ступеней), `test_state_lag_from_snapshot`, `test_course_theory_matches_fake` зелёные.
  Тест-группа: graph.

### Приёмочные тесты `[T]` (старт в окне K, зависят только от `contracts.md` и спеки)

| Задача | История | AC | Вес | Файлы | Группа |
|---|---|---|---|---|---|
| T006 | US1 состав, «Контент», генерация, деньги | AC-2, AC-3, AC-6, AC-8, AC-19, AC-22 | M 15 | `courses/tests/acceptance/step8/us1/test_content_generation.py`, `services/frontend/tests/e2e/step8/rungContent.spec.ts` | content |
| T007 | US2 материал ступени без темы | AC-4, AC-15, AC-16, AC-17, AC-18 | M 15 | `…/us2/test_topic_content_access.py`, `e2e/step8/rungEditor.spec.ts` | content |
| T008 | US3 гейты и откат | AC-9, AC-20, AC-21 | S 10 | `…/us3/test_gate_rules.py` | saga |
| T009 | US4 уроки и трек | AC-12 | S 10 | `…/us4/test_lesson_rung.py` | lessons |
| T010 | US5 структура и окно ступени | AC-10, AC-11 | S 10 | `…/us5/test_structure_regen.py`, `e2e/step8/rungModal.spec.ts` | structure, ui |
| T011 | US6 перенос | AC-5, AC-13 | S 10 | `…/us6/test_migrate_command.py` | platform |

Все `[T]` выполняет `implementer` (обычный). Методы называются `test_ac<N>_<что>`. AC, который
держат несколько срезов, режется на методы по швам (AC-3: `test_ac3_generate_writes_sections_by_c`,
`test_ac3_prompt_step4_question_rule`, `test_ac3_button_starts_generation`). Каждый метод снимает
тот срез, на котором он позеленел. Ревью: «каждый AC покрыт, тест бьёт обе стороны, данные
создаются в методе». AC-7 (качество вживую) не тест: это приёмка US1 на `cp-*`.

### Веер (стартует от **влитых** предков, стека нет, кроме T020 → T021)

**US1: состав, «Контент», генерация, деньги**
- [ ] **T012 [V] «Контент» по ступеням: ручка `rung-theory` и вкладка** — обычный, M, 15 · T003 T005
  Файлы: `views_rung_theory.py` (тело), `docs/api/endpoints/course-rung-theory.md` (тело), `topic_content/tests/test_rung_theory_endpoint.py`,
  `frontend/.../tabs/RungContentTab.tsx` (новый), `tabs/ContentTab.tsx` (ветка по флагу), `utils/rungTheory.ts`, `types/rungTheory.ts`,
  `__tests__/components/RungContentTab.test.tsx` · Приёмка: AC-2, AC-22 (показ) · Готово-когда: `test_rung_theory_five_roles`,
  `test_rung_theory_states_match_composition`, jest `renders six rung states`, `old course keeps topic tab` · Группа: content.
- [ ] **T013 [V] Промпт теории ступени в `ml-llm`** — обычный, M, 15 · T004
  Файлы: `ml-llm/app/prompts/topic_content/plan_system_rung_theory.md`, `text_system_rung_theory.md`, схема ответа
  `kind=rung_theory`, `ml-llm/tests/test_topic_content_rung_theory_prompt.py` · AC-3 (форма) · Готово-когда:
  `test_rung_theory_response_matches_c13_sample`, `test_step4_has_question_and_rule` · Группа: content.
- [ ] **T014 [V] Запрос генерации: единица, план, режимы** — обычный, M, 15 · T004 T005
  Файлы: `generation/units.py`, `plan.py`, `dispatch.py` (+ читатели :354/:360), `rung_request.py` (тело),
  `generation/tests/test_rung_theory_generate.py` · AC-3, AC-6 (только `Lag`), AC-19 (блок карты) ·
  Готово-когда: `test_generate_sections_by_c_and_map`, `test_complete_only_lag_readonly_accepted`, `test_map_only_map`,
  `test_ref_in_context`, `test_step4_two_lexical_nodes` · Группа: content.
- [ ] **T015 [V] Запись черновика и слияние под замком** — deep, M, 24 · T001 T004
  Файлы: `generation/rung_draft_writer.py` (тело), `generation/tests/test_rung_theory_merge.py` · AC-3, AC-6, AC-19 ·
  Готово-когда: `test_snapshot_r8_per_mode`, `test_complete_copies_active_version_under_lock`,
  `test_concurrent_edit_no_lost_sections`, `test_nothing_to_do_200_no_unit`, `test_topic_null_course_set` · Группа: content.
- [ ] **T016 [V] Деньги и автопуть** — deep, M, 24 · T004
  Файлы: `generation/rung_billing.py` (тело), `course_pipeline/auto_pipeline.py` (**общий с шагом 6**),
  `generation/tests/test_rung_theory_billing.py`, `course_pipeline/tests/test_auto_pipeline_rung.py` · AC-8 ·
  Готово-когда: `test_reserve_ge_fact_each_mode`, `test_zero_calls_without_click`, `test_autopath_never_complete` ·
  Группа: billing, saga. Цена считается по `RungUnit` (C12), поэтому T005 не нужна.
- [ ] **T017 [V] Кнопки генерации и ответ ручки по режимам** — обычный, M, 15 · T003 T004 T005
  Файлы: `topic_content/rung_modes.py` (тело), `topic_content/tests/test_rung_modes_endpoint.py`,
  `frontend/.../content/RungTheoryActions.tsx`, `utils/rungTheoryGeneration.ts`, `__tests__/components/RungTheoryContentButtons.test.tsx` ·
  AC-22 (кнопки), AC-6 («нечего делать») · Готово-когда: `test_modes_generate_complete_map_dispatch`,
  `test_nothing_to_do_returns_200`, jest `pack button shows count`, `rereads after response` · Группа: content.

**US2: материал ступени без темы**
- [ ] **T018 [V] Доступ, отказы по пути, граф курса без темы** — deep, M, 24 · T001 T003 T004
  Файлы: `access_registry/preflight.py`, `topic_content/views.py` (проверки курса :1035/:1149/:1206, `topic_id` :270,
  отказы R-31), `task_classes/views.py` (отказ `content-topics`), `course_graph_editor/read.py`,
  `access_registry/tests/test_preflight_rung_material.py`, `courses/tests/test_pipeline_path_refusals.py`,
  `course_graph_editor/tests/test_read_without_topic.py` · AC-4, AC-13 (предполётная), AC-15, AC-17 ·
  Готово-когда: `test_five_roles_each_route`, `test_topic_route_on_flag_422`, `test_old_material_same_course`,
  `test_graph_keys_rung_not_none` · Группа: platform, structure, content.
  `views.py` правит и T004 (ветка `regenerate-content`), поэтому ребро T004 → T018.
- [ ] **T019 [V] Материал ступени в редакторе: ручки R-30 и `ContentEditorDrawer`** — deep, M, 24 · T001 T003
  Файлы: `topic_content/rung_material.py` (тело, писатель), `views_rung_material.py` (тело), 4 тела
  `docs/api/endpoints/course-topic-content-*.md`, `topic_content/tests/test_rung_material_endpoints.py`,
  `frontend/.../content/ContentEditorDrawer.tsx` (ветка адресов), `utils/rungMaterial.ts`,
  `__tests__/components/ContentEditorDrawerRung.test.tsx` · AC-17 (R-30), AC-18 · Готово-когда:
  `test_create_theory_under_rung_lock`, `test_versions_switch_by_group`, `test_name_and_place_from_carrier`,
  jest `drawer uses course routes on flag`, `occ conflict keeps unsaved` · Группа: content.
- [ ] **T020 [S] Разделы: карта подхода и знания раздела** — обычный, M, 15 · T001 T004
  *Почему не срез:* `topic_content/services.py` (2 703 строки) — один владелец за раз.
  Файлы: `topic_content/services.py` (создание и правка раздела, читатели :606/:835/:1416), `topic_content/serializers.py`
  (поля раздела), `topic_content/tests/test_section_rules_rung.py`, `frontend/.../content/SectionsList.tsx`,
  `content/SectionKnowledgePicker.tsx` (новый), `__tests__/components/SectionKnowledgePicker.test.tsx` · AC-16, AC-18 (знания) ·
  Готово-когда: `test_second_approach_map_422_already_taken`, `test_map_on_backing_not_applicable`,
  `test_knowledge_ids_must_be_course_knowledge`, jest `picker lists course knowledge` · Группа: content.
- [ ] **T021 [S] Форк и пересборка без потери разметки** — обычный, M, 15 · T001; T020 (стек)
  Файлы: `topic_content/services.py` (`_carry_…` :1069–1146, форк :2332/:2350, пересборка :1637/:1942),
  `topic_content/tests/test_fork_rebuild_markup.py` · AC-16 · Готово-когда: `test_fork_keeps_knowledge_and_step_both_paths`,
  `test_rebuild_keeps_map` · Группа: content. `hold` откатывает только диапазоны строк T021, вызовы T004 не трогает.
- [ ] **T022 [V] Импорт в носитель и вставные вопросы без темы** — обычный, M, 15 · T001 T003
  Файлы: `topic_content/passthrough.py`, `views_rung_import.py` (тело), `docs/api/endpoints/course-topic-content-populate.md` (тело),
  `topic_content/embedded_items/services.py` (проверки IE-9/IE-10 здесь, **не** в `models.py`), `topic_content/coverage/check.py`,
  `coverage/gate.py`, `topic_content/tests/test_import_without_topic.py`, `embedded_items/tests/test_embedded_without_topic.py`,
  `coverage/tests/test_coverage_knowledge_rung.py` · AC-4, AC-18 (импорт и вопрос) · Готово-когда:
  `test_import_topic_null_group_from_carrier`, `test_question_foreign_knowledge_refused`, `test_coverage_by_course` ·
  Группа: documents, banks, content.

**US3: гейты и откат**
- [ ] **T023 [V] Четыре правила гейта 2** — обычный, M, 15 · T004 T005
  Файлы: `gates/rules_rung_theory.py` (тела), `course_pipeline/tests/test_rules_rung_theory.py` · AC-9 ·
  Готово-когда: `test_knowledge_without_section_blocker`, `test_section_without_knowledge_warning`, `test_lag_warning`,
  `test_no_map_blocker`, `test_fork_without_section_blocker` · Группа: saga.
- [ ] **T024 [V] Снятие старых правил на флаге и `ksa-task-class-inadequate`** — обычный, M, 15 · T003
  Файлы: `graph_invariants/structure_gate.py`, `task_classes/readiness.py`, `gates/rules_content.py`,
  `gates/rules_topic_content.py`, `gates/facts.py`, `gates/rules_structure.py` (`_ksa_task_class_inadequate*` :662–772,
  **общий с шагом 6**), `task_classes/gate_rules.py`, `course_pipeline/tests/test_gate2_flag_rules.py`,
  `task_classes/tests/test_gate_rules_flag.py` · AC-9, AC-21 · Готово-когда: `test_old_rules_silent_on_flag`,
  `test_old_rules_fire_without_flag`, `test_ksa_inadequate_on_flag_by_rung` · Группа: saga.
- [ ] **T025 [V] Откат гейта 2 по условию** — обычный, M, 15 · T004 T005
  Файлы: `topic_content/rung_rollback.py` (тело), `course_pipeline/gating.py`, `saga/gate_backing.py` (**общий с шагом 6**;
  `saga` стоит на ярусе 2 и **не импортирует** `rung_theory`, поэтому решение передаётся аргументом из `rung_rollback`),
  `saga/tests/test_reopen_rung_theory.py`, `topic_content/tests/test_rung_rollback.py` · AC-20 ·
  Готово-когда: `test_rollback_only_when_coverage_lost`, `test_complete_approval_no_rollback` · Группа: saga, content.

**US4: уроки и трек**
- [ ] **T026 [V] Урок А по ступени и «Опирается на»** — обычный, M, 15 · T003 T005
  Файлы: `lesson/mode_a/services.py` (:101–176, :238, проверка `'A'` на флаге; **общий с шагом 6**),
  `topic_content/lesson_modes.py`, `lesson/serializers.py` (`refs`), `lesson/views_rung_theory.py` (тело),
  `docs/api/endpoints/lesson-rung-theory.md` (тело), `lesson/mode_a/tests/test_mode_a_rung.py`,
  `frontend/.../mode-a/LessonModeA.tsx`, `mode-a/RungRefs.tsx`, `utils/lessonRungTheory.ts`, `__tests__/components/LessonModeARefs.test.tsx` ·
  AC-12 (урок А) · Готово-когда: `test_mode_a_by_rung_on_flag`, `test_refs_point_to_first_rung`,
  `test_student_reads_theory_by_course_access`, jest `refs link to rung theory` · Группа: lessons.
- [ ] **T027 [V] Урок Б, контекст генерации задач, банк диагностики, трек** — обычный, M, 15 · T005
  Файлы: `rung_theory/sections.py` (`sections_for_knowledge`), `dialogue/material_b.py`, `generation/context.py`,
  `diagnostic_bank/payload.py`, `track_manage/services.py`, `track_manage/planner.py`, `dialogue/tests/test_material_b_rung.py`,
  `track_manage/tests/test_track_rung_theory.py`, `diagnostic_bank/tests/test_payload_rung.py` · AC-12 (урок Б, трек) ·
  Готово-когда: `test_material_b_takes_needed_rungs_theory_and_map`, `test_task_gen_context_from_rungs`,
  `test_diag_payload_rung_sections`, `test_track_on_flag_no_reading_class` · Группа: lessons, graph, banks.

**US5: структура и окно ступени**
- [ ] **T028 [V] Перегенерация структуры** — deep, M, 24 · T001
  Файлы: `task_classes/rung_layout.py`, `structure_gen/skeleton.py`, `task_classes/rung_layout_db.py` (:503, :706, :1137, :1677),
  `task_classes/rung_regen.py`, `task_classes/tests/test_rung_regen_theory.py` · AC-10 (перегенерация) ·
  Готово-когда: `test_regen_carries_theory_by_key`, `test_skeleton_no_content_reading_on_flag`; `check_course_structure_writes.py`
  зелёный · Группа: banks. **Общий с шагом 6 каталог** `course_structure/` и `task_classes/`.
- [ ] **T029 [V] Окно ступени без «Тип» и «+ Теория», удаление с теорией → парковка** — обычный, M, 15 · T001 T003
  Файлы: `task_classes/services.py` (:173, :786, :1893, ветка R-48; **общий с шагом 6**), `course_structure/deletion.py`,
  `topic_content/parent_deletion.py`, `course_structure/tests/test_deletion_parking.py`, `task_classes/tests/test_content_reading_refusal.py`,
  `frontend/.../structure/TaskClassModal.tsx` (**общий с шагом 6**), `structure/TopicTreePanel.tsx`, текст окна удаления,
  `__tests__/components/TaskClassModalRung.test.tsx` · AC-10 (удаление), AC-11 · Готово-когда: `test_content_reading_on_flag_422`,
  `test_delete_rung_with_approved_theory_parks`, jest `no type field on flag`, `no add theory button` · Группа: banks, structure.

**US6: перенос**
- [ ] **T030 [V] Перенос версий: `rung_theory_transfer`, журнал, отказы по курсу** — deep, M, 24 · T001 T003 T004
  Файлы: `topic_content/rung_theory_transfer.py` (тело), `management/commands/migrate_rung_theory.py` (только отчёт `--dry-run`),
  `topic_content/tests/test_rung_theory_transfer.py` · AC-5 (перенос, идемпотентность, ноль вызовов модели, отказ курса
  с учеником или опубликованного) · Готово-когда: `test_apply_moves_versions_bytes_equal`, `test_second_apply_zero_changes`,
  `test_dry_run_writes_nothing`, `test_refuses_course_with_student`, `test_no_llm_ledger_rows` · Группа: content.
- [ ] **T031 [V] Оболочки, `--backfill-course`, выгрузка журнала, раннбук** — deep, M, 24 · T001 T003 T004
  Файлы: `topic_content/rung_theory_cleanup.py` (тело; удаление оболочки идёт **через дверь** `course_structure`,
  `deletion.py` не правится, а если правка нужна — доклад), `docs/meta/process/rung-theory-migration-runbook.md` (тело),
  `topic_content/tests/test_rung_theory_cleanup.py`, `topic_content/tests/test_backfill_content_course.py` · AC-5 (оболочки,
  `Document.task_class` в журнале, выгрузка), AC-13 (`course IS NULL` = 0) · Готово-когда: `test_empty_shell_removed_with_snapshot`,
  `test_protected_shell_kept_with_reason`, `test_backfill_fills_null_course`, `test_export_rows_equal_count` · Группа: content.
  `migrate_rung_theory.py` правит только T030 (отчёт), T031 работает в своём модуле. Флаги заведены в T003.

**Хвост**
- [ ] **T032 [H] Хвост и документы замысла** — обычный, M, 15 · все `[V]`/`[S]`
  Файлы: `docs/INDEX.md`, `docs/TAGS.md` (поднять `updated` у документов, тела которых заполнили срезы), журнал проекта,
  `ADR-099` (D9, О-6), журнал концепции (ответы ВЛ 23.11), строка шага 8 в плане, находки «хвост» дословно,
  сверка полного списка читателей по теме (риск 3 спеки: `grep` из §10 п. 3 против `Файлы:` всех задач).
  Готово-когда: `check_docs_index.py`, `check_doc_links.py` зелёные.

## 5. Тесты и документы: где что пишется

- **Тесты среза** лежат в каталоге модуля среза (`check_test_location`: тесты подмодуля — в подмодуле).
  Приёмочные лежат в `courses/tests/acceptance/step8/us<N>/`: они импортируют несколько пакетов, поэтому
  это интеграционные тесты и их место наверху законно. Общих `conftest`/фикстур нет, проект на `unittest`.
  Данные строятся в методе через существующие `courses/tests/_course_fixtures.py`, без DB-фикстур K.
  Так `[T]` не зависит от кода K.
- **Имена тестов подобраны под правила `test_registry`** (`simF2A_r2/cls.py` на `test_registry_base.py`
  оценщика): ни одно не попадает в `core`, поэтому `docs/engineering/test-registry.json` не трогает никто.
  Если срезу нужно имя вне правил, это доклад, а не правка реестра.
- **Документы ручек:** заготовки с frontmatter и строки `TAGS.md` делает T003, потому что новый маршрут
  без описания краснит `check_api_doc_coverage`. Тело заполняет срез ручки, frontmatter он **не трогает**,
  иначе строка `TAGS.md` разойдётся с `updated` и покраснеет `check_docs_index`. Поднимает `updated` T032.
- **Документы модуля:** `rung_theory/AGENTS.md` и `README.md` пишет T002, раздел загрузчика дописывает T005
  (между ними есть ребро). Общие реестры документов (`INDEX`, журнал, ADR, концепция) правит только T032.

## 6. Карта владения: горячие и скрытые общие файлы

| Файл | Владелец (порядок) | Почему без конфликта / что делать |
|---|---|---|
| `topic_content/services.py` | T004 (4 строки) → T020 → T021 (стек) | цепочка по рёбрам |
| `topic_content/views.py` | T004 (ветка `regenerate-content`) → T018 | ребро T004 → T018 (`Зависит от: T001 T003 T004`) |
| `topic_content/serializers.py` | T004 → T020 | ребро |
| `topic_content/models.py` | только T001 | IE-9/IE-10 вынесены в `embedded_items/services.py` |
| `generation/services.py` | только T004 | |
| `utils/auth.ts` | никто | обёртки в `utils/rung*.ts` своих срезов |
| реестры кодов, `api-problems`, `access_registry/registry.py` | T003 | **общие с шагом 6**: на rebase объединение строк делает координатор, `check_codes.py` |
| `gates/registry.py` | T004 | **общий с шагом 6** |
| `gates/rules_structure.py` | T024 | **общий с шагом 6**, идёт в конце веера |
| `docs/engineering/test-registry.json` | никто | имена тестов под правила (§5) |
| `docs/engineering/module-tiers.json` | T002 | **общий с шагом 6** (`learning_process`, `course_bank`): объединение на rebase |
| `rung_theory/AGENTS.md`, `README.md` | T002 → T005 | `check_module_coverage` (порог 300 строк), `check_module_readme` |
| `docs/engineering/module-map.md` | генерируемый, `shared` | любой новый импорт меняет счётчики стрелок. Не правится руками: координатор на rebase выполняет `gen_module_map.py`, и коммит идёт вместе с вливанием |
| `docs/TAGS.md` | T003 → T032 | срезы frontmatter не трогают |
| `scripts/check_topic_content_writes.py` | T004 | все 4 писателя внесены заранее |
| `courses/models.py`, `courses/apps.py` | **никто** | потолок 7138 строк в `loc-budget.json`; модель журнала лежит в `topic_content/models.py` |
| миграции `courses` | T001 | **общая цепочка с шагом 6**: номер на вливании, переименование теста миграции |
| `TaskClassModal.tsx`, `task_classes/services.py`, `course_structure/deletion.py` | T029 | **общие с шагом 6** |
| `course_pipeline/auto_pipeline.py` | T016 | **общий с шагом 6** |
| `saga/gate_backing.py` | T025 | **общий с шагом 6**; ярус 2, импорт `rung_theory` запрещён |
| `lesson/mode_a/services.py` | T026 | **общий с шагом 6** (удаление режимов урока) |

Пересечение `views.py` у T004 и T018 закрыто ребром T004 → T018. Оно есть в `plan.py`, и все цифры
посчитаны с ним. Детерминированное расписание от него не меняется: T018 по рангу и так стартует после вливания T004.

## 7. Расписание

### N = 4, R = 3, c = 6, детерминированно (p = 0, `trace.py`), вливания по одному

| Задача | Слот | Старт | Сдана | Влита | | Задача | Слот | Старт | Сдана | Влита |
|---|---|---|---|---|---|---|---|---|---|---|
| T001 K | 1 | 0 | 24 | 38 | | T016 | 1 | 59 | 83 | 116 |
| T002 K | 2 | 0 | 24 | 44 | | T018 | 3 | 62 | 86 | 122 |
| T004 K | 3 | 0 | 24 | 50 | | T019 | 2 | 65 | 89 | 128 |
| T007 T | 4 | 0 | 15 | 29 | | T030 | 4 | 74 | 98 | 134 |
| T003 K | 4 | 15 | 30 | 56 | | T031 | 1 | 83 | 107 | 140 |
| T006 T | 1 | 24 | 39 | 62 | | T012 | 3 | 86 | 101 | 146 |
| T010 T | 2 | 24 | 34 | 68 | | T013 | 2 | 89 | 104 | 152 |
| T011 T | 3 | 24 | 34 | 74 | | T014 | 4 | 98 | 113 | 158 |
| T008 T | 4 | 30 | 40 | 92 | | T017 | 3 | 101 | 116 | 164 |
| T009 T | 2 | 34 | 44 | 98 | | T021 S | 2 | 104 | 119 | 170 |
| T028 | 3 | 38 | 62 | 104 | | T022 | 1 | 107 | 122 | 176 |
| T005 K | 1 | 44 | 59 | 80 | | T023 | 4 | 113 | 128 | 182 |
| T015 | 4 | 50 | 74 | 110 | | T024 | 3 | 116 | 131 | 188 |
| T020 S | 2 | 50 | 65 | 86 | | T025 | 2 | 119 | 134 | 194 |
| | | | | | | T026 | 1 | 122 | 137 | 200 |
| | | | | | | T027 | 4 | 128 | 143 | 206 |
| | | | | | | T029 | 3 | 131 | 146 | 212 |
| | | | | | | T032 H | 1 | 212 | 227 | **241** |

Что видно из таблицы.
- **Узкое место — очередь вливаний.** Все срезы сданы к 146-й минуте, а последний влит на 212-й:
  32 × 6 = 192 мин работы координатора подряд.
- **Варианты очереди:**
  - c = 0: конец на 173-й минуте;
  - вливания партией (цена 4 + 2n, `task_pairs.py merge` на N веток): **196**;
  - N = 3 по одному: 247;
  - N = 3 партией: 230;
  - N = 2: 318 при любой очереди, там узкое место — слоты.
- **С шумом и отказами** (`sim.py`) очередь даёт +26 мин к медиане при N = 4 (300 → 326) и +11 при N = 2 (486 → 497): работа
  растягивается, и вливания расходятся во времени сами.
- **Совпадения с шагом 6 стоят в конце веера:** T024, T025, T026, T029, а также T016 и T028 в середине.
  К этому времени шаг 6 скорее всего уже влил свои правки тех же файлов.

### Сценарии (`sim.py`, медиана / p90, мин)

| | p = 0.25 | p = 0.43 | p = 0.61 |
|---|---|---|---|
| N = 4, c = 6, по одному | 302 / 325 | **326 / 354** | 356 / 387 |
| N = 4, c = 6, партией | 289 / 315 | 320 / 348 | 351 / 382 |
| N = 4, c = 3 | 278 / 301 | 311 / 337 | 343 / 371 |
| N = 3, R = 2, c = 6 | 342 / 369 | 377 / 405 | 421 / 452 |
| **N = 2, R = 2, c = 6** | 445 / 481 | **497 / 539** | **559 / 600** |
| N = 5, R = 4, c = 6 | 294 / 313 | 310 / 331 | 327 / 352 |
| N = 4: T004 ×3 и отказ | — | 370 / 417 | 396 / 449 |
| N = 4: T003 и T004 ×3, оба с отказом | — | 384 / 426 | 414 / 457 |
| N = 2: T004 ×3 и отказ | — | 550 / 599 | 611 / 658 |
| N = 2: T003 и T004 ×3, оба с отказом | — | 582 / 626 | 646 / 694 |
| N = 4: отказ T005 / T001 / обеих | — | 325 / 331 / 333 | — |
| N = 4 и N = 2: T004 заранее разрезана на a/b (33 задачи; прогон до ребра T004 → T018) | — | 324 / 504; при ×3 и отказе 342 / 539 | 355 / 565 |

Запасной разрез T004 не беру по умолчанию: в базовом случае он почти не помогает (324 против 322 до ребра T004 → T018) и стоит +$8. Беру его по
правилу: **если ревью T004 вернуло задачу или дифф больше 300 строк, координатор режет её по шву
«генерация (C12, C13, C16)» | «`topic_content` и гейты (C14, C15, C17)»**. Потребители уже разделены
по этим швам в `Зависит от:`.

## 8. Ревью, вливание, CI, приёмка

1. **Очередь вливаний — главный рычаг после самого плана.** Во-первых, механику делает скрипт:
   `task_pairs.py merge` (rebase, `--ff-only`, пересборка `module-map.md`, объединение строк реестров).
   Координатор только подтверждает, и c падает с 6 до ~3 (311 против 326). Во-вторых, всё годное
   вливается **партией** (320; детерминированно 196 против 241). Владение файлами делает партию
   безопасной: пересечений `Файлы:` без пути нет. Порядок внутри партии — по рангу.
2. **CI и `cancel-in-progress`.** В `cicd.yml` группа задана как `cicd-${{ github.ref }}`, флаг
   `cancel-in-progress: true`, запуск на пуш любой ветки. Пуши шага 6 в ту же ветку плана отменяют
   наши прогоны, а наши — их. Поэтому партия (3–4 вливания) пушится в **свою ссылку
   `ci/s8-b<NN>`**: у неё своя группа concurrency, и её никто не отменит. Ветка плана
   перематывается `--ff-only` на проверенный коммит после зелёного. Красная партия делится пополам.
   Прогон с `only_groups` по `Тест-группа:` здесь мало что даёт: отпечаток грубый, любая правка
   `services/` сбрасывает все группы django. Так что на `content`/`saga` идёт полный django. Около
   9–10 партий по 15–28 мин на 3 раннерах, которые делятся с шагом 6. **Это общий ресурс: нужен
   один координатор CI для обеих фич.**
3. **Ревью.** Пул R = K − 1. Линзы:
   - K: «хватит ли срезам»; для T004 ещё «нет логики в заглушках»;
   - `[T]`: «AC покрыт, тест бьёт обе стороны, данные в методе»;
   - срез: логика, `Контракт:`, `Готово-когда:`.

   Механику (`check.sh`, `hold`, пробное слияние) ревьюер не повторяет. Повторное ревью идёт по
   диффу доработки, кругов не больше двух.
4. **Ворота вливания.** Срез вливается после своих предков и своей `[T]`. Ребра «только вливание» нет.
5. **Приёмка по истории, как только влиты её срезы.** US6 (перенос) и US5 идут первыми. US1 — с AC-7
   вживую на `cp-*` на двух курсах. Playwright (AC-11, AC-18, AC-22) — на `cc-*`.

## 9. Конфликты и простой

1. **Шаг 6 работает одновременно.** Общие файлы: миграции (T001); коды, доступ, `module-tiers` (T003, T002);
   реестр гейтов (T004); `rules_structure.py` (T024); `auto_pipeline.py` (T016); `saga/gate_backing.py` (T025);
   `mode_a/services.py` (T026); `TaskClassModal.tsx`, `task_classes/services.py`, `course_structure/` (T028, T029);
   `generation/context.py` (T027).
   - **Мера:** `task_pairs.py` читает `Файлы:` **обоих** `tasks.md`, а правило базы «задачи с общими
     файлами одновременно не берутся» действует между фичами.
   - Для K (T001, T002, T003, T004) это может значить ожидание. Тогда K берёт номер миграции и строки
     реестров на rebase, а не ждёт.
   - Это **главный источник простоя, который план сам не снимает**. Модель его не учитывает.
2. **Очередь вливаний.** Её решает §8 п. 1.
3. **T004 широкая и стоит в начале.** ×3 и отказ дают +44 мин при N = 4 и +53 при N = 2. Мера —
   запасной разрез (§7).
4. **Смысловые копии.** «Действующая версия», состав и поиск разделов по знаниям живут только в
   `rung_theory` (T002, T005, T027). Ревьюеру T014, T026, T027 соседние ветки называются по имени.
5. **`hold` на T020/T021.** Откатывать только диапазоны строк среза, вызовы T004 оставить.
6. **Полный прогон `courses` идёт 30 мин.** Исполнитель гоняет свои тесты и группу, полный прогон
   делает CI партии.
7. **Строка `TAGS.md` и `updated`.** Срез, поднявший `updated`, краснит `check_docs_index`. Запрет
   записан в `Готово-когда:` для всех тел документов.

## 10. Прогноз против бейзлайна и сегодняшнего процесса

| | Бейзлайн (оценщик) | r1 (в модели оценщика) | **r2, N = 4** | **r2, N = 2** |
|---|---|---|---|---|
| Длительность, p = 0.43 | ~10–10.5 ч | 6.9 ч (412) | **5.4 ч (326)** | **8.3 ч (497)** |
| Длительность, p = 0.61 | — | 7.5 ч (448) | 5.9 ч (356) | 9.3 ч (559) |
| Одновременно занято | 2.1–2.4 из 4 | 2.85–2.95 | 2.87–2.96 из 4 | 1.77 из 2 |
| Запусков исполнителя / ревью | — | ~66 / 66 | 49 / 49 (p = 0.43) | то же |
| Цена | ~$133 | ~$240 (у меня $271) | **$180 / $213** | то же |

**Качество.**
- «Пересечение с соседней задачей» (16 из 19 отказов при 4 исполнителях) внутри фичи сводится к
  `views.py` T004 → T018, а это ребро.
- «Расхождение сторон» держит срез насквозь (обе стороны у одного исполнителя) и `[T]`, который бьёт
  обе стороны.
- «Незакрытый пункт» держат имена тестов в `Готово-когда:`.
- «Тест, который ничего не держит», ловит `hold`.
- Остаётся пересечение с шагом 6.

Цена выше бейзлайна в 1.35–1.6 раза. Из неё $73 — ревью (49 × $1.5), $75 — deep. Дальше цену снижает
доля доработок p, а не нарезка: при p = 0.25 выходит $151.

## 11. Замечания к процессу (`design.md`)

1. **Очередь вливаний нужно ввести в §7 (оценка времени).** Нижняя граница — c × число вливаний.
   При 32 × 6 = 192 мин это больше W/K + S в идеальном случае. В §8 базы нужно добавить
   `task_pairs.py merge --batch`.
2. **CI партии идёт на своей ссылке `ci/<фича>-b<NN>`,** иначе `cancel-in-progress` гасит соседей.
3. **K глубины 2 под загрузчик** — допустимая форма, которая заменяет ребро «только вливание».
   Это нужно назвать в §3.2 п. 3 как пример `Почему не одна:`.
4. **Скрытые общие файлы проекта** (реестр тестов, ярусы, индекс документов, покрытие ручек,
   потолок строк) нужно читать в пробе плана из `pair-rules.txt` проекта. Иначе их найдёт
   pre-commit у второго среза.
5. **Отметки xfail:** у `unittest` строгость даёт `expectedFailure` (unexpected success считается
   провалом), данные создаются в методе. Формулировку `strict=True` в §3 шаг 5 нужно заменить на
   «по раннеру проекта».
