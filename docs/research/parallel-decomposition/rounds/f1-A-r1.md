# Фича 1 (шаг 6 «Наставника»), команда A, круг 1: разложение и план

Дата 2026-11-24. Процесс — `design.md` (сведённый). Позиция команды A: ширина — от контрактов и
вертикальных срезов; зависимость «по коду» заменена зависимостью «по контракту». Код и документы
читались только на базовом коммите `06a0bbdf4`. Модель плана и проверки — скрипты в
`/tmp/claude-1000/-home-rustam-develop-simbioz-team-muagba-pro/e280ef6f-cbe4-4a58-b39a-164383171093/scratchpad/f1A/`
(`plan.py` — граф, W, S, P и Монте-Карло; `sched.py` — расписание HLFET; `files.py` — карта
владения; проверка «пересечение `Файлы:` без пути в графе» даёт 0).

## 0. Итог в цифрах

| Мера | Значение |
|---|---|
| Задач | 66: 4 `[K]`, 11 `[T]`, 44 `[V]`, 6 `[S]`, 1 `[H]`; из них `deep` — 14 |
| W (сумма весов пробы §5) | 995 вес-мин |
| S (критический путь) | 104 вес-мин: T001 → T029 → T038 → T044 → T045 → T066 |
| P = W/S | 9.6 — норма для K = 4 (≥ 8), предупреждение для K = 5 (< 10, но выше 2K−1) |
| Фаза К | 4 задачи, глубина 1, 78 вес-мин = 8% W (норма ≤ 20%) |
| Готово к старту в момент 0 | 26 задач (4 К, 11 `[T]`, 11 независимых срезов) — окно фазы К не простаивает |
| Расписание HLFET без доработок | K = 4: 290 мин, занятость 4.0 до 280-й минуты; K = 5: 240 мин |
| Ожидание с доработками (300 прогонов, R = K − 1) | K = 4: 358 мин при p = 0.43, 326 при p = 0.25; K = 5: 296 / 270 |
| Средняя одновременная занятость за всю фичу | 3.45–3.47 из 4; 4.2 из 5 (сегодня 2.1–2.4 из 4) |
| Плюс хвост CI и приёмки | ≈ 45–55 мин (последняя партия CI 15–28 мин + приёмка последней истории) |
| Итог по стене | K = 4: ≈ 6.3–6.9 ч; K = 5: ≈ 5.3–5.8 ч |

Фича работоёмкая (78 AC, перевод ~70 файлов на порт, 9 миграций в одной), поэтому время
определяется работой W/K, а не путём: S в 3 раза короче W/K. Пятый исполнитель здесь окупается
(−17%), при R = K − 1 ревьюеров.

## 1. Как читать

`BE/` = `services/django-api/courses/`, `FE/` = `services/frontend/app/(lk)/my-courses/[courseId]/_components/`,
`NEW/` = `services/frontend/app/(lk)/my-courses/new/`, `FEA/` = `services/frontend/`, `config/` =
`services/django-api/config/`. Путь с `#часть` — файл, у которого несколько владельцев по
местам; для пробы это один файл, и такие владельцы всегда стоят на одном пути графа (см. §5).
Номера AC и R — санированной спеки.

## 2. Истории и приёмочные задачи `[T]`

Одна `[T]` на историю, пишется по `contracts.md` и спеке, не по коду К, в момент 0. Тест —
строгий xfail (`unittest.expectedFailure`; во фронте — `test.fail()` Playwright). Срез снимает
xfail своих AC и вливается только после своей `[T]`.

| История | Что | AC | `[T]` | Срезы |
|---|---|---|---|---|
| US1 | Учебный процесс и гейт отправки | 1–6, 9, 21 | T005 | T027, T029, T030 |
| US2 | Экзамены курса | 8, 10–15, 18 | T006 | T028, T016 |
| US3 | Выбранные банки и решатель | 19, 19а, 20, 21, 65 | T007 | T046 |
| US4 | Задача курса: хранение, порт, перенос, стягивание | 55–60, 66–68, 72, 73 | T008 | T001 (AC-55), T033–T041, T042–T045 |
| US5 | Раскладка | 22–32 | T009 | T047, T048, T049 |
| US6 | Приём размещения: связи и свои задачи | 33, 42, 61–64, 71 | T010 | T050, T055 |
| US7 | Гейт 3, один счёт недостачи, перенос и ловушки | 34, 35, 53, 74–77 | T011 | T053, T054, T056 |
| US8 | Ревизии, покрытие, видимость | 36–41, 70 | T012 | T051, T052, T032, T017 |
| US9 | Режимы урока и старые курсы | 43–49 | T013 | T020–T023, T031, T019, T045 |
| US10 | Цель курса и экзамен, копия курса | 50–52, 54 | T014 | T059–T061, T057, T058 |
| US11 | Экраны (клиентские стороны US1–US10) | 7, 16, 17, 22, 36, 43, 46, 69, 78 (UI) | T015 | T062–T065, T024–T026 |

US11 — клиентская сторона срезов US1–US10, разрезанных «сервер ∥ клиент» против контракта
(`design.md` §2.2, без задачи склейки): склейку держат `[T]` обеих сторон (API-тесты T005–T014 и
e2e T015). Резать по сторонам пришлось не ради ширины, а ради владения: `NEW/page.tsx`
(1 397 строк) и `CourseBriefPanel.tsx` (1 341) правят три истории, а у файла один владелец за раз.

## 3. `contracts.md` (карта швов)

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| C1 | `CourseLearningProcess` (поля R-1, PK = course) | T001 [K] | T027, T028, T029, T030, T058 |
| C2 | `learning_process.read`: `settings_for(course)`, `has_current_exam(course, exam_ids=None)` (до T016 — чтение `ExamCourse`/`get_current_versions`, отклонение спеки R-2), `linked_exam_count(course)`; писатель-примитив `disable_exam_activities(course) -> (mocks_disabled, trainer_disabled)` под замком вызывающего | T001 [K] | T027–T030 |
| C3 | `CourseBank` (R-17) | T001 [K] | T046, T047, T048, T058 |
| C4 | `CourseTask` (R-22 целиком, включая `transfer_change_kind`, `ksa_snapshot`, три ограничения БД) | T001 [K] | T042–T045, T047, T049–T051, T058 |
| C5 | `CourseBankLayoutRun` | T001 [K] | T049 |
| C6 | `CourseFinalTask.exam_position_refs`, `exemplar_task_ids`; `CourseFinalTaskKSA.origin = exam` | T001 [K] | T059–T061, T026 |
| C7 | Цепочка миграций шага: 0301 (схема, T001) → 0302 (перенос данных, T042) → 0303 (удаление колонок, T045); номера — на момент вливания | T001 [K] | T042, T045 |
| C8 | Порт `course_bank/placement.py` — весь список R-23а (`rung_ids`, `marks`, `q_on_rungs`, `q_without_rung`, `annotate_rung`, `select_rung`, `course_id_of`, `of_rungs`, `of_course`, `lookup_rung`, `rung_count`, `rung_exists`, `register`, `place`, `set_marks`, `move`, `detach`) + `approve_placement` и `reset_placement`; правило версии Р-CT12 | T002 [K] | T033–T041, T043, T044, T055, T056 |
| C9 | `course_bank.reader.course_tasks(course, *, task_class_ids=None, include_inactive=False) -> list[CourseTaskItem]`, DTO R-23 | T002 [K] | T047, T050–T054 |
| C10 | `reader_links.course_links(...)` — заглушка `[]` в T002, тело — T047 | T002 [K] | T002 (reader.py) |
| C11 | Помощник тестов `make_learning_task(**kw)` (через порт) | T002 [K] | T033–T041, T005–T014 |
| C12 | `exam_tasks.services`: `fipi_task_ids`, `accepted_task_ids`, `task_ksa_ids_many`, `positions_for`, `position_task_ksa_ids` (Е-2, Е-3, Е-4, Е-14, Е-16) | T003 [K] | T032, T047, T048, T051, T052, T059, T060, T018 |
| C13 | Адаптер `course_bank/bank_api.py` — единственный вход курса в банк: `visible_ids`, `trusted_ids`, `steps_of(links)` (через `task_solutions.current_solutions`), `accepted_ids`, `fipi_ids`, `ksa_ids_many`, `current_revisions`, `task_for_author`; `AUDIENCE_STUDENT` | T003 [K] | T047–T052 |
| C14 | Реестр: `learning-process-exam-missing`, `goal-target-not-on-line-top`, `goal-exam-positions-uncovered`, `course-task-placement-unreviewed` (gate_blockers), `rung-ksa-mismatch`, `required-for-mark` (invalid_value_codes), `/problems/goal-exam-position-ksa-missing`; новые meaning/title у `learning-tasks-transfer-insufficient` и `-traps-insufficient`; `problem_types.py`, `locale/ru/problems.json` | T004 [K] | T029, T050, T053, T055, T056, T059–T061 |
| C15 | Привязки гейтов в `gates/registry.py` с заглушками правил (`rules_learning_process.py`, `rules_course_task.py`, `rules_goal_exam.py` отдают `[]`); `TASK_CLASS_MODES_MISSING` и `CONTENT_READING_MODE_INVALID` — только старый путь | T004 [K] | T029, T053, T061, T022 |
| C16 | Все маршруты §6: `learning_process/urls.py`, `course_bank/urls.py` → представления-заглушки по одному файлу на область (`views_process`, `views_exams`, `views_banks`, `views_links`, `views_layout`, `views_revisions`, `views_coverage`), 501; формы запросов и ответов §6 — здесь же, их читают клиентские срезы | T004 [K] | T027, T028, T046, T049–T052, T024, T025, T062–T065 |
| C17 | Хуки: `CourseCreateSerializer`/`CoursePatchSerializer` принимают `exam_ids`, `learning_process`, больше не принимают режимов; `create_course` — одна `transaction.atomic()`, порядок вызовов `exam_links.link_on_create` → `writers.write_on_create`; PATCH — `writers.apply_patch`; деталь курса — `learning_process.api.detail_fields(course)`, ключей режимов нет | T004 [K] | T027, T028, T031, T057 |
| C18 | `course_bank.layout.schedule(course, trigger)`, `wait_for(course, timeout)` — заглушки; точки вызова: прохождение гейта 1, начало генерации задач | T004 [K] | T049 (тело), T046, T034 |
| C19 | `course_bank.detach.detach_links(task_class_ids)` — заглушка; тело T050; точки вызова ставят T036, T037 | T004 [K] | T036, T037, T050 |
| C20 | `course_bank.marks.validate_marks(current, payload, *, pipeline_v2)` — настоящая реализация R-41а (чистая функция) | T004 [K] | T050, T056 |
| C21 | `course_bank.places`: `rung_places(course)` (11/15), `occupancy(course, tc_ids)` | T047 [V] | T049, T051, T052, T054 |
| C22 | `course_bank.candidates`: `candidates(course, tc_ids=None)`, `rung_match`, `fipi_allowed` | T048 [S] | T049, T050, T051, T052 |
| C23 | `course_bank.quotas`: `rung_marks(course)`, `trap_quota_applies(course, tc_id)` | T053 [V] | T052, T054 |
| C24 | `exam_codifier.services`: `author_exam_catalog()`, `course_exam_links(course)`, `link_course` с `ExamAlreadyLinked` | T016 [V] | T028, T046, T058 |

C21–C24 — не швы, а алгоритмы с несколькими потребителями. В К их не взять: им нужны модели
K1, порт K2 и банк K3, и К ушла бы на глубину 2 (по `k_depth.py` это +13–14 мин на путь).
Поэтому они — задачи веера, а рёбра к ним помечены `Почему не по контракту:`.

## 4. Форма графа

- **Фаза К (0–35 мин):** T001–T004 параллельно, без связей между собой. В том же окне —
  все 11 `[T]` и 11 срезов, которым К не нужна: режимы (T020–T023), команда старых курсов
  (T019), функции `exam_codifier` (T016), сторож (T017), фикстура стенда (T018), три
  клиентские задачи против контракта (T024–T026).
- **Веер 1 (35–160):** 9 срезов перевода на порт (T033–T041), учебный процесс и экзамены
  (T027–T030), банки и раскладка (T046–T049), цель (T059–T061), копия (T057), хранение
  приёма размещения (T042, T043).
- **Точка схождения T044** — порт и читатель переходят на `CourseTask`; ждёт все 9 потребителей
  порта. Это не лестница: каждый из девяти стоит на глубине 1 от К.
- **Веер 2:** всё, чему нужен приём размещения своих задач (T055, T056, T053), идёт от T043, а не
  от T044 — приём размещения и вид смены живут только в `CourseTask`, копии полей нет. Поэтому
  T044 не держит продуктовые срезы и стоит на пути только к стягиванию схемы T045.
- **Хвост:** T045 (удаление колонок, сторож чтений), T066 `[H]`.

Рёбра между `[V]` (все с причиной в задаче):

| Ребро | Причина |
|---|---|
| T020/T021/T022/T031 → потребители порта в тех же файлах | общий файл; ранняя задача вливается до старта поздней, ребро упорядочивает по времени, а не удлиняет путь |
| T023 → T062, T025 | `page.tsx`, `types/courses.ts` |
| T029 → T038 | `gating.py`: жизненный цикл и счёт ступеней |
| T016 → T028, T046 | C24 живёт в модуле банка |
| T047 → T049–T054 | C21 и читатель связей |
| T048 → T049 (стек), T050–T052 | C22; T048 → T049 — цепочка `[S]` |
| T053 → T052, T054 | C23 |
| T038 → T053; T034 → T054 | файлы `rules_stages.py`; `deficit.py` |
| T033 → T055 → T056 | `services_learning_tasks.py` (137 упоминаний LearningTask) |
| T057, T028, T046 → T058 | копия — сборка писателей трёх срезов |
| T059 → T060; T062 → T063 → T064; T024 → T065 | общий файл |

## 5. Карта владения горячими файлами

| Файл | Владельцы по порядку (путь в графе) | Как держится |
|---|---|---|
| `config/response-codes.json`, `problem_types.py`, `locale/ru/problems.json` | T004 | все 7 кодов и 2 смены смысла — в К; срезы реестр не растят |
| `BE/urls.py`, `learning_process/urls.py`, `course_bank/urls.py` | T004 | все маршруты — в К, срез заполняет свой `views_<область>.py` |
| `gates/registry.py` | T004 | привязки с заглушками правил в К |
| `BE/services.py` | T004 (`create_course`, хуки) → T031 (`_BRIEF_SYNC_FIELDS`, копия полей) → T057 (`_clone_course_structure_from_source`) | цепочка рёбер |
| `BE/serializers.py`, `BE/views.py` | T004 (курс) → T033 (свои задачи) | ребро T004 → T033 |
| `course_pipeline/gating.py` | T004 (точка гейта 1) → T029 (готовность) → T038 (счёт ступеней) | цепочка |
| `course_pipeline/gates/rules_stages.py` | T038 → T053 (квоты) | ребро |
| `BE/services_learning_tasks.py` | T033 → T055 → T056 | цепочка |
| `BE/tasks.py`, `learning_tasks/deficit.py`, `top_up.py`, `generation_marks.py` | T004 (точка генерации) → T021 (тест режимов) → T034 → T054 | цепочка |
| `course_bank/placement.py`, `reader.py` | T002 → T043 → T044 | цепочка `[K]` → `[S]` |
| `exam_tasks/services.py` | T003 (новые функции в конце файла) → T032 (`_learner_origin_q`) | ребро |
| `BE/migrations/` | T001 (0301) → T042 (0302) → T045 (0303) | одна цепочка в графе; соседи по ветке плана (шаг 8, сессия ЕГЭ) — вне графа, см. §11 |
| `BE/models.py`, `BE/admin.py`, сиды | T001 → … → T045; T031 → T040 | цепочки |
| `NEW/page.tsx` | T023 → T062 | ребро |
| `CourseBriefPanel.tsx` | T023 → T063 → T064 | цепочка |
| `FE/tabs/TasksTab.tsx` | T024 → T065 | ребро |
| README пакетов `learning_process`, `course_bank` | T001 (перечень модулей) → T066 (описание) | срезы README не трогают |
| `docs/engineering/module-map.md` | генерируемое | после rebase перегенерировать, не сливать руками (`pair-rules.txt` → `generated`) |
| `BE/course_bank/__init__.py` | T001, T002, T003 | одинаковое пустое добавление; `pair-rules.txt` → `shared` |

Проверка по скрипту: пересечений `Файлы:` у задач без пути между ними — 0.

## 6. Задачи

- [ ] T001 [K] Схема шага: модели, одна миграция, примитивы учебного процесса
  Срез: контракт (все истории)
  Контракт: владеет C1, C2, C3, C4, C5, C6, C7
  Файлы: BE/learning_process/__init__.py, BE/learning_process/models.py, BE/learning_process/read.py, BE/learning_process/README.md, BE/learning_process/AGENTS.md, BE/learning_process/tests/test_read.py, BE/course_bank/__init__.py, BE/course_bank/models.py, BE/course_bank/README.md, BE/course_bank/AGENTS.md, BE/course_bank/tests/test_models.py, BE/course_goal/models.py, BE/models.py, BE/migrations/0301_step6_schema.py, docs/engineering/module-tiers.json, docs/engineering/module-map.md
  Сущность: CourseLearningProcess, CourseBank, CourseTask, CourseBankLayoutRun, CourseFinalTask
  Миграция: 0301 (единственная схемная миграция шага; transfer_change_kind, ksa_snapshot, origin=exam — сразу здесь)
  Зависит от: —
  Приёмка: AC-55, AC-2 (часть)
  Готово-когда: test_course_task_one_source, test_course_task_unique_exam_task, test_placement_approved_requires_at зелёные и краснеют при снятии ограничений; test_settings_for_defaults (нет строки → умолчания R-1); README обоих пакетов перечисляет все модули из contracts.md (срезы README не трогают); module-map перегенерирован
  Риск: deep
  Размер: M
  Тест-группа: banks, core
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 104

- [ ] T002 [K] Порт размещения своих задач и каркас читателя
  Срез: контракт US4
  Контракт: владеет C8, C9, C10, C11
  Файлы: BE/course_bank/__init__.py, BE/course_bank/placement.py, BE/course_bank/reader.py, BE/course_bank/reader_links.py, BE/course_bank/dto.py, BE/tests/_learning_tasks_fixture.py, BE/course_bank/tests/test_placement_legacy.py, BE/course_bank/tests/test_reader_own.py
  Сущность: порт placement (новый); до T044 порт пишет колонки LearningTask, CourseTask ему не нужен — поэтому K2 параллельна K1, а не за ней
  Зависит от: —
  Приёмка: AC-73 (часть: правило версии)
  Готово-когда: test_port_equals_columns (каждый метод порта на колонках LearningTask даёт то же, что прямой ORM; краснеет при подмене любого метода), test_version_once_per_operation; reader.course_tasks отдаёт свои задачи через порт, связи — из заглушки reader_links ([]); make_learning_task создаёт задачу только через порт
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 103

- [ ] T003 [K] API банка экзамена для курса и адаптер банка
  Срез: контракт US5, US8, US10
  Контракт: владеет C12, C13
  Файлы: BE/course_bank/__init__.py, BE/exam_tasks/services.py, BE/exam_tasks/tests/test_course_api.py, BE/course_bank/bank_api.py, BE/course_bank/tests/test_bank_api.py
  Мера: публичные функции exam_tasks (растёт только здесь)
  Зависит от: —
  Приёмка: AC-41 (часть: курс не читает origin)
  Готово-когда: test_fipi_task_ids_own_origin_only (derived_from не считается), test_accepted_task_ids (active, не дубликат, доверенный ответ), test_position_task_ksa_ids_active_only, test_task_ksa_ids_many_equals_single, test_bank_api_no_origin (адаптер не импортирует поля происхождения)
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 75

- [ ] T004 [K] Швы: реестр кодов, привязки гейтов, маршруты-заглушки, хуки создания/правки/деталей, проверка отметок
  Срез: контракт US1–US10
  Контракт: владеет C14–C20
  Файлы: config/response-codes.json, config/api-problems.json, config/problem_types.py, config/locale/ru/problems.json, BE/course_pipeline/gates/registry.py, BE/course_pipeline/gates/rules_learning_process.py, BE/course_pipeline/gates/rules_course_task.py, BE/course_pipeline/gates/rules_goal_exam.py, BE/urls.py, BE/learning_process/urls.py, BE/learning_process/api.py, BE/learning_process/hooks.py, BE/learning_process/views_process.py, BE/learning_process/views_exams.py, BE/learning_process/exam_links.py, BE/learning_process/writers.py, BE/course_bank/urls.py, BE/course_bank/views_banks.py, BE/course_bank/views_links.py, BE/course_bank/views_layout.py, BE/course_bank/views_revisions.py, BE/course_bank/views_coverage.py, BE/course_bank/layout.py, BE/course_bank/detach.py, BE/course_bank/marks.py, BE/course_bank/tests/test_marks.py, BE/serializers.py, BE/services.py#create_course, BE/views.py#course_detail, BE/course_pipeline/course_patch.py#hook, BE/course_pipeline/gating.py#gate1_pass, BE/tasks.py#generation_start, BE/tests/test_step6_seams.py
  Мера: реестр кодов ответа, реестр привязок гейтов (растут только здесь)
  Зависит от: —
  Приёмка: AC-47 (привязка), AC-43 (API: ответ без режимов)
  Готово-когда: все ручки §6 отвечают 501 problem `not-implemented` (кроме уже существующих); реестр: 7 новых кодов с added_by T-2264 и смена meaning/title двух кодов (сверка реестра зелёная); test_step6_seams: create_course в одной транзакции, хуки зовутся в порядке exam_links → writers; деталь курса без allowed_lesson_modes/prefer_pbl и с learning_process (умолчания) и linked_exam_count; test_marks (4 правила R-41а)
  Риск: обычный
  Размер: M
  Тест-группа: codes, saga, core
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 100

- [ ] T005 [T] [T] US1 Учебный процесс и гейт отправки
  Срез: US1
  Контракт: C1, C2, C14, C15, C16, C17
  Файлы: BE/tests/acceptance/step6/test_us1_learning_process.py
  Зависит от: —
  Приёмка: AC-1…AC-6, AC-9, AC-15 (часть LP)
  Готово-когда: по тесту на каждый AC, строгий xfail (expectedFailure); каждый бьёт и запись, и чтение (PATCH → GET)
  Риск: обычный
  Размер: S
  Тест-группа: core
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 90

- [ ] T006 [T] [T] US2 Экзамены курса
  Срез: US2
  Контракт: C2, C16, C17, C24
  Файлы: BE/tests/acceptance/step6/test_us2_exams.py
  Зависит от: —
  Приёмка: AC-8, AC-10…AC-15, AC-18
  Готово-когда: строгий xfail; гонка AC-13 — TransactionTestCase с двумя потоками
  Риск: обычный
  Размер: S
  Тест-группа: core
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 74

- [ ] T007 [T] [T] US3 Банки и решатель
  Срез: US3
  Контракт: C3, C16
  Файлы: BE/tests/acceptance/step6/test_us3_banks.py
  Зависит от: —
  Приёмка: AC-19, AC-19а, AC-20, AC-21, AC-65
  Готово-когда: строгий xfail
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 55

- [ ] T008 [T] [T] US4 Задача курса: хранение и переход на неё
  Срез: US4
  Контракт: C4, C7, C8, C9, C11
  Файлы: BE/tests/acceptance/step6/test_us4_course_task.py
  Зависит от: —
  Приёмка: AC-56…AC-60, AC-66, AC-67, AC-68 (поиск по коду), AC-72, AC-73
  Готово-когда: строгий xfail; AC-56/57 — тест миграции по scripts/check_migration_tests.py; AC-60 — по одному тесту на каждый путь создания
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 94

- [ ] T009 [T] [T] US5 Раскладка
  Срез: US5
  Контракт: C4, C5, C13, C16, C18, C21, C22
  Файлы: BE/tests/acceptance/step6/test_us5_layout.py
  Зависит от: —
  Приёмка: AC-22 (API), AC-23…AC-32
  Готово-когда: строгий xfail; AC-26 — два прогона в потоках
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 75

- [ ] T010 [T] [T] US6 Приём размещения (связи и свои задачи)
  Срез: US6
  Контракт: C4, C9, C14, C16
  Файлы: BE/tests/acceptance/step6/test_us6_placement.py
  Зависит от: —
  Приёмка: AC-33, AC-42, AC-61…AC-64, AC-71
  Готово-когда: строгий xfail
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 59

- [ ] T011 [T] [T] US7 Гейт 3, один счёт недостачи, перенос и ловушки
  Срез: US7
  Контракт: C9, C14, C15, C20, C23
  Файлы: BE/tests/acceptance/step6/test_us7_gate3_quotas.py
  Зависит от: —
  Приёмка: AC-34, AC-35, AC-53, AC-74…AC-77
  Готово-когда: строгий xfail; AC-35 — один фикстурный курс для трёх потребителей
  Риск: обычный
  Размер: M
  Тест-группа: saga, banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 60

- [ ] T012 [T] [T] US8 Ревизии, покрытие, видимость
  Срез: US8
  Контракт: C9, C13, C16
  Файлы: BE/tests/acceptance/step6/test_us8_revisions_coverage.py
  Зависит от: —
  Приёмка: AC-36 (API), AC-37…AC-41, AC-70
  Готово-когда: строгий xfail; AC-41 — запуск сторожа T017 на дереве
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 51

- [ ] T013 [T] [T] US9 Режимы урока и старые курсы
  Срез: US9
  Контракт: C15, C17
  Файлы: BE/tests/acceptance/step6/test_us9_modes_legacy.py
  Зависит от: —
  Приёмка: AC-43 (API), AC-44…AC-49
  Готово-когда: строгий xfail; AC-48 — тест миграции 0303
  Риск: обычный
  Размер: S
  Тест-группа: structure, lessons
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 95

- [ ] T014 [T] [T] US10 Цель курса, экзамен и копия курса
  Срез: US10
  Контракт: C6, C12, C15, C17
  Файлы: BE/tests/acceptance/step6/test_us10_goal_copy.py
  Зависит от: —
  Приёмка: AC-50…AC-52, AC-54
  Готово-когда: строгий xfail
  Риск: обычный
  Размер: S
  Тест-группа: core, structure
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 64

- [ ] T015 [T] [T] US11 Экраны (e2e на стенде cc-*)
  Срез: US11
  Контракт: C16 (формы ответов §6)
  Файлы: FEA/tests/e2e/step6-create.spec.ts, FEA/tests/e2e/step6-brief.spec.ts, FEA/tests/e2e/step6-tasks.spec.ts, FEA/tests/e2e/step6-structure.spec.ts
  Зависит от: —
  Приёмка: AC-7, AC-16, AC-17, AC-22 (UI), AC-36 (UI), AC-43 (UI), AC-46 (UI), AC-69, AC-78
  Готово-когда: Playwright test.fail() по каждому AC; запускается приёмкой на :8092, в CI не входит
  Риск: обычный
  Размер: M
  Тест-группа: frontend (e2e)
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T016 [V] Экзамены для курса в exam_codifier: каталог автора, связи курса, стойкое связывание
  Срез: US2
  Контракт: владеет C24
  Файлы: BE/exam_codifier/services.py, BE/exam_codifier/tests/test_course_api.py
  Почему не по контракту: функции живут в модуле банка (один писатель exam_codifier), курсу нужны только их имена из C24; у задачи нет зависимостей, она идёт в окне К
  Зависит от: —
  Приёмка: AC-10, AC-13 (часть банка) (тесты из T006 [T]; вливается после них)
  Готово-когда: test_author_exam_catalog_current_only, test_course_exam_links, test_link_course_race_raises_already_linked (два потока → одно ExamAlreadyLinked, не IntegrityError)
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 64

- [ ] T017 [V] Сторож писателей и читателей новых моделей (R-49, часть 1)
  Срез: US4, US8
  Контракт: C1, C3, C4, C5
  Файлы: scripts/check_step6_writes.py, .pre-commit-config.yaml#step6, scripts/tests/test_check_step6_writes.py
  Зависит от: —
  Приёмка: AC-41 (часть), AC-68 (часть: CourseTask) (тесты из T012 [T]; вливается после них)
  Готово-когда: скрипт краснеет на фикстурном файле вне пакета, читающем CourseTask или пишущем CourseLearningProcess/CourseBank/CourseBankLayoutRun; подключён в pre-commit и CI
  Риск: обычный
  Размер: S
  Тест-группа: governance
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 41

- [ ] T018 [V] Фикстура стенда для банка экзамена (Е-10)
  Срез: US5, US10 (приёмка на стенде)
  Контракт: C12
  Файлы: BE/exam_tasks/management/commands/seed_step6_bank_fixture.py, BE/exam_tasks/tests/test_seed_step6_fixture.py
  Зависит от: —
  Приёмка: — (нужна acceptance для AC-22, AC-51 на стенде)
  Готово-когда: команда идемпотентна; создаёт задачи на нескольких позициях с KSA, доверенными ответами и шагами, одну ФИПИ и её вариант authored, позицию без KSA, задачу с ответом без приёма KSA; выдача ФИПИ выключена; test_seed_step6_fixture
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T019 [V] Команда снятия старых курсов с публикации и возврата с модерации (R-47а)
  Срез: US9
  Контракт: —
  Файлы: BE/management/commands/unpublish_legacy_courses.py, BE/tests/test_unpublish_legacy_courses.py
  Зависит от: —
  Приёмка: AC-49 (тесты из T013 [T]; вливается после них)
  Готово-когда: test_unpublish_legacy: список без --apply ничего не меняет; без --actor или без прав IsSagaAdmin — CommandError до изменений; published → banks_ready + sync зеркала; pending_review → review_rejected + заявка rejected с причиной; само-модерация только для pending_review; повтор безопасен
  Риск: deep
  Размер: S
  Тест-группа: saga
  Оценка: вес 16 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 31

- [ ] T020 [V] Режимы — константа: тема, урок, трек (R-42 часть, R-46)
  Срез: US9
  Контракт: —
  Файлы: BE/topic_content/lesson_modes.py, BE/lesson/streaming.py, BE/lesson/mode_a/services.py, BE/lesson/serializers.py, BE/track_manage/read.py, BE/track_manage/serializers.py, BE/tests/test_lesson_mode_selection.py, BE/topic_content/AGENTS.md
  Зависит от: —
  Приёмка: AC-43 (ученик бывшего ["A"] видит Б) (тесты из T013 [T]; вливается после них)
  Готово-когда: test_lesson_mode_selection: курс [] и ["A"] → оба режима по правилам темы; краснеет при возврате чтения поля
  Риск: обычный
  Размер: S
  Тест-группа: lessons
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T021 [V] Режимы — константа: генерация структуры, раскладка ступеней, редактор графа; инвариант «линия А без чтения» (R-42 часть, R-44)
  Срез: US9
  Контракт: —
  Файлы: BE/structure_gen/skeleton.py, BE/structure_gen/tasks.py, BE/task_classes/rung_layout.py, BE/task_classes/rung_layout_db.py, BE/course_graph_editor/read.py, BE/graph_invariants/structure_gate.py, BE/structure_gen/tests/test_phase1_brief_params.py, BE/task_classes/tests/test_rung_layout_db.py, BE/graph_invariants/tests/test_adr087_gate.py, BE/tests/test_learning_tasks_deficit.py#modes, BE/tests/_course_structure_audit_fixture.py
  Зависит от: —
  Приёмка: AC-44, AC-45 (тесты из T013 [T]; вливается после них)
  Готово-когда: _allowed_modes_for_skills даёт [A,B] у курса []; rung_layout строит ступень чтения; reading-line-missing: старый путь — всегда, флаг — пусто (gate1, audit.py, repair)
  Риск: обычный
  Размер: M
  Тест-группа: structure
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 85

- [ ] T022 [V] Окно ступени на флаге без режимов (R-48, R-45 тест)
  Срез: US9
  Контракт: C15 (привязка)
  Файлы: BE/task_classes/services.py, FE/structure/TaskClassModal.tsx, BE/task_classes/tests/test_allowed_modes_flag.py
  Зависит от: —
  Приёмка: AC-46, AC-47 (тесты из T013 [T]; вливается после них)
  Готово-когда: POST ступени с allowed_modes на флаге → 422 not-applicable; без него content_reading [A], whole_task [A,B]; смена вида пересчитывает; без флага — как было; TaskClassModal на флаге без чекбоксов (jest)
  Риск: обычный
  Размер: S
  Тест-группа: banks, frontend
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T023 [V] Фронт: выбор режимов снят из формы создания и панели брифа (R-43, фронт)
  Срез: US9
  Контракт: —
  Файлы: NEW/page.tsx, FE/overview/CourseBriefPanel.tsx, FE/overview/briefFieldLabels.ts, FE/overview/briefConsistency.ts, FE/structure/TopicTreePanel.tsx, FEA/config/courseCreation.ts, FEA/utils/auth.ts, FEA/types/courses.ts, FEA/__tests__/briefValidation.test.ts
  Зависит от: —
  Приёмка: AC-43 (UI) (тесты из T015 [T]; вливается после них)
  Готово-когда: в форме и панели нет полей режимов; briefValidation/briefConsistency без них; jest зелёный
  Риск: обычный
  Размер: S
  Тест-группа: frontend
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 65

- [ ] T024 [V] Экран «Задачи»: блок «Задачи из банка»
  Срез: US11 (клиент US5, US6)
  Контракт: C16 (формы links/layout/candidates)
  Файлы: FE/tasks/CourseBankBlock.tsx, FE/tasks/CourseBankLinkRow.tsx, FE/tasks/CandidatesModal.tsx, FEA/types/courseBankLinks.ts, FEA/lib/api/courseBankLinks.ts, FE/tabs/TasksTab.tsx, FEA/__tests__/tasks/courseBankBlock.test.tsx
  Зависит от: —
  Приёмка: AC-22 (UI), AC-69 (часть связей) (тесты из T015 [T]; вливается после них)
  Готово-когда: блок над списком своих задач при выбранном банке; ступень, пометки «шаги есть → П и З доступны», «ждёт ответа в банке», «банк снят», свёрнутые отклонённые с возвратом, «Подобрать ещё из банка», «в банке ещё N» → «Добавить»; jest на моках ответов по contracts.md
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 45

- [ ] T025 [V] Экран «Задачи»: приём размещения своих задач, вид смены, ловушки «без пары»
  Срез: US11 (клиент US6, US7)
  Контракт: C16 (формы learning-tasks)
  Файлы: FE/tasks/AnswerMarksFields.tsx, FE/tasks/BulkBar.tsx, FE/tasks/EditLearningTaskModal.tsx, FE/tasks/CreateLearningTaskModal.tsx, FE/tasks/TreeGroupedPool.tsx, FE/tasks/InboxLT.tsx, FE/tasks/learningTaskForm.ts, FE/tasks/placementLabels.ts, FEA/types/courses.ts#LearningTask, FEA/__tests__/tasks/placement.test.tsx
  Зависит от: T023
  Приёмка: AC-69 (часть своих), AC-78 (тесты из T015 [T]; вливается после них)
  Готово-когда: одна кнопка «Принять задачу» у новой ставит оба приёма; «Принять размещение» у перенесённой и в пачке; вид смены и «Укажите вид смены»; «без пары» у ловушки; ошибки required-for-mark у полей
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T026 [V] Итоговые задачи: позиции КИМ и образцы (фронт R-50)
  Срез: US11 (клиент US10)
  Контракт: C6 (форма ответа)
  Файлы: FE/overview/FinalTasksBlock.tsx, FE/overview/finalTasks.ts, FE/overview/ExamPositionPicker.tsx, FEA/__tests__/overview/finalTaskPositions.test.tsx
  Зависит от: —
  Приёмка: AC-50 (UI) (тесты из T015 [T]; вливается после них)
  Готово-когда: выбор позиций связанных экзаменов, до 3 образцов, exam_linked:false показан; jest
  Риск: обычный
  Размер: S
  Тест-группа: frontend
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T027 [V] Учебный процесс: проверки, запись под версией курса, чтение, решатель (R-1…R-6 сервер, R-0, R-21)
  Срез: US1
  Контракт: C1, C2, C14, C16, C17
  Файлы: BE/learning_process/validation.py, BE/learning_process/writers.py, BE/learning_process/api.py, BE/learning_process/views_process.py, BE/learning_process/tests/test_validation.py, BE/learning_process/tests/test_writers.py
  Зависит от: T001, T004
  Приёмка: AC-1…AC-6, AC-21 (тесты из T005 [T]; вливается после них)
  Готово-когда: снять xfail AC-1…AC-6, AC-21 в TA1/TA3; test_writers_lock_order (строка курса первой); hold: откат validation.py/writers.py краснит тесты
  Риск: deep
  Размер: M
  Тест-группа: core
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 39

- [ ] T028 [V] Экзамены курса: каталог, список, связать, снять, создание с exam_ids, слияние ответа (R-10…R-14, R-12а)
  Срез: US2
  Контракт: C2, C16, C17, C24
  Файлы: BE/learning_process/exam_links.py, BE/learning_process/views_exams.py, BE/learning_process/catalog.py, BE/learning_process/tests/test_exam_links.py, BE/learning_process/tests/test_exam_links_race.py
  Зависит от: T001, T004, T016
  Приёмка: AC-8, AC-10…AC-13, AC-15, AC-18 (тесты из T006 [T]; вливается после них)
  Готово-когда: снять xfail AC-8, AC-10…AC-13, AC-15, AC-18; 404/403 по правам (AC-12); version +1 и learning_process в ответе
  Риск: deep
  Размер: M
  Тест-группа: core
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 54

- [ ] T029 [V] Гейт отправки learning-process-exam-missing и готовность заранее (R-7)
  Срез: US1
  Контракт: C2, C14, C15
  Файлы: BE/course_pipeline/gates/rules_learning_process.py, BE/course_pipeline/gate_journal.py, BE/publication/views.py#SubmitForReviewView, BE/course_pipeline/gating.py#lifecycle, FE/tabs/PublishTab.tsx, BE/course_pipeline/tests/test_submit_own_refuses.py
  Зависит от: T001, T004
  Приёмка: AC-9 (тесты из T005 [T]; вливается после них)
  Готово-когда: SubmitCheck.own_refuses; порядок витрина → собственные → перепроверка; 409 gate-blocked с gate_title без gate; /lifecycle can_submit_for_review=false и блокер в списке; PublishTab не пишет «Всё готово» при блокере
  Риск: обычный
  Размер: S
  Тест-группа: saga, frontend
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T030 [V] Вход в «Тренажёр ЕГЭ» из курса (Е-15)
  Срез: US1
  Контракт: C2 (settings_for)
  Файлы: BE/exam_trainer/services.py#start_session, BE/exam_trainer/tests/test_entry_from_course.py, FEA/app/courses/[courseId]/ExamTrainerEntry.tsx, FEA/app/courses/[courseId]/page.tsx
  Зависит от: T001
  Приёмка: — (R-9; приёмка — e2e) (тесты из T005 [T]; вливается после них)
  Готово-когда: start_session(entry=course) отказывает при exam_trainer_enabled=false; кнопка на странице курса ученика по каждому связанному экзамену только при включённом
  Риск: обычный
  Размер: S
  Тест-группа: banks, frontend
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T031 [V] Режимы сняты из записи: бриф, правка курса, копия полей, админка, сиды (R-43, сервер)
  Срез: US9
  Контракт: C17
  Файлы: BE/services.py#brief_sync, BE/course_pipeline/course_patch.py#modes, BE/admin.py, BE/domain_errors/__init__.py, BE/management/commands/seed_course_pipeline.py, BE/management/commands/seed_tariff_testbed.py, BE/management/commands/seed_ksa_tc_testbed.py, BE/management/commands/prepare_t1142_manual.py, BE/management/commands/prepare_t1144_purchase_manual.py, BE/tests/test_brief_schema.py, BE/course_pipeline/tests/test_methodology_patch.py, BE/tests/test_main.py#modes
  Зависит от: T004
  Приёмка: AC-43 (API), AC-48 (сиды работают) (тесты из T013 [T]; вливается после них)
  Готово-когда: _BRIEF_SYNC_FIELDS, _POST_PUBLICATION_BLOCKED_FIELDS, update_course_brief, course_patch без режимов; присланное поле игнорируется; сиды и prepare_* проходят
  Риск: обычный
  Размер: M
  Тест-группа: structure, core
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 85

- [ ] T032 [V] Выключатель ФИПИ только для задач с собственным происхождением ФИПИ (Е-17)
  Срез: US8
  Контракт: C12
  Файлы: BE/exam_tasks/services.py#_learner_origin_q, BE/exam_tasks/tests/test_fipi_switch_own_origin.py
  Зависит от: T003
  Приёмка: AC-40 (вторая часть), AC-70 (тесты из T012 [T]; вливается после них)
  Готово-когда: задача ФИПИ скрыта при выключенной выдаче, вариант authored на её основе виден
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T033 [V] Порт: CRUD и API своих задач (services_learning_tasks, ручки, права)
  Срез: US4
  Контракт: C8, C11, C17
  Файлы: BE/services_learning_tasks.py, BE/views.py#learning_tasks, BE/permissions.py, BE/tests/test_learning_tasks_api.py, BE/tests/test_learning_task_version.py
  Зависит от: T002, T004
  Приёмка: AC-58, AC-60 (автор), AC-72, AC-73 (тесты из T008 [T]; вливается после них)
  Готово-когда: ни одного обращения к task_class/is_transfer/is_trap/trap_note LearningTask в файлах задачи (grep в тесте); PATCH ступени+шагов → version ровно +1; ответ API прежний
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 79

- [ ] T034 [V] Порт: генерация, недостача, добор
  Срез: US4
  Контракт: C8, C11, C18 (точка вызова)
  Файлы: BE/tasks.py, BE/learning_tasks/selection.py, BE/learning_tasks/deficit.py, BE/learning_tasks/top_up.py, BE/learning_tasks/generation_marks.py, BE/learning_tasks/solution_check.py, BE/learning_tasks/genre_fields.py, BE/learning_tasks/run_outcome.py, BE/learning_tasks/tests/, BE/tests/test_learning_tasks_deficit.py
  Зависит от: T002, T004, T021
  Приёмка: AC-60 (генерация) (тесты из T008 [T]; вливается после них)
  Готово-когда: файлы задачи читают ступень только через порт; генерация зовёт placement.register; тесты learning_tasks на make_learning_task
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T035 [V] Порт: решатель своих задач, биллинг, реестр транспорта
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/learning_task_solver/, BE/billing/learning_tasks.py, BE/ml_transport/registry.py
  Зависит от: T002
  Приёмка: AC-73 (решатель читает по новой версии) (тесты из T008 [T]; вливается после них)
  Готово-когда: то же правило grep; тесты learning_task_solver зелёные
  Риск: обычный
  Размер: M
  Тест-группа: banks, billing, transport
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T036 [V] Порт: перекладка ступеней шагов 3а/4 (rung_switch, target_ksa, topic_merge, services ступени)
  Срез: US4
  Контракт: C8, C11, C19 (точка вызова)
  Файлы: BE/task_classes/rung_switch.py, BE/task_classes/target_ksa.py, BE/task_classes/topic_merge.py, BE/task_classes/services.py, BE/task_classes/predicates.py, BE/task_classes/delete_preview.py, BE/task_classes/rung_layout_db.py, BE/task_classes/tests/
  Зависит от: T002, T021, T022
  Приёмка: AC-67 (rung_switch) (тесты из T008 [T]; вливается после них)
  Готово-когда: detach_or_delete зовёт placement.detach и course_bank.detach.detach_links; relocate — move с version +1 один раз
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T037 [V] Порт: удаление ступеней и тем, редактор графа
  Срез: US4
  Контракт: C8, C11, C19
  Файлы: BE/course_structure/deletion.py, BE/course_structure/rung_layout.py, BE/course_graph_editor/write.py, BE/course_graph_editor/read.py, BE/course_graph_editor/delete_preview.py, BE/course_structure/tests/test_deletion*.py, BE/course_structure/tests/test_rung_layout*.py, BE/course_graph_editor/tests/
  Зависит от: T002, T021, T004
  Приёмка: AC-60 (сохранение графа, bulk_create), AC-67 (deletion.py, rung_layout.py) (тесты из T008 [T]; вливается после них)
  Готово-когда: обработчик before_delete для TaskClass зовёт detach_links; write.py после bulk_create зовёт register
  Риск: обычный
  Размер: M
  Тест-группа: banks, graph
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T038 [V] Порт: гейты и сага
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/course_pipeline/gating.py#rung, BE/course_pipeline/gates/rules_stages.py, BE/course_pipeline/gates/facts.py, BE/course_pipeline/auto_pipeline.py, BE/course_pipeline/methodology_locks.py, BE/course_pipeline/views.py, BE/saga/reopen.py, BE/saga/state_machine.py, BE/course_pipeline/tests/test_gating_*.py, BE/course_pipeline/tests/test_rules_stages*.py, BE/course_pipeline/tests/test_auto_pipeline*.py, BE/saga/tests/, BE/publication/tests/, BE/methodology_params/tests/
  Зависит от: T002, T004, T029
  Приёмка: AC-63 (часть: счёт по порту) (тесты из T008 [T]; вливается после них)
  Готово-когда: rules_stages.rung_count/rung_exists через порт; reopen и auto_pipeline без колонок
  Риск: обычный
  Размер: M
  Тест-группа: saga
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T039 [V] Порт: уроки, диалог, трек, материал, документы
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/lesson/streaming.py, BE/lesson/mode_a/services.py, BE/dialogue/item_materialization.py, BE/dialogue/lesson_setup.py, BE/dialogue/orchestrator_b.py, BE/track_manage/read.py, BE/track_manage/validation.py, BE/track_manage/models.py, BE/topic_content/passthrough.py, BE/topic_content/lesson_modes.py, BE/topic_content/generation/, BE/documents/services.py, BE/documents/views.py, BE/dialogue/tests/, BE/lesson/tests/, BE/track_manage/tests/, BE/documents/tests/
  Зависит от: T002, T020
  Приёмка: AC-66 (урок по ступени) (тесты из T008 [T]; вливается после них)
  Готово-когда: dialogue/lesson_setup получает задачи ступени через порт; тесты lessons зелёные
  Риск: обычный
  Размер: M
  Тест-группа: lessons, content, documents
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T040 [V] Порт: импорт, команды, сиды, админка
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/_lt_import.py, BE/lt_import.py, BE/services_lt_import.py, BE/admin.py, BE/management/commands/archive_non_whole_task_learning_tasks.py, BE/management/commands/repair_structure_links.py, BE/management/commands/rung_rule_report.py, BE/management/commands/learning_task_target_audit.py, BE/management/commands/solution_steps_report.py, BE/management/commands/cleanup_tc_role_anomalies.py, BE/management/commands/backfill_adr087_projection.py, BE/management/commands/seed_t815_demo.py, BE/management/commands/seed_ksa_tc_testbed.py, BE/management/commands/seed_course_pipeline.py, BE/management/commands/_seed_lifecycle.py, BE/structure_gen/semantics.py, BE/tests/test_lt_import.py
  Зависит от: T002, T031
  Приёмка: AC-60 (импорт, сид) (тесты из T008 [T]; вливается после них)
  Готово-когда: импорт и сиды создают задачи через порт; команды отчётов читают через порт
  Риск: обычный
  Размер: M
  Тест-группа: documents, platform
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T041 [V] Порт: общие тесты courses/tests на фикстуру make_learning_task
  Срез: US4
  Контракт: C11
  Файлы: BE/tests/test_integration.py, BE/tests/test_main.py, BE/tests/test_structure_gen.py, BE/tests/_course_structure_audit_fixture.py, BE/tests/test_backfill_adr087.py, BE/structure_gen/tests/test_sync_topic_links.py, BE/matching/tests/, BE/ml_transport/tests/
  Зависит от: T002, T020, T021, T031
  Приёмка: AC-68 (тесты) (тесты из T008 [T]; вливается после них)
  Готово-когда: в перечисленных файлах нет LearningTask(task_class=…) и прямых полей роли
  Риск: обычный
  Размер: M
  Тест-группа: core
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T042 [S] Перенос своих задач в задачи курса: миграция RunPython и проверочная команда (R-22а)
  Срез: US4
  Контракт: C4, C7
  Файлы: BE/migrations/0302_course_task_from_learning_task.py, BE/management/commands/check_learning_task_course_alignment.py, BE/tests/test_migration_0302.py
  Миграция: 0302
  Почему не срез: перенос данных одной миграцией, цепочка миграций линейна
  Зависит от: T001
  Приёмка: AC-56, AC-57 (тесты из T008 [T]; вливается после них)
  Готово-когда: снять xfail AC-56, AC-57; миграция на исторических моделях, идемпотентна, обратима, сверка (а)–(д); check_learning_task_course_alignment: код 1 при рассогласовании
  Риск: deep
  Размер: M
  Тест-группа: banks, platform
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 79

- [ ] T043 [S] Хранение приёма размещения и вида смены своих задач в CourseTask
  Срез: US4, US6
  Контракт: C4, C8, C9
  Файлы: BE/course_bank/placement.py, BE/course_bank/reader.py, BE/course_bank/tests/test_placement_storage.py
  Почему не срез: меняет внутренности порта K2, вызывающий код не трогает
  Зависит от: T001, T002
  Приёмка: AC-60 (у новой — задача курса), AC-62 (сброс) (тесты из T008 [T]; вливается после них)
  Готово-когда: register создаёт CourseTask (placed_by=with_task, ready_for_review), строка на старую задачу — get_or_create по правилу миграции; approve_placement, сброс при place/move/set_marks, transfer_change_kind в set_marks/marks; reader отдаёт placement_status своих
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 79

- [ ] T044 [S] Порт и читатель переключены на CourseTask (ступень и роль своих задач)
  Срез: US4
  Контракт: C8, C9
  Файлы: BE/course_bank/placement.py, BE/course_bank/reader.py, BE/course_bank/tests/test_port_switch.py
  Почему не срез: точка схождения всех потребителей порта
  Зависит от: T042, T043, T033, T034, T035, T036, T037, T038, T039, T040, T041
  Приёмка: AC-58, AC-73 (тесты из T008 [T]; вливается после них)
  Готово-когда: снять xfail AC-58 и AC-73; порт и читатель не читают колонки LearningTask; полный прогон courses в партии зелёный
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 55

- [ ] T045 [S] Удаление колонок своих задач и режимов; сторож чтений (R-22б, R-47, R-49 часть 2)
  Срез: US4, US9
  Контракт: C7
  Файлы: BE/migrations/0303_drop_step6_columns.py, BE/models.py, BE/course_goal/models.py#none, BE/tests/test_migration_0303.py, scripts/check_step6_writes.py
  Миграция: 0303
  Почему не срез: стягивание схемы после перехода всех читателей
  Зависит от: T044, T020, T021, T031, T022, T017
  Приёмка: AC-48, AC-59, AC-68 (тесты из T013 [T]; вливается после них)
  Готово-когда: миграция RemoveField learning_task.(task_class, is_transfer, is_trap, trap_note), course/brief.(allowed_lesson_modes, prefer_pbl); обратная — AddField и заполнение из course_task; сторож: режимы не читаются нигде, поля LearningTask вне миграций — нет
  Риск: deep
  Размер: S
  Тест-группа: platform, core
  Оценка: вес 16 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 31

- [ ] T046 [V] Выбранные банки: список, выбрать, снять; число задач курса по экзамену (R-17…R-20, course_task_count)
  Срез: US3
  Контракт: C3, C4, C16, C18 (schedule), C24
  Файлы: BE/course_bank/banks.py, BE/course_bank/views_banks.py, BE/course_bank/tests/test_banks.py
  Почему не по контракту (ребро T016): список экзаменов курса — функция C24 модуля банка
  Зависит от: T001, T004, T016
  Приёмка: AC-19, AC-19а, AC-20 (связи на месте), AC-65 (тесты из T007 [T]; вливается после них)
  Готово-когда: снять xfail AC-19, AC-19а, AC-65; выбор после гейта 1 зовёт layout.schedule(trigger=bank_selected)
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 45

- [ ] T047 [V] Читатель связей, места ступени, видимость (R-23 связи, R-28, R-40)
  Срез: US5, US8
  Контракт: C4, C9, C10, C13; владеет C21
  Файлы: BE/course_bank/reader_links.py, BE/course_bank/places.py, BE/course_bank/tests/test_reader_links.py, BE/course_bank/tests/test_places.py
  Зависит от: T001, T002, T003
  Приёмка: AC-20 (active=false), AC-36 (has_steps), AC-40 (тесты из T009 [T]; вливается после них)
  Готово-когда: reader_links пакетно (без запроса на задачу — assertNumQueries); rung_places 11/15; occupancy под замком вызывающего; аудитория student одной константой
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 60

- [ ] T048 [S] Раскладка, расчёт: кандидаты ступеней, правило ФИПИ, приоритет (R-25, R-26, R-29, R-30)
  Срез: US5
  Контракт: C13; владеет C22
  Файлы: BE/course_bank/candidates.py, BE/course_bank/tests/test_candidates.py
  Почему не срез: раскладка — один алгоритм в две фазы; цепочка [S] T048 → T049, стек разрешён
  Зависит от: T003
  Приёмка: AC-25, AC-27…AC-30 (тесты из T009 [T]; вливается после них)
  Готово-когда: candidates() без записи; один кандидат → moved, два → ambiguous; ФИПИ только верх линии, ≤ 3; порядок ответ → шаги → видна → номера КИМ по кругу → id
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 54

- [ ] T049 [S] Раскладка, запись: замок курса, места, журнал прогонов, Celery, запуски gate1/bank_selected/generation/manual, ожидание генерацией (R-27, R-28)
  Срез: US5
  Контракт: C5, C18, C21, C22
  Файлы: BE/course_bank/layout.py, BE/course_bank/tasks.py, BE/course_bank/views_layout.py, BE/course_bank/tests/test_layout_write.py, BE/course_bank/tests/test_layout_concurrency.py
  Почему не по контракту (ребро T047): счёт мест C21 — один на раскладку, недостачу и отчёт
  Зависит от: T048 (стек), T047, T004
  Приёмка: AC-22 (API), AC-23, AC-24, AC-26, AC-31, AC-32 (тесты из T009 [T]; вливается после них)
  Готово-когда: снять xfail TA5; два прогона в потоках не превышают мест; повтор ничего не меняет; отклонённую не возвращает; генерация ждёт прогон не дольше предела, по пределу — failed в журнале
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 39

- [ ] T050 [V] Связи: ручное добавление, правка, отклонение и возврат, приём размещения пачкой, после публикации закрыто; detach_links (R-31…R-35, R-38, R-22 detach)
  Срез: US6
  Контракт: C14, C16, C19, C20, C21, C22
  Файлы: BE/course_bank/links.py, BE/course_bank/detach.py, BE/course_bank/views_links.py, BE/course_bank/tests/test_links.py, BE/course_bank/tests/test_detach.py
  Зависит от: T047, T048, T004
  Приёмка: AC-33, AC-42, AC-64 (связь), AC-67 (связи) (тесты из T010 [T]; вливается после них)
  Готово-когда: снять xfail AC-33, AC-42, AC-64; гонка добавления → already-taken; rung-ksa-mismatch с candidates; R-41а через marks.validate_marks
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T051 [V] Новые ревизии и смена KSA без ревизии (R-36)
  Срез: US8
  Контракт: C13, C16, C21, C22
  Файлы: BE/course_bank/revisions.py, BE/course_bank/views_revisions.py, BE/course_bank/tests/test_revisions.py
  Зависит от: T047, T048, T004
  Приёмка: AC-37…AC-39 (тесты из T012 [T]; вливается после них)
  Готово-когда: apply под select_for_update по каждой связи; concurrent-change при гонке; размещение остаётся принятым
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 39

- [ ] T052 [V] Отчёт покрытия D-033 (R-37)
  Срез: US8
  Контракт: C16, C21, C22, C23
  Файлы: BE/course_bank/coverage.py, BE/course_bank/views_coverage.py, BE/course_bank/tests/test_coverage.py
  Зависит от: T047, T048, T053
  Приёмка: AC-36 (отчёт) (тесты из T012 [T]; вливается после них)
  Готово-когда: все строки R-37 считаются из читателя, мест, кандидатов и квот; «выдача закрыта» — не из fipi_open_bank
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T053 [V] Гейт 3 по задачам курса и квоты по ступени (R-24)
  Срез: US7
  Контракт: C9, C14, C15; владеет C23
  Файлы: BE/course_bank/quotas.py, BE/course_pipeline/gates/rules_course_task.py, BE/course_pipeline/gates/rules_stages.py#quotas, BE/course_bank/tests/test_quotas.py, BE/course_pipeline/tests/test_gate3_course_tasks.py
  Почему не по контракту (ребро T038): квоты живут в rules_stages.py, который T038 переводит на порт
  Зависит от: T047, T043, T038, T004
  Приёмка: AC-34, AC-63, AC-71, AC-76, AC-77 (тесты из T011 [T]; вливается после них)
  Готово-когда: course-task-placement-unreviewed только у стоящих на ступени, принятых в банке, у связи — активных; шаги и ключ — только свои; квоты по ступени, trap_quota_applies ложна
  Риск: обычный
  Размер: M
  Тест-группа: saga, banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 45

- [ ] T054 [V] Один счёт недостачи для генерации, «Догенерировать» и гейта 3 (R-39)
  Срез: US7
  Контракт: C9, C21, C23
  Файлы: BE/learning_tasks/deficit.py, BE/learning_tasks/top_up.py, BE/learning_tasks/generation_marks.py, BE/learning_tasks/tests/test_deficit_one_count.py
  Зависит от: T053, T047, T034
  Приёмка: AC-35, AC-23 (вторая часть) (тесты из T011 [T]; вливается после них)
  Готово-когда: три потребителя дают один дефицит; невидимые и без ответа место занимают, недостачу не закрывают; ловушки генерации до каталога не пишутся
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T055 [V] Приём своих задач: «Принять задачу» ставит и размещение, approve-placement, сброс при смене ступени или роли (R-34а)
  Срез: US6
  Контракт: C8, C14
  Файлы: BE/services_learning_tasks.py#bulk, BE/tests/test_learning_task_placement.py
  Почему не по контракту (ребро T033): тот же файл services_learning_tasks.py
  Зависит от: T043, T033
  Приёмка: AC-61, AC-62, AC-66 (approve на старом пути), AC-71 (тесты из T010 [T]; вливается после них)
  Готово-когда: снять xfail AC-61, AC-62, AC-71; без флага approve-placement → 422 action not-applicable; version +1 за пункт
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 49

- [ ] T056 [V] Отметки своих задач: проверка R-41а, вид смены в создании, PATCH и ответе (R-41, R-41а, R-41б)
  Срез: US7
  Контракт: C8, C20
  Файлы: BE/services_learning_tasks.py#marks, BE/learning_tasks/answer_forms.py, BE/tests/test_learning_task_marks.py
  Почему не по контракту (ребро T055): тот же файл services_learning_tasks.py
  Зависит от: T055, T004
  Приёмка: AC-74, AC-75 (свои) (тесты из T011 [T]; вливается после них)
  Готово-когда: снять xfail AC-74, AC-75; снятие переноса без вида сбрасывает вид; генерация и импорт пишут без проверки
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T057 [V] Копия курса нового пути: одна транзакция, флаг сразу, KSA без темы, рёбра, ступени и связи ступеней (R-12в)
  Срез: US10
  Контракт: C17
  Файлы: BE/course_structure/clone.py, BE/services.py#clone, BE/course_structure/tests/test_clone_v2.py
  Почему не по контракту (ребро T031): тот же create_course
  Зависит от: T004, T031
  Приёмка: AC-54 (ступени, граф, откат) (тесты из T014 [T]; вливается после них)
  Готово-когда: task_class_map отдаётся в create_course; whole_task_template переводится по картам (relative_to, involves_skill_ids); источник с нарушениями — наследуются, отказ только на новых
  Риск: deep
  Размер: M
  Тест-группа: structure, graph
  Оценка: вес 24 (проба), исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 54

- [ ] T058 [V] Копия курса нового пути: учебный процесс, экзамены, банки, связи на ступенях копии (R-12б пп. 1–3)
  Срез: US10
  Контракт: C1, C3, C4, C24
  Файлы: BE/course_bank/copy.py, BE/learning_process/copy.py, BE/course_bank/tests/test_copy.py
  Почему не по контракту (рёбра T057, T028, T046): копия — сборка писателей трёх срезов
  Зависит от: T057, T028, T046, T001
  Приёмка: AC-54 (остальное) (тесты из T014 [T]; вливается после них)
  Готово-когда: связи копии — те же exam_task и revision, ступени по карте, placement_status всегда ready_for_review; экзамен вне каталога пропущен и пробники выключены
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T059 [V] Позиции КИМ и образцы у итоговой задачи, копия этих полей (R-50, R-12б п. 4)
  Срез: US10
  Контракт: C6, C12, C14
  Файлы: BE/course_goal/services.py, BE/course_goal/serializers.py, BE/course_goal/exam_refs.py, BE/course_goal/tests/test_exam_refs.py
  Зависит от: T001, T004
  Приёмка: AC-50 (тесты из T014 [T]; вливается после них)
  Готово-когда: not-allowed для несвязанного экзамена, unknown-reference для номера вне плана, too-many при 4 образцах; exam_linked:false у снятого
  Риск: обычный
  Размер: M
  Тест-группа: core
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 40

- [ ] T060 [V] «Подобрать умения» по позиции КИМ из банка (R-51)
  Срез: US10
  Контракт: C12, C14
  Файлы: BE/course_goal/services.py#suggest, BE/course_goal/suggest_errors.py, BE/course_goal/tests/test_suggest_by_position.py
  Почему не по контракту (ребро T059): тот же course_goal/services.py
  Зависит от: T059, T003
  Приёмка: AC-51 (тесты из T014 [T]; вливается после них)
  Готово-когда: без вызова ml-llm и без учёта расхода; позиция без KSA → 409 goal-exam-position-ksa-missing, suggest_status=failed
  Риск: обычный
  Размер: S
  Тест-группа: core
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T061 [V] Автопроверки цели: не на верху линии, позиции экзамена без итоговой задачи (R-52)
  Срез: US10
  Контракт: C6, C15
  Файлы: BE/course_pipeline/gates/rules_goal_exam.py, BE/course_pipeline/tests/test_goal_exam_rules.py
  Зависит от: T001, T004
  Приёмка: AC-52 (тесты из T014 [T]; вливается после них)
  Готово-когда: две причины-предупреждения только на флаге
  Риск: обычный
  Размер: S
  Тест-группа: saga
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T062 [V] Форма создания: блоки «Экзамены» и «Учебный процесс» (R-6, R-12а клиент)
  Срез: US11 (клиент US1, US2)
  Контракт: C16, C17
  Файлы: NEW/page.tsx, NEW/LearningProcessFields.tsx, NEW/ExamPicker.tsx, FEA/types/learningProcess.ts, FEA/lib/api/learningProcess.ts, FEA/__tests__/new/learningProcessFields.test.tsx
  Почему не по контракту (ребро T023): тот же page.tsx
  Зависит от: T023
  Приёмка: AC-7 (создание) (тесты из T015 [T]; вливается после них)
  Готово-когда: блоки только при pipelineV2 && !areasWithoutCatalog; пробники и тренажёр недоступны до выбора экзамена; одна отправка с exam_ids и learning_process; общие компоненты LearningProcessFields и ExamPicker
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 55

- [ ] T063 [V] Панель брифа: «Учебный процесс» и «Экзамены», опора и черновик, окно О-3 (R-6, R-13а)
  Срез: US11 (клиент US1, US2)
  Контракт: C16
  Файлы: FE/overview/CourseBriefPanel.tsx, FE/overview/ExamsBlock.tsx, FE/overview/useExamMerge.ts, FE/overview/BanksBlock.tsx, FEA/__tests__/overview/examMerge.test.ts
  Почему не по контракту (ребро T062): общие компоненты блока
  Зависит от: T062
  Приёмка: AC-7 (панель), AC-16, AC-17 (тесты из T015 [T]; вливается после них)
  Готово-когда: слияние ответа записи экзамена с несохранённой формой; окно «Экзамен снят… Снять и банк?» только при bank_selected; заглушка BanksBlock смонтирована
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 40

- [ ] T064 [V] Панель брифа: блок «Банки задач» и решатель (R-18…R-21 клиент)
  Срез: US11 (клиент US3)
  Контракт: C16
  Файлы: FE/overview/BanksBlock.tsx, FEA/types/courseBanks.ts, FEA/lib/api/courseBanks.ts, FEA/__tests__/overview/banksBlock.test.tsx
  Почему не по контракту (ребро T063): BanksBlock смонтирован в панели T063
  Зависит от: T063
  Приёмка: AC-19 (UI), AC-21 (UI) (тесты из T015 [T]; вливается после них)
  Готово-когда: выбранные, предложения, прочие; решатель с одним вариантом «Общий»
  Риск: обычный
  Размер: S
  Тест-группа: frontend
  Оценка: вес 10 (проба), исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T065 [V] Экран «Задачи»: окно ревизий и отчёт покрытия (R-36, R-37 клиент)
  Срез: US11 (клиент US8)
  Контракт: C16
  Файлы: FE/tasks/RevisionsModal.tsx, FE/tasks/CoverageReport.tsx, FE/tasks/TaskClassCoveragePanel.tsx, FE/tabs/TasksTab.tsx#mount2, FEA/__tests__/tasks/coverage.test.tsx
  Почему не по контракту (ребро T024): монтирование в TasksTab.tsx после T024
  Зависит от: T024
  Приёмка: AC-36 (UI), AC-37 (UI) (тесты из T015 [T]; вливается после них)
  Готово-когда: «в банке новые версии задач: N», «изменились умения», «Перейти на новые версии»; отчёт по ступеням и строки курса
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T066 [H] Хвост: реестры документов, журнал, CHANGELOG, README пакетов, правка Пар §3.2, записи ADR-121, передачи шагам 8–10; находки «хвост» дословно
  Срез: —
  Контракт: —
  Файлы: docs/INDEX.md, docs/TAGS.md, docs/journal/, CHANGELOG.md, BE/learning_process/README.md, BE/course_bank/README.md, docs/architecture/methodology/2026-11-17_parametry-i-model-dannyh-kursa.md, docs/architecture/decisions/ADR-121-kurs-banki-zadach-i-reshateli.md
  Зависит от: все задачи T001–T065
  Приёмка: —
  Готово-когда: все находки ревью с вердиктом «можно сливать, хвост» закрыты дословно; docs/INDEX.md и TAGS.md сверены; README пакетов описывают фактическое
  Риск: обычный
  Размер: M
  Тест-группа: governance
  Оценка: вес 15 (проба), исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 15

## 7. Расписание по слотам

Расписание HLFET (`sched.py`): готовая задача с наибольшим рангом пути идёт в свободный слот;
сдача на ревью освобождает слот; ревью 8 мин и вливание 3 мин — вне слота. Числа — без
доработок; с доработками см. §10.

**K = 4, R = 3** (минуты от старта; вход в слот, без доработок)

```
end 290
slot1: T001@0, T021@24, T029@39, T042@49, T035@73, T039@88, T014@103, T010@113, T062@123, T012@138, T046@148, T059@163, T051@178, T052@202, T032@217, T026@227, T061@237, T066@264
slot2: T002@0, T015@24, T033@39, T006@63, T036@73, T040@88, T016@103, T007@113, T057@123, T024@147, T017@162, T027@172, T045@196, T054@212, T018@227, T060@237
slot3: T004@0, T005@15, T022@25, T003@35, T009@50, T034@65, T038@80, T023@95, T047@105, T048@120, T028@135, T053@159, T049@174, T025@198, T058@213, T030@228, T064@238
slot4: T013@0, T008@10, T020@25, T031@35, T043@50, T037@74, T041@89, T011@104, T044@119, T055@143, T063@167, T019@182, T050@198, T065@213, T056@228
   0-30   avg busy 4.00
  30-60   avg busy 4.00
  60-90   avg busy 4.00
  90-120  avg busy 4.00
 120-150  avg busy 4.00
 150-180  avg busy 4.00
 180-210  avg busy 4.00
 210-240  avg busy 3.93
 240-270  avg busy 0.93
 270-300  avg busy 0.30
 300-330  avg busy 0.00
```

**K = 5, R = 4** (минуты от старта; вход в слот, без доработок)

```
end 240
slot1: T001@0, T022@24, T023@34, T042@44, T039@68, T011@83, T048@98, T024@113, T017@128, T051@138, T054@162, T026@177, T061@187, T066@214
slot2: T002@0, T003@24, T029@39, T035@49, T038@64, T016@79, T007@89, T055@99, T053@123, T049@138, T052@162, T018@177, T060@187
slot3: T004@0, T021@15, T031@30, T043@45, T040@69, T047@84, T057@99, T046@123, T027@138, T050@162, T032@177, T056@187
slot4: T013@0, T005@10, T020@20, T006@30, T033@40, T037@64, T014@79, T010@89, T012@99, T028@109, T063@133, T025@148, T058@163, T030@178, T064@188
slot5: T008@0, T015@15, T009@30, T034@45, T036@60, T041@75, T062@90, T044@105, T059@129, T019@144, T045@160, T065@176
   0-30   avg busy 5.00
  30-60   avg busy 5.00
  60-90   avg busy 5.00
  90-120  avg busy 5.00
 120-150  avg busy 5.00
 150-180  avg busy 5.00
 180-210  avg busy 2.67
 210-240  avg busy 0.50
 240-270  avg busy 0.00
```

Что видно в расписании:

- окно К (0–35) занято полностью: К идёт рядом с `[T]` и независимыми срезами;
- T003 при K = 4 стартует на 35-й минуте: ранг у неё ниже, чем у T001, T002, T004, а первые
  потребители (T032, T047) раньше 100-й минуты не нужны;
- занятость 4.0 до ≈ 240-й минуты, дальше хвост: T045, T066 и короткие срезы последней волны.
  Хвост 240–290 — это путь T044 → T045 → T066, а не нехватка работы;
- T045 ждёт и T044, и последнего из режимов, и сторожа T017. Поэтому T017 (вес 10) держим не
  в конце: в момент 0 он готов, но HLFET отдаёт его на 160-ю минуту, а запаса до 196-й ему
  хватает.

## 8. Тесты и документы

**Где пишутся тесты.**

- Приёмочные: `[T]` T005–T015, в момент 0, в `BE/tests/acceptance/step6/` и
  `FEA/tests/e2e/step6-*.spec.ts`. Строгий xfail: тест, который неожиданно прошёл, валит прогон.
  Срез снимает xfail своих AC в своей ветке; ревьюер сверяет, что снятые AC — те, что
  перечислены в `Приёмка:`.
- Модульные — в самом срезе, в `Файлы:` (каталог `tests/` пакета). Проба `hold`
  (`task_pairs.py`) откатывает рабочие файлы среза и требует, чтобы его тесты покраснели.
- Тесты миграций (0301, 0302, 0303) — у владельца миграции, по `scripts/check_migration_tests.py`.
- Общие тесты `courses/tests/` переводит на `make_learning_task` одна задача T041. Остальные срезы
  в этих файлах не пишут, а заводят тесты в каталоге своего пакета.

**Где пишутся документы.**

- В срезе только то, что ревьюер обязан увидеть вместе с кодом: строки реестра кодов (их
  написала T004), docstring публичных функций контракта.
- README и AGENTS.md пакетов: перечень модулей пишет T001, описание — T066.
- `docs/INDEX.md`, `TAGS.md`, журнал, CHANGELOG, правка Пар §3.2, передачи шагам 8–10 — T066.
  Это единственная задача, которой принадлежат реестры документов, поэтому срезы на них не
  конфликтуют.
- `module-map.md` — генерируемое. Его перегенерирует каждый, кто добавил модуль, а при rebase
  файл не сливается, а строится заново.

## 9. Ревью и вливание

- **Ревью.** Пул R = K − 1 (3 при K = 4, 4 при K = 5); при R = 1 и K = 4 медиана 763 мин,
  при R = 2 — 410, при R = 3 — 358, так что пул меньше K − 1 — главное узкое место после работы.
  Ревьюер (`reviewer`) читает дифф против `contracts.md` и `Готово-когда:`. Не больше двух
  кругов; на втором — только дифф доработки (база 0.23.13). Находку «можно сливать, хвост»
  задача не ждёт: её дословно забирает T066.
- **`deep`** (14 задач): T001, T002, T019, T027, T028, T033, T042, T043, T044, T045, T049, T051,
  T055, T057. Их ведёт `implementer-deep`, ревьюит отдельный ревьюер с правом
  `architect` спросить по шву.
- **Перед вливанием** каждой ветки:
  1. `task_pairs.py merge` против всех веток в работе;
  2. `hold` — тесты среза краснеют без его рабочих файлов;
  3. `check.sh` по `Тест-группе:` задачи.

  Полный прогон `courses` (≈ 30 мин) по одной ветке не гоняем.
- **CI партиями.** Партия — 3–4 влитых ветки, по времени ≈ каждые 35–45 мин; при K = 5 ≈
  5–6 веток. Красную партию делим пополам. Без партий 66 полных прогонов дали бы ≈ 33 ч CI.
  Партиями выходит ≈ 9–11 прогонов, они идут фоном и стену не держат, кроме последней партии.
- **Обязательные полные прогоны** — после T044 и после T045: точки, где меняется хранилище
  для всех потребителей. Их вливаем в отдельной партии из одной ветки.
- **Порядок вливания К:** T004 → T001 → T002 → T003. Хуки T004 ссылаются на модули, которых
  ещё нет, а T001 создаёт пакеты, — поэтому T004 вливается с пустыми модулями-заглушками,
  а T001 при rebase их наполняет. Это единственный файловый стык внутри К. Он назван в
  `pair-rules.txt` → `shared`: одинаковые пустые `__init__.py` и модули с одной строкой
  docstring.
- **Трекер Narta.** Задача на каждую T, у `[T]` и `[K]` метки; карточка задачи — поля из §6,
  статус меняет хук после вливания.

## 10. Проба плана (`design.md` §5) — самопроверка

| Проверка | Значение | Норма | Итог |
|---|---|---|---|
| У каждой `[V]` есть `[T]` своей истории | 44 из 44 (через ворота `G`) | все | да |
| Ребро V → V с причиной | 33 ребра, у всех `Почему не по контракту:` или общий файл | все | да |
| `[S]` с «Почему не срез:» | 6 из 6 | все | да |
| `(стек)` только в цепочке `[S]` | 1: T048 → T049 | да | да |
| Пересечение `Файлы:` без пути в графе | 0 | 0 | да |
| Миграции на одном пути | 0301 → 0302 → 0303 | да | да |
| Рост одного реестра в двух задачах | нет: коды, маршруты, привязки — только T004 | нет | да |
| Глубина К | 1 | 1 | да |
| Доля К | 8% W | ≤ 20% | да |
| Число задач К | 4 | 1–3 | **отклонение**, §12 |
| P = W/S | 9.6 | ≥ 2K: 8 (K = 4), 10 (K = 5) | да / предупреждение |
| R | K − 1 | ≥ K − 1 | да |

## 11. Прогноз времени, качества и простоя

**Время.**

| Слотов | Без доработок | p = 0.43 (сегодня) | p = 0.25 (ожидание) | p = 0.15 | + CI и приёмка |
|---|---|---|---|---|---|
| K = 3, R = 2 | — | 464 (p90 483) | 424 | 402 | ≈ +50 |
| K = 4, R = 3 | 290 | 358 (p90 373) | 326 | 310 | ≈ +50 |
| K = 5, R = 4 | 240 | 296 (p90 308) | 270 | 257 | ≈ +50 |

- p — доля задач, вернувшихся с первого ревью; второй круг — с вероятностью 0.4 · p.
- Работа с доработками W' = W(1 + 0.7p) = 1169 вес-мин при p = 0.25.
- Ожидание при p = 0.25:
  - K = 4: ≈ 6.3 ч, в худшем случае ≈ 6.9 ч;
  - K = 5: ≈ 5.3 ч, в худшем ≈ 5.8 ч.
- В деньгах ≈ $280: 18 запусков deep, ≈ 68 обычных, ≈ 86 ревью.

**Качество.** Откуда p ≈ 0.25 вместо 0.43:

- узкие `Готово-когда` с названными тестами;
- `[T]`, написанные до кода, а не после;
- контракты вместо чтения чужих веток.

Чего план не ловит:

- **Ошибку в шве.** Если C8 (порт) неверен, его чинят 9 потребителей. Против этого
  `test_port_equals_columns` и `deep` для T002.
- **Семантику правила версии Р-CT12.** Каждая операция даёт ровно +1, а ступень и шаги
  меняются в двух потребителях. Проверку держит T002 (`test_version_once_per_operation`) и
  AC-73 в T008.
- **Расхождение фронта и сервера.** Его ловит только e2e T015, а он идёт на приёмке, не в CI.
  Клиентские срезы пишутся по формам §6 из C16. Если форма в спеке неполна, расхождение
  всплывёт на стенде.

**Простой и конфликты.**

- **Слоты.** Занятость 3.45 из 4 и 4.2 из 5 за всю фичу. Остаток — хвост T044 → T045 → T066
  и ожидание ревью при доработках.
- **CI.** Фоновой нагрузки ≈ 9–11 полных прогонов. Простоя по CI нет, пока партия не красная.
  Красная партия возвращает ≈ 2 ветки, и это уже в p.
- **Горячие файлы** (§5) — все на цепочках. Внутри цепочки поздний ждёт раннего. Самая
  длинная: `gating.py` T004 → T029 → T038, она и есть критический путь.
- **Внешние конфликты** — вне графа:
  - шаг 8 и сессия ЕГЭ правят те же места: номер миграции, `TaskClassModal.tsx`,
    `exam_tasks/services.py`;
  - номер миграции 0301 берём на момент вливания (C7);
  - T022 и T003 ставим первыми в своих файлах и вливаем рано;
  - нужна сверка с ветками соседей перед стартом, её делает `architect`.
- **Документы.** Узких мест нет, все реестры у T066. Сама T066 длинная (вес 20) и стоит
  на пути. Её можно начинать раньше, по мере вливаний: ADR-121 и передачи шагам 8–10 —
  уже после T049. Вливается она последней.

## 12. Отклонения от процесса и спеки

1. **К — 4 задачи, а не 1–3.** Фича втрое больше обычной (78 AC, ≈ 70 файлов на порт). Три
   задачи К дали бы одну на 40+ вес-мин, и она стала бы путём. Четыре независимые, глубина 1,
   8% W.
2. **`transfer_change_kind` — сразу в 0301**, а не отдельной миграцией, как в спеке: одна
   схемная миграция на шаг. Поле пустое до T043; цепочка миграций короче на одну.
3. **Перенос данных разделён:** T042 — RunPython 0302 и проверочная команда; T043 — хранение
   приёма размещения в порте. Строки на задачи, созданные после 0302, порт создаёт сам
   (`get_or_create`). Без этого T043 ждал бы T042.
4. **C21–C24 принадлежат срезам, не К** — §3, с причиной на каждом ребре.
5. **Фронт режется по экрану против контракта, а не вместе с сервером.** Причина — владение
   `page.tsx` и `CourseBriefPanel.tsx`; склейку держат `[T]` обеих сторон.
6. **Порт сначала на старых колонках (T002), переключение — одной задачей (T044).** Так 9
   потребителей идут параллельно, и каждый вливается зелёным без `CourseTask`.

## 13. Раскрытие

При первой попытке читать базовый коммит оболочка zsh приняла `$C:` за модификатор, и
`git show` вывел дифф коммита. На экран попали frontmatter и первые строки оригинальной
спеки шага 6 и сводка TAGS для шага 8 — оба файла из запретного списка. Разложения по задачам
там не было. Дальше коммит подставлялся только как `${C}`. Разложение базовой линии,
задачи Narta и стенограммы не открывались.
