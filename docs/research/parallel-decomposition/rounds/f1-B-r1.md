# Фича 1 (шаг 6 пайплайна курса): разложение и план. Команда B, круг 1

Дата 2026-11-24. Процесс: `design.md` (сведение A-2 и B-2). Вход:
`feature-1-description.md`, санированная спека `inputs/feature-1/step6-spec-sanitized.md`,
документ переноса и ловушек, код наставника **только на `06a0bbdf4`** (`git show`,
`git ls-tree`, `git grep` по этому коммиту). Запрещённые пути, ветки, задачи Narta и
baseline не открывались.

Проверка плана — скрипт `decomp/f1B/plan.py` (проба по §5 design + событийная модель, 300
прогонов) и `decomp/f1B/sched.py` (точечное расписание HLFET). Все цифры ниже взяты из них.

## 0. Итог за минуту

| Мера | Значение |
|---|---|
| Задач | **63**: 6 `[K]`, 11 `[T]`, 40 `[V]`, 5 `[S]`, 1 `[H]` |
| W (сумма весов) | 1037 мин-весов |
| S (критический путь) | **106**: T001 → T003 → T042 → T033 → T065 |
| P = W/S | **9.8**: норма для K = 4 (≥ 8), предупреждение для K = 5 (< 10) |
| Фаза К | 126 = 12% W (норма ≤ 20%), глубина 2 у двух задач (обосновано, §2) |
| `[T]` | 130 = 13% W |
| Пересечения `Файлы:` у задач без пути | **0** (проверено скриптом по всем 1953 парам) |
| Точечное расписание без доработок | K = 4: 293 мин; K = 5: 242 мин |
| Модель с доработками, p = 0.43 | K = 4, R = 3: **467 мин**, занято 3.44 из 4; K = 5, R = 4: **403 мин**, 4.03 из 5 |
| Модель с доработками, p = 0.25 | K = 4: 384 мин; K = 5: 321 мин |
| Тот же граф, слот держится до вливания (как сейчас) | K = 4: 692 мин, K = 5: 573 мин (p = 0.43) |
| Запусков исполнителя / ревью | ~104 / ~104 при p = 0.43; ~82 / ~82 при p = 0.25 |

Совет: **K = 5, R = 4** (P ≥ 5 разрешает пятого по §1.11; −14% к K = 4). Если ревьюеров
только 3: K = 5, R = 3 даёт 413 мин, почти столько же.

Полная оценка с хвостом CI (последняя партия 15–28 мин) и приёмкой на стенде (~30 мин):
**K = 5: ~6.1–7.7 ч, K = 4: ~7.2–8.8 ч** (нижняя граница при p = 0.25, верхняя при p = 0.43).

## 1. Позиция команды B на этой фиче, коротко

Ширину дало планирование, а не форма задач:
1. **Карта владения** (§5): у каждого файла один владелец на время его жизни в графе. Где
   двум срезам нужен один горячий файл (`services_learning_tasks.py`, `gating.py`,
   `services.py`, `serializers.py`, `CourseBriefPanel.tsx`), ставится ребро порядка, и
   только там, где оно не ложится на критический путь (это проверено расписанием). Либо общее
   выносится в К как точка подключения с заглушкой.
2. **Явный граф с критическим путём**: самая длинная цепочка фичи («задача курса»: порт →
   перевод потребителей → переключение → приём своих задач) разрезана **по владению
   файлами** на 8 параллельных срезов перевода. Без этого она одна занимала бы ~130 мин
   подряд.
3. **Расписание по слотам** (§7) HLFET по рангу пути; доработка получает ранг своей задачи.
4. **Параллельность внутри задачи**: тесты `[T]` пишет другой агент в окне фазы К; сдача
   освобождает слот; механику (пробное слияние, `hold`, `check.sh` своей группы) делает
   скрипт; на этом графе это −33% (692 → 467 мин при K = 4).

## 2. Где я отступаю от `design.md` и почему

| Пункт design | Отступление | Довод |
|---|---|---|
| §3.2 п. 3: задач К 1–3, глубина 1 | 6 задач К; T003 и T006 — глубина 2 (T006 — `(стек)` от T001) | Фича втрое больше модели design (78 AC, 22 среза в модели). Одна К на всё — это L (> 300 строк диффа), а резать её запрещено как раз правилом размера. Глубина 2 не лежит на критическом пути целиком: путь идёт T001 → T003 → …, а ветка T002 → перевод → T052 короче (24 + 15 + 24 + 24 = 87). Фаза К — 12% W при пороге 20%. Стек T006 от T001: T006 берёт у T001 только каркас пакетов (`__init__.py`, имена моделей), а не смысл полей, поэтому каскад отказа T001 по смыслу шва его почти не задевает. Это K → K, а не K → V; запрет design «(стек) от [K] при срезах ≥ 2K» касается K → V. |
| §3.2 п. 5: по сторонам режем только при срезах < 2K | Сервер ∥ клиент у трёх историй: учебный процесс (T025 ∥ T026), экзамены (T029 ∥ T030), приём своих задач (T055 ∥ T056) | Без разреза каждая из них — L (сервер с замком и версией плюс форма со слиянием черновика). Режем по сторонам против контракта без задачи склейки (§2.2 design). У T055 есть ещё одна причина: она на хвосте цепочки «задача курса», и её клиентская половина (T056) уходит с пути целиком, потому что стартует от K. |
| §3.2 п. 1: одна история — один `[V]` | Перевод потребителей на порт (US7) — 8 срезов **по владению файлами**, а не по сценарию | Сценария у перевода нет: это «каждый читатель и писатель зоны X идёт через порт». Срез держит свой кусок AC-68 (сторож) и AC-73, тесты зоны лежат в файлах зоны. Деление по владению — то, что даёт ширину 8 на месте цепочки. |
| §7 п. 1: W' = W × (1 + 0.7p) | Использую модель с повторными отказами | Формула считает один круг. При p = 0.43 модель даёт ~104 запуска на 63 задачи, то есть 1.65 запуска на задачу, а не 1.3. Ближе к W × (1 + 0.7 · p / (1 − p)) = 1.53 W. Это расхождение я прошу проверить на baseline. |
| §3 шаг 12: CI партиями по 3–4 | Партия переменная: всё, что влито с начала прошлой проверки, но не меньше 3 и не больше 6 | 63 вливания по 4 — это 16 проверок по 15–28 мин, то есть 240–450 мин, если проверки идут строго по одной. При 28 мин пропускная способность CI (4/28 = 0.14 вливания в минуту) **ниже** темпа вливаний (63/403 = 0.16). Переменная партия убирает CI с пути, и остаётся только хвост последней партии. |

## 3. Истории и критерии приёмки

| Ист. | Что | AC | `[T]` |
|---|---|---|---|
| US1 | Учебный процесс: хранение, проверки, запись, чтение, блок UI, гейт отправки, вход в тренажёр | 1–7, 9 | T007 |
| US2 | Экзамены курса: каталог, связать/снять, создание с экзаменами, гонка, слияние формы, окно О-3, staff | 8, 10–18 | T008 |
| US3 | Выбранные банки и решатель | 19, 19а, 20, 21, 65 | T009 |
| US4 | Раскладка задач банка | 22–32 | T010 |
| US5 | Связи: ручные действия, приём размещения, ревизии, покрытие, видимость, после публикации | 33, 36–42, 64, 70 | T011 |
| US6 | Гейт 3, один счёт недостачи, квоты по ступени | 34, 35, 63, 76, 77 | T012 |
| US7 | Задача курса: модель, порт, перенос данных, один писатель, удаление колонок, удаление ступени | 55–60, 66–68, 71–73 | T013 |
| US8 | Приём своей задачи и её размещения, разметка, экран «Задачи» | 61, 62, 69, 74, 75, 78 | T014 |
| US9 | Режимы урока и старые курсы | 43–49 | T015 |
| US10 | Цель курса и экзамен | 50–53 | T016 |
| US11 | Копирование курса нового пути | 54 | T017 |

Приёмка шага (e2e на стенде `cc-*` :8092 с фикстурой Е-10, прогон описи Р) — роль
`acceptance` по истории, как только влиты её срезы, и итоговый прогон после T065.

## 4. Карта швов (`contracts.md`)

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| C1 | `CourseLearningProcess` (R-1), умолчания, `learning_process.settings_for(course)` (R-5, только поля выбранного способа) | T001 | T025, T027, T028, T060 |
| C2 | `learning_process.exams.has_current_exam(course, exam_ids=None)`, `linked_exam_count(course)` — через C15 | T006 | T025, T027, T029, T060 |
| C3 | `concurrency.lock_course(course)` и порядок замков R-0 (курс → экзамен → банк → трек) | T001 | T025, T029, T033, T037 |
| C4 | `CourseBank` (R-17) | T001 | T003, T031, T033, T061 |
| C5 | `CourseTask` с `transfer_change_kind` сразу, перечисления `TransferChangeKind`, `CourseTaskPlacementStatus`, `placed_by`; ограничения `ck_course_task_one_source`, `uq_course_task_exam_task`, `ck_course_task_placement_approved` (R-22) | T001 | T003, T035–T038, T051, T052, T054, T061 |
| C6 | `CourseBankLayoutRun` (R-27) | T001 | T033, T034 |
| C7 | `CourseFinalTask.exam_position_refs`, `exemplar_task_ids` (R-50) | T001 | T060, T062–T064 |
| C8 | `ExamCourse.course` → CASCADE (Е-11) | T001 | — |
| C9 | Порт `course_bank/placement.py`, все методы R-23а; до T052 — на колонках `LearningTask` | T002; переключает T052 | T043–T050, T054, T055 |
| C10 | Помощник тестов `make_learning_task(**kw)` через порт | T002 | все `[T]` US7/US8, T043–T050 |
| C11 | `course_bank.reader.course_tasks(...)` → `CourseTaskItem` (все поля R-23, включая `visible`, `has_steps`, `bank_accepted`, `revision_is_current`) | T003 | T031, T034–T038, T041, T042, T052, T061 |
| C12 | `course_bank/quotas.py`: `rung_marks(course)`, `trap_quota_applies(course, tc_id)` (ложна) | T003 | T041, T042, T038 |
| C13 | `course_bank/marks.py`: `validate_marks(state, sent)` (R-41а) | T003 | T035, T055 |
| C14 | `course_bank/places.py`: `rung_places(course)`, `occupancy(course, tc_ids)` (R-28) | T003 | T032, T033, T038, T042 |
| C15 | API банка экзамена: `fipi_task_ids`, `task_ksa_ids_many`, `positions_for`, `position_task_ksa_ids`, `author_exam_catalog`, `course_exam_links`, `accepted_task_ids`, стойкая к гонке `link_course` (Е-2…Е-6, Е-14, Е-16) | T004 | T003, T006, T029, T032, T039, T040, T063 |
| C16 | 7 новых кодов (`added_by: T-2264`), смена `meaning`/`title` у двух кодов квот, `/problems/goal-exam-position-ksa-missing`, подписи `locale/ru/problems.json`, подписи фронта | T005 | все, кто отдаёт эти коды |
| C17 | Регистрация в `gates/registry.py`: `learning-process-exam-missing` (свой гейт отправки, флаг), `course-task-placement-unreviewed` (гейт 3), `goal-target-not-on-line-top` (гейт 1), `goal-exam-positions-uncovered` (гейт «Бриф») — каждая ссылается на свой файл-заглушку `rules_lp_exam.py`, `rules_course_task.py`, `rules_goal_exam.py`; привязка `TASK_CLASS_MODES_MISSING`, `CONTENT_READING_MODE_INVALID` только к старому пути (R-45) | T005 | T027, T041, T064 |
| C18 | Маршруты всех ручек §6 спеки с заглушками 501 (`learning_process/urls.py`, `course_bank/urls.py`, включение в `courses/urls.py`) | T006 | T029, T031, T034–T038 |
| C19 | Поля сериализаторов курса: `learning_process`, `exam_ids` (принимаются, передаются в C20); деталь курса: `learning_process`, `linked_exam_count` | T006 | T020, T025, T029 |
| C20 | `create_course`: одна `transaction.atomic()` на всю ветку, `pipeline_v2` при `Course.objects.create`, вызовы-заглушки в фиксированном порядке: `apply_on_create`, `link_on_create`, затем копии R-12б пп. 0–4 | T006 | T025, T029, T057–T061 |
| C21 | `_clone_course_structure_from_source` перенесена в `course_structure/clone.py` без изменения поведения; `clone_rungs.copy_rungs(source, target, maps) -> task_class_map` (заглушка `{}`); `CourseGraphCopy.task_class_map` | T006 | T057, T058, T061 |
| C22 | `course_bank/layout.py`: `schedule(course, trigger)`, `schedule_and_wait(course, *, timeout)` (заглушки) | T006 | T031, T033, T034, T042 |
| C23 | Слушатель прохождения гейта 1 `course_bank/listeners.py` (заглушка, подключена) | T006 | T033 |
| C24 | Ветка «Подобрать умения» по позициям в `course_goal/views_tasks.py` → `course_goal/exam_ksa.py` (заглушка) | T006 | T063 |
| C25 | Клиент: `types/step6.ts`, поля в `types/courses.ts`; точки монтирования `LearningProcessBlock`, `CourseExamsBlock`, `CourseBanksBlock`, `CourseBankBlock` и его детей; `step6/api.ts`; общий компонент `MarksFields` (вид смены, пояснение ловушки, «без пары») | T005 | T023, T026, T030, T031, T034–T038, T056 |
| C26 | Сторож `scripts/check_step6_writes.py` (R-49): писатели новых моделей; с T052 — `CourseTask` вне `course_bank` и поля `LearningTask`; с T053 — режимы урока | T002 → T052 → T053 | все |

Правило поправки — только добавлением (ADR-0019). Срез, которому не хватило шва,
докладывает и доделывает своё.

## 5. Задачи

Вес: 10 мин × 1.6 (deep) × 1.5 (M). Ожидаемая длительность запуска: S обычный 7–10 мин,
M обычный 10–15, S deep 11–17, M deep 16–25. Миграция: номер даётся при вливании
(Е-9), зависимость — на голову дерева. Пути — от `services/django-api/courses/`
(`BE/`) и `services/frontend/app/(lk)/my-courses/` (`FE/`, `CID/` — `FE/[courseId]/_components/`).

### Фаза К (старт 0)

- [ ] T001 [K] Схема шага 6: модели, одна миграция, каркас пакетов
  Контракт: владелец C1, C3–C8
  Файлы: BE/learning_process/{__init__,models,settings}.py, BE/course_bank/{__init__,models}.py, BE/migrations/0301_step6_schema.py, BE/course_goal/models.py, BE/exam_codifier/models.py, BE/concurrency.py, BE/tests/_step6_factories.py, docs/engineering/module-tiers.json, module-boundaries.json (+ module-map.md — генерируемое)
  Сущность: CourseLearningProcess, CourseBank, CourseTask, CourseBankLayoutRun, CourseFinalTask, ExamCourse
  Миграция: да (единственная схемная миграция фичи)
  Зависит от: —
  Готово-когда: миграция накатывается и откатывается; ограничения CourseTask ловят обе ссылки, ни одной, повтор задачи банка, `approved` без даты (тесты краснеют на откате ограничений); `settings_for` без строки отдаёт умолчания R-1; `lock_course` берёт строку курса
  Риск: deep · Размер: M · Тест-группа: django:courses
- [ ] T002 [K] Порт размещения на колонках `LearningTask`, помощник тестов, сторож писателей
  Контракт: владелец C9, C10, C26 (первая ступень)
  Файлы: BE/course_bank/placement.py, BE/tests/_learning_tasks_fixture.py, scripts/check_step6_writes.py, .pre-commit-config.yaml
  Зависит от: — (порт не трогает новые модели; `course_bank/__init__.py` — T001, поэтому вливается после T001)
  Готово-когда: каждый метод R-23а покрыт тестом на колонках; правило версии Р-CT12 (`move`, `detach` +1 под `select_for_update`, внутри PATCH — 0); сторож ловит запись новых моделей вне пакета
  Риск: deep · Размер: M · Тест-группа: django:course_bank
- [ ] T004 [K] API банка экзамена для курса (часть работы сессии ЕГЭ)
  Контракт: владелец C15
  Файлы: BE/exam_tasks/services.py, BE/exam_codifier/services.py, их tests/test_course_api.py
  Зависит от: —
  Готово-когда: `fipi_task_ids` — только собственное происхождение ФИПИ (`derived_from` не в счёт); пакетные функции — один запрос (`assertNumQueries`); `position_task_ksa_ids` — только `active`; `accepted_task_ids` — `active`, не дубликат, доверенный ответ; `link_course` при гонке — своё исключение «уже связан»
  Риск: обычный · Размер: M · Тест-группа: django:exam
- [ ] T005 [K] Реестры и регистрация: коды, подписи, гейты, точки клиента
  Контракт: владелец C16, C17, C25
  Файлы: services/django-api/config/{response-codes.json, api-problems.json, locale/ru/problems.json}, .claude/response-codes.json, BE/course_pipeline/gates/{registry.py, rules_lp_exam.py, rules_course_task.py, rules_goal_exam.py}, services/frontend/types/{courses.ts, step6.ts}, FE/new/page.tsx, CID/overview/CourseBriefPanel.tsx, CID/tabs/TasksTab.tsx, CID/step6/{api.ts, MarksFields.tsx, mounts.tsx}, services/frontend/utils/problemLabels.ts
  Мера: реестр кодов, реестр правил гейтов
  Зависит от: —
  Готово-когда: `check_codes.py`, `check_problem_catalog.py` зелёные; правила-заглушки зарегистрированы и молчат; R-45 привязан к старому пути (AC-47 — тест в T015); точки монтирования на флаге отрисовывают пустые блоки, без флага ничего; `MarksFields` с тестом jest
  Риск: обычный · Размер: M · Тест-группа: frontend + django:pipeline
- [ ] T003 [K] Читатель задач курса, квоты, места, проверка отметок
  Почему не одна: читатель читает таблицу T001, свои задачи берёт через порт T002, приём в банке — через T004; вместе с ними это L
  Контракт: владелец C11–C14
  Файлы: BE/course_bank/{reader,quotas,marks,places}.py, BE/course_bank/tests/test_reader.py
  Зависит от: T001, T002, T004
  Готово-когда: один запрос на вид источника (тест числа запросов на 50 задачах); DTO своей задачи до T052 — из порта; `trap_quota_applies` ложна; `rung_places` 11/15
  Риск: deep · Размер: M · Тест-группа: django:course_bank
- [ ] T006 [K] Точки подключения в общих файлах сервера
  Почему не одна: правит существующие горячие файлы (`services.py`, `serializers.py`, `views.py`, `urls.py`, `clone.py`), а T001 — новые; вместе это L
  Контракт: владелец C2, C18–C24
  Файлы: BE/{urls,serializers,services,views}.py, BE/course_structure/clone.py, BE/course_goal/views_tasks.py, BE/learning_process/{urls,views,exams,services,copy}.py, BE/course_bank/{urls,views,layout,listeners,copy}.py, BE/course_goal/exam_ksa.py, BE/course_structure/clone_rungs.py
  Зависит от: T004; T001 (стек)
  Готово-когда: все ручки §6 отвечают 501 на флаге и прежним образом без флага; `create_course` — одна транзакция (тест: сбой в заглушке копии → курса нет, число курсов то же); эталон `copy.json` старого пути не изменён; перенос `_clone_…` — без изменения поведения (весь `course_structure` зелёный)
  Риск: deep · Размер: M · Тест-группа: django:courses

### `[T]` — независимые приёмочные тесты (Sonnet, в окне фазы К)

Одна на историю: тесты по `AC-n` против `contracts.md` и спеки, строгий xfail
(`strict=True`, импорт кода внутри теста), UI-критерии — e2e Playwright `test.fails`.
Код К не читают. Вливаются до срезов своей истории.

| Задача | Ист. | Файлы | Размер |
|---|---|---|---|
| T007 | US1 | BE/tests/acceptance/step6/us1/, FE e2e `tests/e2e/step6/us1.spec.ts` | S |
| T008 | US2 | …/us2/ (+ e2e AC-16, AC-17) | S |
| T009 | US3 | …/us3/ | S |
| T010 | US4 | …/us4/ (AC-26 — два потока, `TransactionTestCase`) | M |
| T011 | US5 | …/us5/ | S |
| T012 | US6 | …/us6/ | S |
| T013 | US7 | …/us7/ (тест миграции по `check_migration_tests.py`, AC-57) | M |
| T014 | US8 | …/us8/ (+ e2e AC-69, AC-78) | S |
| T015 | US9 | …/us9/ (AC-49 — команда, все ветки) | M |
| T016 | US10 | …/us10/ | S |
| T017 | US11 | …/us11/ (AC-54 целиком, источник с циклом) | M |

Риск у всех обычный, Тест-группа: django:acceptance (новая группа реестра тестов).

### US9 Режимы урока и старые курсы

- [ ] T020 [V] Запись и ответы курса без режимов (R-43, сервер)
  Срез: US9 / «автор больше не выбирает режимы»
  Файлы: BE/{serializers,services,views}.py, BE/course_pipeline/course_patch.py, BE/admin.py, BE/domain_errors/__init__.py, BE/management/commands/{seed_tariff_testbed,seed_ksa_tc_testbed,prepare_t1142_manual,prepare_t1144_purchase_manual}.py
  Зависит от: T006 (общие файлы), T050 (общий `seed_course_pipeline.py`: правит T050, здесь не трогается)
  Приёмка: AC-43 (сервер)
  Готово-когда: деталь без `allowed_lesson_modes`/`prefer_pbl`; присланные поля — как неизвестные; копия курса не копирует их; xfail AC-43 (сервер) снят
  Риск: обычный · Размер: M · Тест-группа: django:courses
- [ ] T021 [V] Читатели режимов — константа (R-42)
  Срез: US9 / «у каждого курса оба режима»
  Файлы: BE/topic_content/lesson_modes.py, BE/lesson/{serializers,streaming}.py, BE/lesson/mode_a/services.py, BE/track_manage/{read,serializers}.py, BE/structure_gen/{skeleton,tasks}.py, BE/task_classes/{rung_layout,rung_layout_db}.py, BE/course_graph_editor/read.py
  Зависит от: —
  Приёмка: AC-44, AC-43 (ученик бывшего `["A"]`)
  Готово-когда: grep по читателям пуст (кроме сторожа); AC-44 зелёный и краснеет на откате константы
  Риск: обычный · Размер: M · Тест-группа: django:lessons
- [ ] T022 [V] Инвариант «линия А без чтения» по флагу и окно ступени на флаге (R-44, R-48 сервер)
  Срез: US9 / «флаговый курс не получает блокер чтения»
  Файлы: BE/graph_invariants/structure_gate.py, BE/task_classes/services.py
  Зависит от: —
  Приёмка: AC-45, AC-46 (API), AC-47
  Риск: обычный · Размер: S · Тест-группа: django:graph
- [ ] T023 [V] Клиент без режимов: форма, панель, окно ступени, уроки (R-43, R-48 клиент)
  Срез: US9 / клиент
  Файлы: CID/structure/{TaskClassModal,TopicTreePanel}.tsx, FE/new/page.tsx, CID/overview/{CourseBriefPanel.tsx, briefFieldLabels.ts, briefConsistency.ts}, services/frontend/{config/courseCreation.ts, utils/auth.ts, utils/tracks.ts, types/courses.ts}, app/(lk)/lessons/[lessonId]/{page.tsx, lessonStopPlan.ts, _components/mode-a/types.ts} и их тесты в `__tests__/`
  Зависит от: T005 (точки монтирования в тех же файлах)
  Приёмка: AC-43 (UI), AC-46 (UI)
  Риск: обычный · Размер: M · Тест-группа: frontend
- [ ] T024 [V] Команда `unpublish_legacy_courses` (R-47а)
  Срез: US9 / «старые курсы сняты с публикации и возвращены с модерации»
  Файлы: BE/management/commands/unpublish_legacy_courses.py (+ тест)
  Зависит от: —
  Приёмка: AC-49
  Риск: deep (права, сага) · Размер: M · Тест-группа: django:saga

### US1 Учебный процесс

- [ ] T025 [V] Учебный процесс: проверки, запись под версией курса, чтение (R-1…R-5, сервер)
  Срез: US1 / «автор правит учебный процесс в панели и при создании»
  Контракт: C1, C2, C3, C19, C20
  Файлы: BE/learning_process/{services,validation,serializers}.py
  Зависит от: T006
  Приёмка: AC-1…AC-6, AC-8 (часть `mock_enabled` без экзамена)
  Готово-когда: каждый код R-2 своим тестом; 409 на чужой версии; без флага 422 `not-applicable`; модерация — прежняя заморозка
  Риск: deep (замок, версия) · Размер: M · Тест-группа: django:learning_process
- [ ] T026 [V] Блок «Учебный процесс» (R-6, клиент)
  Срез: US1 / клиент против C19, C25
  Файлы: CID/step6/LearningProcessBlock.tsx (+ тест jest)
  Зависит от: T005
  Приёмка: AC-7
  Риск: обычный · Размер: M · Тест-группа: frontend
- [ ] T027 [V] Гейт отправки «пробники и тренажёр ⇒ экзамен» и готовность заранее (R-7)
  Срез: US1 / «отправка останавливается, автор видит причину заранее»
  Файлы: BE/course_pipeline/{gate_journal,gating}.py, BE/publication/views.py, BE/course_pipeline/gates/rules_lp_exam.py, CID/tabs/PublishTab.tsx
  Зависит от: T005, T006, T046 (тот же `gating.py` и `publication/views.py` переводит на порт T046)
  Приёмка: AC-9
  Риск: deep · Размер: M · Тест-группа: django:pipeline
- [ ] T028 [V] Вход в «Тренажёр ЕГЭ» из курса (Е-15)
  Срез: US1 / «ученик входит в тренажёр, если курс его включил»
  Файлы: BE/exam_trainer/services.py, app/(lk)/courses/[id]/{page.tsx, ExamTrainerEntry.tsx}
  Зависит от: T001 (C1)
  Приёмка: R-9 (тест в T007)
  Риск: обычный · Размер: M · Тест-группа: django:exam

### US2 Экзамены курса

- [ ] T029 [V] Экзамены курса, сервер: каталог, список, связать, снять, создание с экзаменами (R-10…R-14, R-12а)
  Срез: US2 / сервер против C2, C15, C18–C20
  Файлы: BE/learning_process/{exams,views_exams,catalog}.py
  Зависит от: T006
  Приёмка: AC-8, AC-10…AC-15, AC-18, AC-14 (staff — только проверка 405)
  Готово-когда: гонка двух потоков — одна 201, другая 422 (не 500); 404/403 по правам чтения и правки; версия курса +1 при связывании и снятии
  Риск: deep (права, гонка) · Размер: M · Тест-группа: django:learning_process
- [ ] T030 [V] Экзамены курса, клиент: блок, выбор при создании, слияние с черновиком, окно О-3 (R-6, R-13а)
  Срез: US2 / клиент против C25
  Файлы: CID/step6/{CourseExamsBlock.tsx, briefDraftMerge.ts, ExamUnlinkDialog.tsx}
  Зависит от: T005
  Приёмка: AC-16, AC-17
  Риск: обычный · Размер: M · Тест-группа: frontend

### US3, US4, US5 Банки, раскладка, связи

- [ ] T031 [V] Выбранные банки и решатель (R-11 `bank_selected`/`bank_task_count`, R-17…R-21)
  Файлы: BE/course_bank/{banks,views_banks}.py, CID/step6/CourseBanksBlock.tsx
  Зависит от: T003, T006
  Приёмка: AC-19, AC-19а, AC-20, AC-21, AC-65
  Риск: обычный · Размер: M · Тест-группа: django:course_bank
- [ ] T032 [S] Раскладка: расчёт кандидатов (R-25, R-26, R-29, R-30)
  Почему не срез: одна функция отбора; запись под замком (T033) без неё не проверить
  Файлы: BE/course_bank/layout_calc.py
  Зависит от: T003
  Приёмка: AC-25, AC-27…AC-30
  Риск: обычный · Размер: M · Тест-группа: django:course_bank
- [ ] T033 [S] Раскладка: запись под замком, Celery, журнал, запуски (а)(б)(в) (R-27, R-28)
  Файлы: BE/course_bank/{layout,layout_run,listeners,tasks}.py
  Зависит от: T006, T042 (вызов из генерации); T032 (стек)
  Приёмка: AC-22 (сервер), AC-23, AC-24, AC-26, AC-31, AC-32
  Готово-когда: два параллельных прогона не превышают мест (`TransactionTestCase`); прогон с ошибкой пишет `failed`
  Риск: deep (конкурентность) · Размер: M · Тест-группа: django:course_bank
- [ ] T034 [V] «Подобрать ещё из банка» и блок «Задачи из банка» (R-27 ручной запуск, R-29 остаток)
  Файлы: BE/course_bank/{views_layout,candidates}.py, CID/step6/CourseBankBlock.tsx
  Зависит от: T032 (функция отбора), T006, T005
  Приёмка: AC-22 (UI)
  Риск: обычный · Размер: M · Тест-группа: django:course_bank
- [ ] T035 [V] Ручное добавление и правка связи (R-31, R-32, R-35, R-38, R-41а для связей)
  Файлы: BE/course_bank/{links,views_links}.py, CID/step6/LinkDialogs.tsx
  Зависит от: T003, T006, T005
  Приёмка: AC-30 (ручное), AC-42, AC-74/75 (связь)
  Риск: обычный · Размер: M · Тест-группа: django:course_bank
- [ ] T036 [V] Приём и отклонение размещения связей, возврат отклонённой (R-33, R-34)
  Файлы: BE/course_bank/{links_bulk,views_bulk}.py, CID/step6/{LinkBulkBar,RejectedLinks}.tsx
  Зависит от: T003, T006, T005
  Приёмка: AC-33, AC-64
  Риск: обычный · Размер: M · Тест-группа: django:course_bank
- [ ] T037 [V] Новые ревизии и «изменились умения» (R-36)
  Файлы: BE/course_bank/{revisions,views_revisions}.py, CID/step6/RevisionsModal.tsx
  Зависит от: T003, T006, T005
  Приёмка: AC-37, AC-38, AC-39
  Риск: deep (гонка перехода) · Размер: M · Тест-группа: django:course_bank
- [ ] T038 [V] Отчёт покрытия D-033 (R-37)
  Файлы: BE/course_bank/{coverage,views_coverage}.py, CID/step6/CoverageReport.tsx
  Зависит от: T003, T006, T005
  Приёмка: AC-36 (отчёт), AC-40 (строка отчёта)
  Риск: обычный · Размер: M · Тест-группа: django:course_bank
- [ ] T039 [V] Видимость задач на основе ФИПИ (Е-17)
  Файлы: BE/exam_tasks/services.py (`_learner_origin_q`)
  Зависит от: T004 (тот же файл)
  Приёмка: AC-70, AC-40 (вторая часть), AC-41 (сторож)
  Риск: обычный · Размер: S · Тест-группа: django:exam
- [ ] T040 [V] Фикстура стенда Е-10
  Файлы: BE/exam_tasks/management/commands/seed_step6_exam_fixture.py
  Зависит от: T004
  Готово-когда: команда идемпотентна; на `cc_concept` даёт состав Е-10 (SELECT в докладе)
  Риск: обычный · Размер: S · Тест-группа: django:exam

### US6 Гейт 3 и недостача

- [ ] T041 [V] Гейт 3 по задачам курса и квоты по ступени (R-24, R-41б)
  Файлы: BE/course_pipeline/gates/{rules_stages,rules_course_task}.py, BE/course_pipeline/gating.py, config/response-codes.json и locale (только `meaning`/`title` двух кодов квот)
  Зависит от: T003, T005, T046 (тот же `rules_stages.py`/`gating.py`), T027 (тот же `gating.py`)
  Приёмка: AC-34, AC-63 (связи и своя задача, не принятая в банке), AC-76, AC-77 (гейт)
  Риск: обычный · Размер: M · Тест-группа: django:pipeline
- [ ] T042 [V] Один счёт недостачи; генерация после раскладки; квоты генератора (R-39, R-27 (в))
  Файлы: BE/learning_tasks/{deficit,top_up,generation_marks}.py, BE/services_learning_tasks.py (место вызова генерации)
  Зависит от: T003, T006 (C22), T045 и T043 (те же файлы переводят на порт)
  Приёмка: AC-35, AC-77 (генератор)
  Готово-когда: ожидание раскладки с пределом (тест: заглушка C22 висит → генерация идёт по пределу и считает по записанному)
  Риск: deep (ожидание с пределом) · Размер: M · Тест-группа: django:learning_tasks

### US7 Задача курса

Перевод потребителей на порт: 8 срезов по владению, каждый зависит только от T002.
Поведение не меняется (порт на колонках), поэтому порядок между ними не нужен.
Тесты зоны (в том числе модули `courses/tests/test_*` о ней) — в срезе зоны; новые задачи в
тестах — через `make_learning_task`.

| Задача | Зона и файлы | Риск/Размер | Доп. зависимость |
|---|---|---|---|
| T043 | `services_learning_tasks.py` (CRUD, PATCH, пачка, сериализация) | обычный M | — |
| T044 | импорт: `_lt_import.py`, `lt_import.py`, `services_lt_import.py`, `documents/{models,services}.py` | обычный M | — |
| T045 | `learning_tasks/*` (answer_forms, deficit, generation_marks, selection, solution_check, top_up), `learning_task_solver/{author,button,generation,solve_job}.py` | обычный M | — |
| T046 | `course_pipeline/{auto_pipeline,gating,views}.py`, `gates/{facts,rules_stages,rules_structure}.py`, `saga/{events,reopen}.py`, `publication/views.py` | обычный M | — |
| T047 | `task_classes/{rung_switch,delete_preview}.py` (`relocate`, `detach_or_delete`, правило версии) | deep S | — |
| T048 | `task_classes/{predicates,rung_layout_db,rung_rule,services,topic_merge}.py` | обычный M | T021, T022 (общие файлы) |
| T049 | `course_structure/{editor,generation,rung_layout}.py`, `course_graph_editor/{delete_preview,read,write}.py` (в том числе `bulk_create` + `register`), `structure_gen/{skeleton,tasks}.py` | обычный M | T021 |
| T050 | `dialogue/{item_materialization,lesson_setup,orchestrator_b}.py`, `topic_content/{generation/context,generation/services,lesson_modes,passthrough,services}.py`, `track_manage/{models,planner}.py`, команды и сиды (`archive_non_whole_task_learning_tasks`, `learning_task_target_audit`, `repair_tc_complexity_per_line`, `rung_rule_report`, `seed_course_pipeline`, `seed_t815_demo`, `solution_steps_report`) | обычный M | T021 |

Общее для T043–T050: `Срез: US7 / потребители зоны пишут и читают ступень и роль только
через порт`; `Приёмка: AC-68 (по зоне), AC-73 (T043, T047), AC-60 (T043, T044, T049, T050)`;
`Готово-когда: grep по зоне не находит обращений к полям LearningTask task_class/is_trap/
is_transfer/trap_note (ORM); тесты зоны зелёные без правки ожиданий`.

- [ ] T051 [S] Перенос своих задач в задачи курса (R-22а) и проверочная команда
  Почему не срез: миграция данных
  Файлы: BE/migrations/03xx_course_task_from_learning_task.py, BE/management/commands/check_learning_task_course_alignment.py, BE/tests/test_migration_course_task_transfer.py
  Миграция: да (после T001)
  Зависит от: T001
  Приёмка: AC-56, AC-57
  Готово-когда: сверки (а)–(д) внутри миграции; повтор — 0 строк; обратная возвращает колонки; исторические модели, без импорта из `task_classes`/`course_bank`
  Риск: deep · Размер: M · Тест-группа: django:courses
- [ ] T052 [S] Переключение порта и читателя на `CourseTask`; `register` пишет; сторож полей
  Почему не срез: точка, где вторая правда о ступени исчезает; ждёт всех потребителей
  Файлы: BE/course_bank/{placement,reader}.py, scripts/check_step6_writes.py
  Зависит от: T043–T050, T051, T003
  Приёмка: AC-58, AC-60, AC-66, AC-68, AC-71, AC-72, AC-73 (после переключения)
  Готово-когда: весь `django:*` зелёный без правки тестов потребителей (это и есть проверка, что вызывающий код не меняется); новые методы порта `approve_placement`, `placement_of`
  Риск: deep · Размер: M · Тест-группа: django:* (полный прогон партии)
- [ ] T053 [S] Удаление колонок: `learning_task` (R-22б) и режимов курса и брифа (R-47)
  Почему не срез: удаление после перевода всех читателей; одним выпуском (спека)
  Файлы: BE/models.py, BE/migrations/03yy_drop_lt_marks_and_lesson_modes.py, scripts/check_step6_writes.py
  Миграция: да
  Зависит от: T052, T020, T021, T022, T023, T024
  Приёмка: AC-48, AC-59
  Риск: deep · Размер: S · Тест-группа: django:*
- [ ] T054 [V] Удаление ступени и темы при задачах курса (R-22 `detach_links`)
  Файлы: BE/course_bank/detach.py, BE/course_structure/{deletion,rung_layout}.py, BE/task_classes/rung_switch.py
  Зависит от: T003, T047, T049 (те же файлы)
  Приёмка: AC-67
  Риск: deep (версия) · Размер: S · Тест-группа: django:graph

### US8 Приём своих задач

- [ ] T055 [V] Приём своей задачи и её размещения, сервер (R-34а, R-41а для своих)
  Срез: US8 / сервер; половина среза по сторонам (на пути, §2)
  Файлы: BE/services_learning_tasks.py, BE/course_bank/placement.py (только вызов новых методов — их завёл T052)
  Зависит от: T052, T042 (тот же файл)
  Приёмка: AC-61, AC-62, AC-63 (своя задача), AC-71, AC-74, AC-75 (своя)
  Риск: deep (права, версия) · Размер: M · Тест-группа: django:learning_tasks
- [ ] T056 [V] Экран «Задачи» для своих задач, клиент (AC-69, AC-78)
  Файлы: CID/tasks/{EditLearningTaskModal,BulkBar,InboxLT,CreateLearningTaskModal,TreeGroupedPool}.tsx
  Зависит от: T005 (C25, `MarksFields`)
  Приёмка: AC-69, AC-78
  Риск: обычный · Размер: M · Тест-группа: frontend

### US11 Копирование курса

- [ ] T057 [V] Копия графа: KSA без темы, `CompetencyKSA` по компетенции, рёбра, порядок (R-12в пп. 3, 8)
  Файлы: BE/course_structure/clone.py
  Зависит от: T006 (функция перенесена в этот файл)
  Приёмка: AC-54 (граф)
  Риск: deep · Размер: M · Тест-группа: django:graph
- [ ] T058 [V] Копия ступеней и связей ступени с переводом шаблона по картам (R-12в пп. 4, 5, 7)
  Файлы: BE/course_structure/clone_rungs.py
  Зависит от: T006 (C21: сигнатура и карты)
  Приёмка: AC-54 (ступени, шаблон, `STATE_STALE`, линии)
  Риск: deep · Размер: M · Тест-группа: django:graph
- [ ] T059 [V] Копия наследует нарушения источника (В-23 (а))
  Файлы: BE/course_structure/guard.py
  Зависит от: —
  Приёмка: AC-54 (источник с циклом)
  Риск: deep · Размер: S · Тест-группа: django:graph
- [ ] T060 [V] Копия учебного процесса, экзаменов и ссылок итоговых задач (R-12б пп. 1, 2, 4)
  Файлы: BE/learning_process/copy.py, BE/course_goal/services.py (`copy_course_goal`)
  Зависит от: T006, T029 (копия зовёт писателя связи R-12, а не свою копию — R-49)
  Приёмка: AC-54 (учебный процесс, экзамены, позиции)
  Риск: обычный · Размер: M · Тест-группа: django:learning_process
- [ ] T061 [V] Копия банков и связей банка по карте ступеней (R-12б п. 3)
  Файлы: BE/course_bank/copy.py
  Зависит от: T006, T003, T031 (писатель банка), T058 (карта ступеней)
  Приёмка: AC-54 (связи на ступенях копии, `ready_for_review`)
  Риск: deep · Размер: M · Тест-группа: django:course_bank

### US10 Цель курса и экзамен

- [ ] T062 [V] Позиции КИМ и образцы у итоговой задачи (R-50), сервер и блок итоговых задач
  Файлы: BE/course_goal/{services_tasks,serializers_positions}.py, CID/overview/{FinalTasksBlock.tsx, finalTasks.ts}
  Зависит от: T006, T005
  Приёмка: AC-50
  Риск: обычный · Размер: M · Тест-группа: django:course_goal
- [ ] T063 [V] «Подобрать умения» по позиции КИМ (R-51)
  Файлы: BE/course_goal/exam_ksa.py
  Зависит от: T004, T006
  Приёмка: AC-51
  Риск: обычный · Размер: S · Тест-группа: django:course_goal
- [ ] T064 [V] Две автопроверки цели (R-52)
  Файлы: BE/course_pipeline/gates/rules_goal_exam.py
  Зависит от: T005
  Приёмка: AC-52, AC-53 (чтение диффа — ревьюер)
  Риск: обычный · Размер: S · Тест-группа: django:pipeline

### Хвост

- [ ] T065 [H] Реестры документов, журнал, находки «хвост», правки источников по §8 спеки
  Файлы: docs/INDEX.md, CHANGELOG.md, docs/journal/, README и AGENTS новых пакетов (финальная сверка), записи координатора в Ж, Пар §3.2, ADR-121 (только отметки «Спросить»)
  Зависит от: все `[V]`/`[S]`
  Риск: обычный · Размер: S · Тест-группа: docs

## 6. Карта владения горячих файлов

| Файл | Владельцы по порядку (путь в графе) |
|---|---|
| `courses/services.py`, `serializers.py`, `views.py` | T006 → T020 |
| `services_learning_tasks.py` | T043 → T042 → T055 |
| `course_pipeline/gating.py` | T046 → T027 → T041 |
| `gates/rules_stages.py` | T046 → T041 |
| `gates/registry.py` | только T005 |
| `config/response-codes.json`, `locale/ru/problems.json` | T005 → T041 (две строки `meaning`/`title`) |
| `publication/views.py` | T046 → T027 |
| `task_classes/rung_switch.py` | T047 → T054 |
| `task_classes/services.py` | T022 → T048 |
| `course_structure/rung_layout.py` | T049 → T054 |
| `course_structure/clone.py` | T006 → T057 |
| `learning_tasks/{deficit,top_up,generation_marks}.py` | T045 → T042 |
| `structure_gen/*`, `course_graph_editor/read.py`, `topic_content/lesson_modes.py`, `task_classes/rung_layout_db.py` | T021 → T048/T049/T050 |
| `seed_course_pipeline.py` | T050 (сиды режимов правит там же, T020 его не трогает) |
| `exam_tasks/services.py` | T004 → T039 |
| `course_bank/placement.py` | T002 → T052 → T055 |
| `course_bank/reader.py` | T003 → T052 |
| `scripts/check_step6_writes.py` | T002 → T052 → T053 |
| `models.py` (`LearningTask`, `Course`, `Brief`) | только T053 |
| `FE/new/page.tsx`, `CourseBriefPanel.tsx` | T005 → T023 |
| `CID/tabs/TasksTab.tsx` | только T005 |
| `types/courses.ts` | T005 → T023 |

Общие генерируемые (`shared` в `pair-rules.txt`): `docs/engineering/module-map.md`,
`docs/engineering/test-registry.json`, схема API. При rebase их перегенерируют, а не
сливают руками.

Что карта не видит, и как это закрыто:
- **Одна сущность** — все модели и поля в T001, `LearningTask` трогает только T053.
- **Одна мера** — реестр кодов и реестр правил гейтов растит только T005; T041 меняет
  `meaning` у двух существующих кодов (путь T005 → T041).
- **Миграции** — T001, T051, T053, и они лежат на одном пути (T001 → T051 → T052 → T053).
  Соседи (шаг 8, сессия ЕГЭ) пишут в ту же цепочку: номер даётся при вливании.
- **Смысловое пересечение** (вторая копия правила ступени, второй счёт мест) — швы C11–C14
  в К; ревьюеру среза называются ветки в полёте с тем же `Контракт:`.

## 7. Расписание по слотам (точечное, HLFET, без доработок)

K = 5, R = 4, ревью 8, вливание 2. Окончание — 242 мин (K = 4 — 293, K = 3 — 379).

```
T001 [K] слот 1:     0–   24, влита    34
T002 [K] слот 2:     0–   24, влита    34
T015 [T] слот 3:     0–   15, влита    25
T004 [K] слот 4:     0–   15, влита    25
T013 [T] слот 5:     0–   15, влита    25
T021 [V] слот 4:    15–   30, влита    40
T022 [V] слот 5:    15–   25, влита    35
T017 [T] слот 3:    15–   30, влита    42
T012 [T] слот 1:    24–   34, влита    44
T005 [K] слот 2:    24–   39, влита    49
T010 [T] слот 5:    25–   40, влита    50
T006 [K] слот 3:    30–   54, влита    64
T007 [T] слот 4:    30–   40, влита    50
T008 [T] слот 1:    34–   44, влита    54
T051 [S] слот 2:    39–   63, влита    73
T003 [K] слот 4:    40–   64, влита    74
T047 [V] слот 5:    40–   56, влита    66
T043 [V] слот 1:    44–   59, влита    69
T044 [V] слот 3:    54–   69, влита    79
T045 [V] слот 5:    56–   71, влита    81
T046 [V] слот 1:    59–   74, влита    84
T048 [V] слот 2:    63–   78, влита    88
T049 [V] слот 4:    64–   79, влита    89
T050 [V] слот 3:    69–   84, влита    94
T009 [T] слот 5:    71–   81, влита    91
T058 [V] слот 1:    74–   98, влита   108
T024 [V] слот 2:    78–  102, влита   112
T029 [V] слот 4:    79–  103, влита   113
T031 [V] слот 5:    81–   96, влита   106
T042 [V] слот 3:    84–  108, влита   118
T052 [S] слот 5:    96–  120, влита   130
T032 [S] слот 1:    98–  113, влита   123
T027 [V] слот 2:   102–  126, влита   136
T011 [T] слот 4:   103–  113, влита   123
T014 [T] слот 3:   108–  118, влита   128
T023 [V] слот 4:   113–  128, влита   138
T020 [V] слот 1:   113–  128, влита   138
T016 [T] слот 3:   118–  128, влита   138
T025 [V] слот 5:   120–  144, влита   154
T057 [V] слот 2:   126–  150, влита   160
T037 [V] слот 3:   128–  152, влита   162
T061 [V] слот 1:   128–  152, влита   162
T033 [S] слот 4:   128–  152, влита   162
T055 [V] слот 5:   144–  168, влита   178
T059 [V] слот 2:   150–  166, влита   176
T054 [V] слот 4:   152–  168, влита   184
T053 [S] слот 3:   152–  168, влита   178
T028 [V] слот 1:   152–  167, влита   177
T026 [V] слот 2:   166–  181, влита   191
T030 [V] слот 1:   167–  182, влита   192
T056 [V] слот 3:   168–  183, влита   193
T062 [V] слот 4:   168–  183, влита   199
T035 [V] слот 5:   168–  183, влита   193
T036 [V] слот 2:   181–  196, влита   206
T038 [V] слот 1:   182–  197, влита   207
T060 [V] слот 5:   183–  198, влита   214
T034 [V] слот 3:   183–  198, влита   208
T041 [V] слот 4:   183–  198, влита   208
T039 [V] слот 2:   196–  206, влита   216
T040 [V] слот 1:   197–  207, влита   217
T064 [V] слот 3:   198–  208, влита   222
T063 [V] слот 4:   198–  208, влита   218
T065 [H] слот 1:   222–  232, влита   242
```

Слоты не простаивают с 0 до ~208: окно фазы К (0–74) заполняют `[T]` и срезы без
зависимостей от К (T021, T022, T024, T059): из 370 слот-минут окна задачи К занимают только 126,
остальное — работа, которая без `[T]` и без карты владения ждала бы К. Простой появляется только на хвосте (208–242: T064/T063 → T065).

## 8. Тесты, документы, ревью и вливания

**Тесты.**
- `[T]` по истории — до кода, другим агентом (Sonnet), строгий xfail. Срез снимает xfail
  своих `AC-n` и прикладывает вывод `hold`: откат не-тестовых `Файлы:` к базе → тесты
  `Готово-когда:` краснеют. Пустой тест виден до ревью.
- Тест среза лежит в файле среза. Общие фабрики — только T001 (`_step6_factories.py`) и
  T002 (`make_learning_task`).
- **`check.sh` исполнителя гоняет `Тест-группа:` и сторожей, а не весь `courses`.** Полный
  прогон (~11 тыс. тестов, ~30 мин) в каждом запуске прибавил бы 30 мин к каждому из ~104
  запусков — это ~3100 слот-минут, вдвое больше всей работы. Полный прогон делает только
  партия CI. Исключения — T052 и T053 (`django:*`): там проверка всего — суть задачи.
- Отпечаток групп CI у наставника грубый (любая правка `services/` сбрасывает все группы
  django). Это рычаг вне базы: срезы `course_bank`, `learning_process`, `frontend` с
  отпечатком по пакету гоняли бы 1–2 группы. Сейчас так не считается.

**Документы.** README и AGENTS новых пакетов — в T001 (каркас) и в срезе, если он меняет
поведение пакета. Общие реестры (INDEX, CHANGELOG, журнал) и правки источников по §8
спеки (Ж, Пар §3.2, ADR-121) — только T065. Документы рамок не трогаются.

**Ревью.** Пул R = K − 1. Ревьюер получает одну линзу: логика, `Контракт:`,
`Готово-когда:`/`AC-n`; механику (слияние со всеми ветками в полёте, `hold`, `check.sh`)
сделал скрипт при сдаче. Для `[K]` — линза «хватит ли срезам»; для `[T]` — «каждый `AC-n`
покрыт, тест бьёт обе стороны». Вердикт «можно сливать, хвост» уводит мелочи в T065. Второй
круг — только по находкам, третий — человек. Доработку берёт любой свободный исполнитель
новым запуском (кэш 5 мин всё равно остыл бы за время ревью).

**Вливания.** Срез вливается после своих зависимостей и `[T]`: rebase, `--ff-only`,
генерируемое перегенерировать. «Влита» — значит в ветке плана после пробного слияния и
`check.sh` группы. CI идёт партиями **переменного размера** (всё влитое с начала прошлой
проверки, от 3 до 6), красная партия делится пополам. Так CI не лежит на пути зависимостей,
а на окончание фичи ложится только последняя партия (15–28 мин).

## 9. Конфликты и простой — где они будут

1. **Сходка перед T052**: 8 срезов перевода плюс T051 и T003. При p = 0.43 в среднем 3–4
   из 8 уйдут на доработку, и T052 ждёт последнего. Это главный источник простоя в модели.
   Смягчение: срезы перевода — первые по рангу среди равных; ревьюер получает только
   «поведение не изменилось, полей нет» (узкая линза).
2. **`services_learning_tasks.py`**: три владельца подряд (T043 → T042 → T055). T055
   ждёт T042, и это ребро лежит на пути к концу US8. Расписание это показывает: T055
   стартует в 144, через 26 мин после вливания T042.
3. **`gating.py`**: T046 → T027 → T041. Ребро T041 → T027 — порядок, а не смысл; если T027
   надолго уйдёт на доработку, T041 подождёт (в модели не на пути).
4. **Миграции**: три миграции фичи на одном пути плюс соседи по цепочке. Конфликт номера
   решается при вливании (новая голова, перегенерация), это ~3–5 мин у вливающего.
5. **Стек T006 от T001**: каскад, если T001 вернётся по смыслу шва (тип поля, обязательность).
   T006 от полей почти не зависит. Координатор пишет каждый такой отказ в журнал (q).
6. **Внешняя работа**: соседняя сессия ЕГЭ и шаг 8 в той же ветке плана. T004, T039, T040
   и T028 — их файлы (`exam_*`); в эксперименте это часть фичи, в жизни — согласование
   владельца. `TaskClassModal.tsx` шаг 8 правит после T023 (передача §8 спеки).
7. **Стенд**: e2e приёмки (AC-7, AC-16, AC-17, AC-22, AC-69, AC-78) — один стенд `cc-*`
   :8092. Приёмка историй идёт последовательно, ~30 мин на хвосте.
8. **Пул ревью**: ~104 ревью × ~8 мин ≈ 830 мин; при K = 5, R = 4 это ~52% пула за ~400 мин,
   при R = 3 — ~67%, но ревью приходят пачками после сходок. При R = 3 почти не хуже (413 против 403), при R = 2 пул станет горлом.

## 10. Оценка времени

| Вариант | Точечно (без доработок) | p = 0.25 | p = 0.43 | + хвост CI и приёмка |
|---|---|---|---|---|
| K = 3, R = 2 | 379 | 492 | 603 | +45…60 |
| K = 4, R = 3 | 293 | 384 | 467 | +45…60 |
| K = 5, R = 4 | 242 | 321 | 403 | +45…60 |
| K = 5, R = 3 | — | 327 | 413 | +45…60 |
| тот же граф, слот до вливания, K = 4 | — | 567 | 692 | +CI очередь |
| тот же граф, слот до вливания, K = 5 | — | 466 | 573 | +CI очередь |

Средняя одновременная занятость: 3.4–3.5 из 4 и 4.0–4.2 из 5. Это против сегодняшних
2.1–2.4 из 4.

Деньги (по медианам наблюдений: implementer ~$0.94, deep ~$4.9, reviewer ~$1.5, с
доработками ×1.65): 21 deep-задача × 1.65 × $4.9 ≈ $170, 42 обычных × 1.65 × $0.94 ≈ $65,
~104 ревью × $1.5 ≈ $156; итого **~$390** при p = 0.43 и ~$310 при p = 0.25. Половина
денег — deep, поэтому `Риск:` надо ставить строго по правилу ролей.

## 11. Что проверить по baseline (для сравнения)

- Сколько у baseline задач и какой у них P = W/S при тех же весах. Если P < 4, выигрыш даёт
  именно перекладка цепочки «задача курса» в 8 параллельных срезов.
- Сколько отказов ревью baseline приходится на пересечение с соседней задачей: здесь их
  должно стать 0 по построению карты (§6), кроме смысловых, которые закрывают швы К.
- Фактическое p и доля повторных отказов: от неё зависит выбор между формулой
  `W(1+0.7p)` и `W(1+0.7p/(1−p))`.
- Шли ли у baseline полные прогоны `courses` в каждом запуске исполнителя: если да, то
  правило «`check.sh` — только своя группа» одно даёт больше, чем пятый слот.
