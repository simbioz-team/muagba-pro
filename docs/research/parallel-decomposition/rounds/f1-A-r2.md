# Фича 1 (шаг 6 «Наставника»), команда A, круг 2: разложение и план

Дата 2026-11-24. Процесс — `design.md` (сведённый) с поправками П-1…П-7 круга 2. Позиция
команды A прежняя: ширина берётся от контрактов и вертикальных срезов, зависимость «по коду»
заменена зависимостью «по контракту». Код читался только на базовом коммите `06a0bbdf4`.
Модель плана и все проверки — скрипты в
`/tmp/claude-1000/-home-rustam-develop-simbioz-team-muagba-pro/e280ef6f-cbe4-4a58-b39a-164383171093/scratchpad/f1A2/`:

- `plan.py` — граф, W, S, P;
- `sched.py` — расписание HLFET;
- `files.py` — карта владения;
- `paths.py` — пересечения без пути;
- `must.py`, `cover2.py` — покрытие потребителей;
- `cls.py`, `tg.py` — классификатор групп тестов на коде базы;
- `evsim.py`, `evsim2.py`, `runsim.py` — симулятор оценщика без изменений и вариант с отдельной
  очередью вливания;
- `overlap.py` — пересечение с планами шага 8 и сессии ЕГЭ.

## 0. Итог в цифрах

| Мера | Круг 1 | Круг 2 |
|---|---|---|
| Задач | 66: 4 `[K]`, 11 `[T]`, 44 `[V]`, 6 `[S]`, 1 `[H]` | 65: 5 `[K]`, 6 `[T]`, 47 `[V]`, 6 `[S]`, 1 `[H]`; `deep` — 14 |
| W (вес-мин) | 995 | 1010 |
| S (критический путь) | 104, без рёбер ворот | 124, с рёбрами ворот `[T]`: T001 → T009 → T021 → T034 → T044 → T045 → T066 |
| P = W/S | 9.6 | 8.15: норма для K = 4 (≥ 8) и с запасом для K = 3 (≥ 6) |
| Фаза К | 4 задачи, 8% W | 5 задач, глубина 1, 93 вес-мин = 9% W |
| Готово к старту в момент 0 | 26 | 13: 5 `[K]` и 8 срезов; `[T]` ждут T001 (правило групп тестов) |
| HLFET без доработок и накладных | K = 4: 290 | K = 3: 380; K = 4: 292 |
| **Прогноз, главный** (K = 3, p = 0.5–0.6, очередь вливания сценарием) | — | **722–758 мин медианой, p90 785–836, ≈ 12.0–12.6 ч активного времени** |
| То же, вливание вручную (параметры оценщика) | — | 987–1023 мин, ≈ 16.5–17 ч |
| K = 4, если шаг 8 и сессия ЕГЭ не держат слот | 358 (неверно, накладные = 0) | 591–623 мин (очередь), 864–898 (вручную) |
| Средняя занятость исполнителей | 3.45 из 4 (неверно) | 2.4 из 3 (очередь), 1.8 из 3 (вручную) |
| Базовая линия по оценщику | ≈ 21 ч активного | — |

Изменение главного вывода: время фичи определяется не работой W/K, а **координатором и
вливанием**. Пока вливание ручное, исполнители заняты ≈ 2 из 4, и пятый слот даёт −2…−3%.
Совет круга 1 «K = 5, R = 4» снят. Первая мера — очередь вливания сценарием, вторая —
слоты. Лимит в 4 исполнителя общий с шагом 8 и сессией ЕГЭ, поэтому главный прогноз дан при
K = 3.

## 1. Ответ на замечания оценщика

| # | Замечание | Принято? | Что сделано | Где |
|---|---|---|---|---|
| 1 | Координатор и вливания считались бесплатными | да, полностью | Прогноз пересчитан **симулятором оценщика без изменений** (`evsim.py`) на новом графе; добавлен вариант с отдельной очередью вливания (`evsim2.py`, `sepmq`). Совет K = 5 снят. Вливание — сценарием: координатор только раздаёт задачи | §9, §11 |
| 2 | Главная оценка должна идти при p = 0.5–0.6 | да | Главная строка прогноза — p = 0.5–0.6. p = 0.3 — цель, а не ожидание. Механизмы снижения p перечислены отдельно, в прогноз не заложены | §11 |
| 3 | `answer_forms.py` у одного T056, T045 от T056 не зависит | да, перенос файла | `learning_tasks/answer_forms.py` переведён в **T033** (P1), а T033 → T044 → T045. T055 и T056 правят его позже, через порт. Проверка «каждый поздний редактор потребителя имеет переводчика-предка до T045» — 0 нарушений | T033, §10 |
| 4 | `rules_structure.py:462` без владельца | да | `gates/rules_structure.py` (RUNG_REGEN_TASKS_RELOCATED) — в **T038**, через `placement.q_without_rung` | T038 |
| 5 | 16 из 39 тест-модулей, создающих LearningTask, без владельца | да | Три тестовые задачи **T068–T070** (26 модулей, по образцу T632/T647/T648 базовой линии), остальное — в T040, T021, T031. Все от T002 (помощник C11), все до T044. Объединение списков оценщика — 215 файлов. После правок без владельца 39, каждый проверен руками: в 36 нет ни одного обращения к `LearningTask` (только `task_class` у `TopicContent`/`TaskClass`), 3 — комментарий или историческая миграция | §6, §10 |
| 6 | Скрытое ребро T001 → T004 (C2) | да, ребро снято | T004 больше не потребляет C2. Деталь курса отдаёт `learning_process.api.DEFAULTS` (константа R-1 в своём файле), `linked_exam_count` считается через `ExamCourse` — он есть на базе (`exam_codifier/models.py:128`). Переключение на `settings_for` — в T027. Заглушки T004 T001 не наполняет | T004, T027 |
| 7 | Реестр тестов без владельца, новые модули уходят в core, неверные `Тест-группа` | да | Правило групп — шов **C26 в T001**: `("banks", course_bank\|learning_process\|step6\|exam_trainer)` вторым правилом, `("structure", course_goal)` сразу после saga. Проверено классификатором базы: 731 существующий тест-модуль courses группу не меняет, ни один новый модуль шага не уходит в core (без правила ушли бы 10). `Тест-группа` каждой задачи **вычислена классификатором**, а не вписана руками | T001, §8 |
| 8 | `module-boundaries.json` без владельца | да | В T001, вместе с `module-tiers.json` и регистрацией моделей в `apps.py` | T001 |
| 9 | У клиентских срезов нет общих примеров ответов, e2e только на приёмке | да | Новая **[K] T067**: примеры §6 в JSON, общие для серверного теста (`assert_matches_example`) и jest-моков (`step6CourseBankExamples.ts` читает те же файлы). Прецедент на базе: jest уже читает файлы сервера через `../../../django-api/…`. Расхождение формы теперь краснеет в CI на той стороне, которая её сломала | T067, §8 |
| 10 | Нет сверки с шагом 8 и сессией ЕГЭ; лимит 4 исполнителя общий | да | Сверка по файлам с планами `f2-*`, `f3-*` (§12). Главный прогноз — K = 3. Порядок вливания по 9 общим горячим файлам назван | §11, §12 |

В чём не уступаем. Позиция команды A подтверждена новыми числами: P = 8.15, ширина 13 задач в
момент 0 и 32 задачи готовы к старту сразу после окна К. **Работа фичи параллелится. Ограничение —
в последовательном звене вне графа: координатор, вливание и CI.** Без накладных K = 4 даёт
495 мин при занятости 3.45. С ручным вливанием те же 4 слота дают 864 мин при занятости 2.0.
Разница 369 мин — цена вливания, а не формы разложения. Значит, по замечанию 1 чинить нужно
вливание, а не граф. Сделать граф «уже» (меньше задач, но крупнее) — ответ мимо цели. Вливаний станет меньше, но
каждая задача станет длиннее, а с ней и путь. Узкое место при этом останется тем же звеном.

## 2. Истории и приёмочные задачи `[T]`

Поправка П-3: одна `[T]` на **пару историй**. Так 11 `[T]` превратились в 6, и вливаний
стало на 5 меньше. Каждая `[T]` пишется по `contracts.md`, спеке и примерам C25, не по коду К.
Тест — строгий xfail (`unittest.expectedFailure`, во фронте — `test.fail()` Playwright).
Срез снимает xfail своих AC и вливается только после своей `[T]` (ребро ворот).

| Истории | AC | `[T]` | Срезы под воротами |
|---|---|---|---|
| US1 + US2: учебный процесс, гейт отправки, экзамены курса | 1–6, 8–15, 18, 21 | T005 | T016, T027, T028, T029, T030 |
| US3 + US5: банки, решатель, раскладка | 19, 19а, 20–32, 65 | T006 | T046, T047, T048, T049 |
| US4 + US6: задача курса, порт, перенос; приём размещения | 33, 42, 55–64, 66–68, 71–73 | T007 | T033–T044, T050, T055 |
| US7 + US8: гейт 3, недостача, перенос и ловушки; ревизии, покрытие, видимость | 34–41, 53, 70, 74–77 | T008 | T017, T032, T051–T054, T056 |
| US9 + US10: режимы урока, старые курсы; цель, экзамен, копия | 43–52, 54 | T009 | T019–T022, T031, T045, T057–T061 |
| US11: экраны | 7, 16, 17, 22, 36, 43, 46, 69, 78 (UI) | T010 | T023–T026, T062–T065 |

`[T]` зависят от T001 только правилом групп тестов: без него модуль
`tests/acceptance/step6/*` классифицируется в core, а предкоммитная проверка
`test_registry.py --check` красная (`core_ceiling` = 2). Это ребро стоит 24 вес-мин на пути
T001 → T009 → T021. Вариант «правило отдельной микро-задачей» в симуляторе дал 592 мин против
591 при K = 4, так что выигрыша нет, и ребро оставлено.

Номера T011–T015 свободны намеренно. Номера срезов совпадают с кругом 1, чтобы оценщик сверял
задачи один к одному. Новые задачи — T067–T070.
## 3. `contracts.md` (карта швов)

Отличия от круга 1: C2 больше не потребляет T004; C11 добавились T068–T070; C16 больше не несёт форм ответов — они в C25; новые C25 и C26.

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| C1 | `CourseLearningProcess` (поля R-1, PK = course) | T001 [K] | T027, T028, T029, T030, T058 |
| C2 | `learning_process.read`: `settings_for(course)`, `has_current_exam(course, exam_ids=None)` (до T016 — чтение `ExamCourse`/`get_current_versions`, отклонение спеки R-2), `linked_exam_count(course)`; писатель-примитив `disable_exam_activities(course) -> (mocks_disabled, trainer_disabled)` под замком вызывающего | T001 [K] | T027–T030 (T004 — **нет**: деталь курса на `api.DEFAULTS`, переключение в T027) |
| C3 | `CourseBank` (R-17) | T001 [K] | T046, T047, T048, T058 |
| C4 | `CourseTask` (R-22 целиком, включая `transfer_change_kind`, `ksa_snapshot`, три ограничения БД) | T001 [K] | T042–T045, T047, T049–T051, T058 |
| C5 | `CourseBankLayoutRun` | T001 [K] | T049 |
| C6 | `CourseFinalTask.exam_position_refs`, `exemplar_task_ids`; `CourseFinalTaskKSA.origin = exam` | T001 [K] | T059–T061, T026 |
| C7 | Цепочка миграций шага: 0301 (схема, T001) → 0302 (перенос данных, T042) → 0303 (удаление колонок, T045); номера — на момент вливания | T001 [K] | T042, T045 |
| C8 | Порт `course_bank/placement.py` — весь список R-23а (`rung_ids`, `marks`, `q_on_rungs`, `q_without_rung`, `annotate_rung`, `select_rung`, `course_id_of`, `of_rungs`, `of_course`, `lookup_rung`, `rung_count`, `rung_exists`, `register`, `place`, `set_marks`, `move`, `detach`) + `approve_placement` и `reset_placement`; правило версии Р-CT12 | T002 [K] | T033–T041, T043, T044, T055, T056 |
| C9 | `course_bank.reader.course_tasks(course, *, task_class_ids=None, include_inactive=False) -> list[CourseTaskItem]`, DTO R-23 | T002 [K] | T047, T050–T054 |
| C10 | `reader_links.course_links(...)` — заглушка `[]` в T002, тело — T047 | T002 [K] | T002 (reader.py) |
| C11 | Помощник тестов `make_learning_task(**kw)` (через порт) | T002 [K] | T033–T041, T068–T070, T005–T009 |
| C12 | `exam_tasks.services`: `fipi_task_ids`, `accepted_task_ids`, `task_ksa_ids_many`, `positions_for`, `position_task_ksa_ids` (Е-2, Е-3, Е-4, Е-14, Е-16) | T003 [K] | T032, T047, T048, T051, T052, T059, T060, T018 |
| C13 | Адаптер `course_bank/bank_api.py` — единственный вход курса в банк: `visible_ids`, `trusted_ids`, `steps_of(links)` (через `task_solutions.current_solutions`), `accepted_ids`, `fipi_ids`, `ksa_ids_many`, `current_revisions`, `task_for_author`; `AUDIENCE_STUDENT` | T003 [K] | T047–T052 |
| C14 | Реестр: `learning-process-exam-missing`, `goal-target-not-on-line-top`, `goal-exam-positions-uncovered`, `course-task-placement-unreviewed` (gate_blockers), `rung-ksa-mismatch`, `required-for-mark` (invalid_value_codes), `/problems/goal-exam-position-ksa-missing`; новые meaning/title у `learning-tasks-transfer-insufficient` и `-traps-insufficient`; `problem_types.py`, `locale/ru/problems.json` | T004 [K] | T029, T050, T053, T055, T056, T059–T061 |
| C15 | Привязки гейтов в `gates/registry.py` с заглушками правил (`rules_learning_process.py`, `rules_course_task.py`, `rules_goal_exam.py` отдают `[]`); `TASK_CLASS_MODES_MISSING` и `CONTENT_READING_MODE_INVALID` — только старый путь | T004 [K] | T029, T053, T061, T022 |
| C16 | Все маршруты §6: `learning_process/urls.py`, `course_bank/urls.py` → представления-заглушки по одному файлу на область (`views_process`, `views_exams`, `views_banks`, `views_links`, `views_layout`, `views_revisions`, `views_coverage`), 501; формы ответов — в C25 | T004 [K] | T027, T028, T046, T049–T052 |
| C17 | Хуки: `CourseCreateSerializer`/`CoursePatchSerializer` принимают `exam_ids`, `learning_process`, больше не принимают режимов; `create_course` — одна `transaction.atomic()`, порядок вызовов `exam_links.link_on_create` → `writers.write_on_create`; PATCH — `writers.apply_patch`; деталь курса — `learning_process.api.detail_fields(course)`, ключей режимов нет; в T004 тело — `DEFAULTS` и `ExamCourse`, C2 не вызывается | T004 [K] | T027, T028, T031, T057 |
| C25 | Примеры ответов §6: `BE/tests/contract_examples/step6/<ручка>.json` (≈ 25), `assert_matches_example(response, name)` на сервере, `step6CourseBankExamples.ts` во фронте (читает те же файлы); пример — источник формы, спека — источник смысла | T067 [K] | серверные срезы с ручками (T027, T028, T046, T047, T050, T051, T052, T059, T055), все клиентские (T024–T026, T062–T065), `[T]` T005–T010 |
| C26 | Правило групп тестов: в `scripts/test_registry.py` `("banks", course_bank\|learning_process\|step6\|exam_trainer)` вторым, `("structure", course_goal)` после saga; модели пакетов в `apps.py`; `module-tiers.json`, `module-boundaries.json` | T001 [K] | все задачи с новыми тест-модулями |
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

- **Окно К (0–24 мин).** T001–T004 и T067 идут параллельно, без связей между собой. В том
  же окне стартуют 8 срезов, которым К не нужна:
  - режимы T020–T022 (сервер);
  - команда старых курсов T019;
  - `exam_codifier` T016;
  - сторож T017;
  - фикстура стенда T018;
  - фронтовое снятие режимов T023.
- **Веер 1 (24–150).** Сразу после К готовы к старту 32 задачи:
  - шесть `[T]`;
  - 9 срезов перевода на порт (T033–T041) и три тестовых (T068–T070);
  - учебный процесс и экзамены T027–T030;
  - банки и раскладка T046–T049;
  - цель T059–T061, копия T057;
  - хранение приёма размещения T042, T043;
  - клиентские срезы на примерах C25.
- **Схождение T044.** Ждёт 9 переводчиков порта, 3 тестовые задачи и T042, T043. Все стоят
  на глубине 1 от К, так что это не лестница.
- **Веер 2.** T053–T056 идут от T043, а не от T044.
- **Хвост.** T045 (удаление колонок, сторож), затем T066 `[H]`.

Рёбра между `[V]` — как в круге 1 (§4 там), плюс:

| Ребро | Причина |
|---|---|
| T001 → T005…T010 | C26: без правила групп тест-модуль `[T]` уходит в core, предкоммитная проверка красная |
| T067 → T024–T026, T062, T027, T028, T043, T046, T047 | C25: примеры ответов |
| T002 → T068–T070 → T044 | C11 помощник; перевод тестов до переключения хранилища |
| T001 → T062 | `NEW/page.tsx` читает типы C1, а не литералы |
| ~~T001 → T004~~ (скрытое ребро снято) | замечание 6: C2 больше не нужен T004 |

## 5. Карта владения горячими файлами

Изменения против круга 1:

| Файл | Владельцы по порядку | Как держится |
|---|---|---|
| `scripts/test_registry.py`, `scripts/tests/test_test_registry.py` | T001 | одно правило на фичу (C26); срезы реестр тестов не трогают; в `test-registry.json` ни одной строки исключений |
| `docs/engineering/module-boundaries.json`, `module-tiers.json` | T001 | оба пакета заведены в К |
| `BE/apps.py` | T001 | регистрация моделей пакетов и импорт `course_bank.tasks` (заглушка Celery) |
| `BE/learning_tasks/answer_forms.py` | T033 → T055 → T056 | цепочка; T033 — до T044 → T045 |
| `BE/course_pipeline/gates/rules_structure.py` | T038 | один владелец |
| `BE/tests/contract_examples/step6/*.json` | T067 | срезы файлы примеров не правят. Если форма неверна — возврат в T067 через `architect`, а не правка на месте |
| `FEA/__tests__/_helpers/step6CourseBankExamples.ts` | T067 | один владелец |
| 26 тест-модулей с `LearningTask(task_class=…)` | T068 (9, course_pipeline), T069 (9, courses/tests), T070 (8) | все от T002, все до T044 |
| `BE/learning_process/__init__.py`, `BE/course_bank/__init__.py` | T001, T002, T003, T004 | одинаковое пустое добавление, `pair-rules.txt` → `shared` |

Остальная карта — как в круге 1 (§5 там). Проверка `paths.py`: пересечений `Файлы:` без
пути в графе — 0, с учётом вложенности каталогов.

## 6. Задачи

Сокращения путей: `BE/` = `services/django-api/courses/`,
`FE/` = `services/frontend/app/(lk)/my-courses/[courseId]/_components/`,
`NEW/` = `services/frontend/app/(lk)/my-courses/new/`, `FEA/` = `services/frontend/`,
`config/` = `services/django-api/config/`.

Поле `Тест-группа:` вычислено `tg.py`: классификатор базы `scripts/test_registry.py` с
правилом C26 прогнан по каждому тест-модулю задачи. Группы перечислены по убыванию числа
модулей. `frontend` и `e2e` — вне реестра django.

Оценка исполнителя — в минутах по замеру базы:

| Размер | обычный | `deep` |
|---|---|---|
| S | 8 | 12 |
| M | 12 | 17 |

Ревью ≈ 8 мин на круг.

- [ ] T001 [K] Схема шага: модели, одна миграция, примитивы учебного процесса
  Срез: контракт (все истории)
  Контракт: владеет C1, C2, C3, C4, C5, C6, C7
  Файлы: BE/learning_process/__init__.py, BE/learning_process/models.py, BE/learning_process/read.py, BE/learning_process/README.md, BE/learning_process/AGENTS.md, BE/learning_process/tests/test_read.py, BE/course_bank/__init__.py, BE/course_bank/models.py, BE/course_bank/README.md, BE/course_bank/AGENTS.md, BE/course_bank/tests/test_models.py, BE/course_goal/models.py, BE/models.py, BE/migrations/0301_step6_schema.py, docs/engineering/module-tiers.json, docs/engineering/module-map.md, BE/apps.py, BE/course_bank/tasks.py, docs/engineering/module-boundaries.json, scripts/test_registry.py, scripts/tests/test_test_registry.py
  Сущность: CourseLearningProcess, CourseBank, CourseTask, CourseBankLayoutRun, CourseFinalTask
  Миграция: 0301 (единственная схемная миграция шага; transfer_change_kind, ksa_snapshot, origin=exam — сразу здесь)
  Правило-шов: test_registry.py (C26) — единственная правка реестра тестов за фичу; срезы реестр не трогают
  Зависит от: —
  Приёмка: AC-55, AC-2 (часть)
  Готово-когда: test_course_task_one_source, test_course_task_unique_exam_task, test_placement_approved_requires_at зелёные и краснеют при снятии ограничений; test_settings_for_defaults (нет строки → умолчания R-1); README обоих пакетов перечисляет все модули из contracts.md (срезы README не трогают); module-map перегенерирован; правило групп тестов (C26): `scripts/test_registry.py` получает ("banks", course_bank|learning_process|step6|exam_trainer) вторым правилом и ("structure", course_goal) сразу после saga; случай в `scripts/tests/test_test_registry.py`: 731 существующий модуль courses не меняет группу, новые модули шага не попадают в core; `test_registry.py --check` зелёный без единой строки в test-registry.json; модели пакетов зарегистрированы в apps.py, там же импорт `course_bank.tasks` (заглушка); module-tiers.json и module-boundaries.json знают оба пакета
  Риск: deep
  Размер: M
  Тест-группа: banks, governance
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 124

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
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 103

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
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 75

- [ ] T004 [K] Швы: реестр кодов, привязки гейтов, маршруты-заглушки, хуки создания/правки/деталей, проверка отметок
  Срез: контракт US1–US10
  Контракт: владеет C14–C20; C2 не потребляет (детали — на константе DEFAULTS, переключение на settings_for — в T027)
  Файлы: config/response-codes.json, config/api-problems.json, config/problem_types.py, config/locale/ru/problems.json, BE/course_pipeline/gates/registry.py, BE/course_pipeline/gates/rules_learning_process.py, BE/course_pipeline/gates/rules_course_task.py, BE/course_pipeline/gates/rules_goal_exam.py, BE/urls.py, BE/learning_process/urls.py, BE/learning_process/api.py, BE/learning_process/hooks.py, BE/learning_process/views_process.py, BE/learning_process/views_exams.py, BE/learning_process/exam_links.py, BE/learning_process/writers.py, BE/course_bank/urls.py, BE/course_bank/views_banks.py, BE/course_bank/views_links.py, BE/course_bank/views_layout.py, BE/course_bank/views_revisions.py, BE/course_bank/views_coverage.py, BE/course_bank/layout.py, BE/course_bank/detach.py, BE/course_bank/marks.py, BE/course_bank/tests/test_marks.py, BE/serializers.py, BE/services.py#create_course, BE/views.py#course_detail, BE/course_pipeline/course_patch.py#hook, BE/course_pipeline/gating.py#gate1_pass, BE/tasks.py#generation_start, BE/tests/test_step6_course_bank_seams.py, BE/learning_process/__init__.py, BE/course_bank/__init__.py
  Мера: реестр кодов ответа, реестр привязок гейтов (растут только здесь)
  Зависит от: —
  Приёмка: AC-47 (привязка), AC-43 (API: ответ без режимов)
  Готово-когда: все ручки §6 отвечают 501 problem `not-implemented` (кроме уже существующих); реестр: 7 новых кодов с added_by T-2264 и смена meaning/title двух кодов (сверка реестра зелёная); test_step6_course_bank_seams: create_course в одной транзакции, хуки зовутся в порядке exam_links → writers; деталь курса без allowed_lesson_modes/prefer_pbl, с `learning_process` = `api.DEFAULTS` (константа R-1 в своём api.py, read.py T001 не вызывается) и `linked_exam_count` через существующий ExamCourse; test_marks (4 правила R-41а); рост courses/services.py, serializers.py, tasks.py — 0 строк (loc-budget), хуки — вызовы в пакет
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 100

- [ ] T067 [K] Примеры ответов §6 (JSON) — общий источник для серверных тестов и jest-моков
  Срез: контракт US1–US11
  Контракт: владеет C25
  Файлы: BE/tests/contract_examples/__init__.py, BE/tests/contract_examples/step6/, FEA/__tests__/_helpers/step6CourseBankExamples.ts, FEA/__tests__/_helpers/step6CourseBankExamples.test.ts
  Почему отдельная [K]: формы нужны и серверу, и клиенту; без общего источника стык сервер ∥ клиент вскрывается только e2e на приёмке
  Зависит от: —
  Приёмка: — (шов: формы ответов всех ручек §6)
  Готово-когда: по файлу на ручку §6 (≈ 25) в `BE/tests/contract_examples/step6/`; `assert_matches_example(response, name)` сверяет ключи, типы и коды ошибок (лишний или пропавший ключ — красное); `step6CourseBankExamples.ts` читает те же файлы по пути `../../../django-api/…` (как уже делают publishFieldSection.test.ts и methodologyParamsLabelsSync.test.ts); самопроверка: каждый пример валиден по типам `FEA/types/*` шага и по полям §6
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 94

- [ ] T005 [T] US1+US2 Учебный процесс, гейт отправки, экзамены курса
  Срез: US1, US2
  Контракт: C1, C2, C14–C17, C24, C25
  Файлы: BE/tests/acceptance/__init__.py, BE/tests/acceptance/step6/__init__.py, BE/tests/acceptance/step6/test_us1_us2_process_exams.py
  Зависит от T001 только правилом групп тестов (C26): без него модуль `tests/acceptance/step6/*` уходит в core и предкоммитная проверка красная
  Зависит от: T001
  Приёмка: AC-1…AC-6, AC-8…AC-15, AC-18, AC-21
  Готово-когда: по тесту на каждый AC, строгий xfail (`unittest.expectedFailure`); каждый бьёт и запись, и чтение (PATCH → GET); гонка AC-13 — TransactionTestCase с двумя потоками; формы ответов — `assert_matches_example`
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 95

- [ ] T006 [T] US3+US5 Банки, решатель и раскладка
  Срез: US3, US5
  Контракт: C3–C5, C13, C16, C18, C21, C22, C25
  Файлы: BE/tests/acceptance/step6/test_us3_us5_banks_layout.py
  Зависит от T001 только правилом групп тестов (C26): без него модуль `tests/acceptance/step6/*` уходит в core и предкоммитная проверка красная
  Зависит от: T001
  Приёмка: AC-19, AC-19а, AC-20, AC-21, AC-22 (API), AC-23…AC-32, AC-65
  Готово-когда: строгий xfail; AC-26 — два прогона в потоках
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 75

- [ ] T007 [T] US4+US6 Задача курса и приём размещения
  Срез: US4, US6
  Контракт: C4, C7–C9, C11, C14, C16
  Файлы: BE/tests/acceptance/step6/test_us4_us6_course_task_placement.py
  Зависит от T001 только правилом групп тестов (C26): без него модуль `tests/acceptance/step6/*` уходит в core и предкоммитная проверка красная
  Зависит от: T001
  Приёмка: AC-33, AC-42, AC-55…AC-64, AC-66…AC-68, AC-71…AC-73
  Готово-когда: строгий xfail; AC-56/57 — тест миграции по scripts/check_migration_tests.py; AC-60 — по одному тесту на каждый путь создания
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 94

- [ ] T008 [T] US7+US8 Гейт 3, недостача, перенос и ловушки; ревизии, покрытие, видимость
  Срез: US7, US8
  Контракт: C9, C13–C16, C20, C21, C23
  Файлы: BE/tests/acceptance/step6/test_us7_us8_gate3_revisions.py
  Зависит от T001 только правилом групп тестов (C26): без него модуль `tests/acceptance/step6/*` уходит в core и предкоммитная проверка красная
  Зависит от: T001
  Приёмка: AC-34…AC-41, AC-53, AC-70, AC-74…AC-77
  Готово-когда: строгий xfail; AC-35 — один фикстурный курс для трёх потребителей; AC-41 — запуск сторожа T017 на дереве
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 60

- [ ] T009 [T] US9+US10 Режимы урока и старые курсы; цель, экзамен и копия курса
  Срез: US9, US10
  Контракт: C6, C12, C15, C17
  Файлы: BE/tests/acceptance/step6/test_us9_us10_modes_goal_copy.py
  Зависит от T001 только правилом групп тестов (C26): без него модуль `tests/acceptance/step6/*` уходит в core и предкоммитная проверка красная
  Зависит от: T001
  Приёмка: AC-43 (API), AC-44…AC-52, AC-54
  Готово-когда: строгий xfail; AC-48 — тест миграции 0303
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 100

- [ ] T010 [T] US11 Экраны (e2e на стенде cc-*)
  Срез: US11
  Контракт: C16, C25
  Файлы: FEA/tests/e2e/step6-create.spec.ts, FEA/tests/e2e/step6-brief.spec.ts, FEA/tests/e2e/step6-tasks.spec.ts, FEA/tests/e2e/step6-structure.spec.ts
  Зависит от T001 только правилом групп тестов (C26): без него модуль `tests/acceptance/step6/*` уходит в core и предкоммитная проверка красная
  Зависит от: T001
  Приёмка: AC-7, AC-16, AC-17, AC-22 (UI), AC-36 (UI), AC-43 (UI), AC-46 (UI), AC-69, AC-78
  Готово-когда: Playwright `test.fail()` по каждому AC; запускается приёмкой на :8092, в CI не входит
  Риск: обычный
  Размер: M
  Тест-группа: e2e (приёмка)
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T016 [V] Экзамены для курса в exam_codifier: каталог автора, связи курса, стойкое связывание
  Срез: US2
  Контракт: владеет C24
  Файлы: BE/exam_codifier/services.py, BE/exam_codifier/tests/test_course_api.py
  Почему не по контракту: функции живут в модуле банка (один писатель exam_codifier), курсу нужны только их имена из C24; у задачи нет зависимостей, она идёт в окне К
  Зависит от: —
  Приёмка: AC-10, AC-13 (часть банка) (тесты из T005 [T]; вливается после них)
  Готово-когда: test_author_exam_catalog_current_only, test_course_exam_links, test_link_course_race_raises_already_linked (два потока → одно ExamAlreadyLinked, не IntegrityError)
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 64

- [ ] T017 [V] Сторож писателей и читателей новых моделей (R-49, часть 1)
  Срез: US4, US8
  Контракт: C1, C3, C4, C5
  Файлы: scripts/check_course_bank_writes.py, .pre-commit-config.yaml#step6, scripts/tests/test_check_course_bank_writes.py
  Зависит от: —
  Приёмка: AC-41 (часть), AC-68 (часть: CourseTask) (тесты из T008 [T]; вливается после них)
  Готово-когда: `scripts/check_course_bank_writes.py` краснеет на фикстурном файле вне пакета, читающем CourseTask или пишущем CourseLearningProcess/CourseBank/CourseBankLayoutRun; подключён в pre-commit и CI
  Риск: обычный
  Размер: S
  Тест-группа: governance
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 41

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
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T019 [V] Команда снятия старых курсов с публикации и возврата с модерации (R-47а)
  Срез: US9
  Контракт: —
  Файлы: BE/management/commands/unpublish_legacy_courses.py, BE/management/commands/tests/test_legacy_courses_moderation.py
  Зависит от: —
  Приёмка: AC-49 (тесты из T009 [T]; вливается после них)
  Готово-когда: test_legacy_courses_moderation: список без --apply ничего не меняет; без --actor или без прав IsSagaAdmin — CommandError до изменений; published → banks_ready + sync зеркала; pending_review → review_rejected + заявка rejected с причиной; само-модерация только для pending_review; повтор безопасен
  Риск: deep
  Размер: S
  Тест-группа: saga
  Оценка: вес 16, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 31

- [ ] T020 [V] Режимы — константа: тема, урок, трек (R-42 часть, R-46)
  Срез: US9
  Контракт: —
  Файлы: BE/topic_content/lesson_modes.py, BE/lesson/streaming.py, BE/lesson/mode_a/services.py, BE/lesson/serializers.py, BE/track_manage/read.py, BE/track_manage/serializers.py, BE/tests/test_lesson_mode_selection.py, BE/topic_content/AGENTS.md
  Зависит от: —
  Приёмка: AC-43 (ученик бывшего ["A"] видит Б) (тесты из T009 [T]; вливается после них)
  Готово-когда: test_lesson_mode_selection: курс [] и ["A"] → оба режима по правилам темы; краснеет при возврате чтения поля
  Риск: обычный
  Размер: S
  Тест-группа: lessons
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T021 [V] Режимы — константа: генерация структуры, раскладка ступеней, редактор графа; инвариант «линия А без чтения» (R-42 часть, R-44)
  Срез: US9
  Контракт: —
  Файлы: BE/structure_gen/skeleton.py, BE/structure_gen/tasks.py, BE/task_classes/rung_layout.py, BE/task_classes/rung_layout_db.py, BE/course_graph_editor/read.py, BE/graph_invariants/structure_gate.py, BE/structure_gen/tests/test_phase1_brief_params.py, BE/task_classes/tests/test_rung_layout_db.py, BE/graph_invariants/tests/test_adr087_gate.py, BE/tests/test_learning_tasks_deficit.py#modes, BE/tests/_course_structure_audit_fixture.py, BE/structure_gen/tests/test_phase1_flag_autopath.py
  Зависит от: —
  Приёмка: AC-44, AC-45 (тесты из T009 [T]; вливается после них)
  Готово-когда: _allowed_modes_for_skills даёт [A,B] у курса []; rung_layout строит ступень чтения; reading-line-missing: старый путь — всегда, флаг — пусто (gate1, audit.py, repair); test_phase1_flag_autopath без allowed_lesson_modes
  Риск: обычный
  Размер: M
  Тест-группа: structure, banks, saga
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 85

- [ ] T022 [V] Окно ступени на флаге без режимов (R-48, R-45 тест)
  Срез: US9
  Контракт: C15 (привязка)
  Файлы: BE/task_classes/services.py, FE/structure/TaskClassModal.tsx, BE/task_classes/tests/test_allowed_modes_flag.py
  Зависит от: —
  Приёмка: AC-46, AC-47 (тесты из T009 [T]; вливается после них)
  Готово-когда: POST ступени с allowed_modes на флаге → 422 not-applicable; без него content_reading [A], whole_task [A,B]; смена вида пересчитывает; без флага — как было; TaskClassModal на флаге без чекбоксов (jest)
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T023 [V] Фронт: выбор режимов снят из формы создания и панели брифа (R-43, фронт)
  Срез: US9
  Контракт: —
  Файлы: NEW/page.tsx, FE/overview/CourseBriefPanel.tsx, FE/overview/briefFieldLabels.ts, FE/overview/briefConsistency.ts, FE/structure/TopicTreePanel.tsx, FEA/config/courseCreation.ts, FEA/utils/auth.ts, FEA/types/courses.ts, FEA/__tests__/briefValidation.test.ts
  Зависит от: —
  Приёмка: AC-43 (UI) (тесты из T010 [T]; вливается после них)
  Готово-когда: в форме и панели нет полей режимов; briefValidation/briefConsistency без них; jest зелёный
  Риск: обычный
  Размер: S
  Тест-группа: frontend
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 65

- [ ] T024 [V] Экран «Задачи»: блок «Задачи из банка»
  Срез: US11 (клиент US5, US6)
  Контракт: C16 (формы links/layout/candidates), C25
  Файлы: FE/tasks/CourseBankBlock.tsx, FE/tasks/CourseBankLinkRow.tsx, FE/tasks/CandidatesModal.tsx, FEA/types/courseBankLinks.ts, FEA/lib/api/courseBankLinks.ts, FE/tabs/TasksTab.tsx, FEA/__tests__/tasks/courseBankBlock.test.tsx
  Зависит от: T067
  Приёмка: AC-22 (UI), AC-69 (часть связей) (тесты из T010 [T]; вливается после них)
  Готово-когда: блок над списком своих задач при выбранном банке; ступень, пометки «шаги есть → П и З доступны», «ждёт ответа в банке», «банк снят», свёрнутые отклонённые с возвратом, «Подобрать ещё из банка», «в банке ещё N» → «Добавить»; jest на моках ответов по contracts.md; jest-моки — только из `step6CourseBankExamples` (C25), своих литералов ответа нет
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 45

- [ ] T025 [V] Экран «Задачи»: приём размещения своих задач, вид смены, ловушки «без пары»
  Срез: US11 (клиент US6, US7)
  Контракт: C16 (формы learning-tasks), C25
  Файлы: FE/tasks/AnswerMarksFields.tsx, FE/tasks/BulkBar.tsx, FE/tasks/EditLearningTaskModal.tsx, FE/tasks/CreateLearningTaskModal.tsx, FE/tasks/TreeGroupedPool.tsx, FE/tasks/InboxLT.tsx, FE/tasks/learningTaskForm.ts, FE/tasks/placementLabels.ts, FEA/types/courses.ts#LearningTask, FEA/__tests__/tasks/placement.test.tsx
  Зависит от: T067, T023
  Приёмка: AC-69 (часть своих), AC-78 (тесты из T010 [T]; вливается после них)
  Готово-когда: одна кнопка «Принять задачу» у новой ставит оба приёма; «Принять размещение» у перенесённой и в пачке; вид смены и «Укажите вид смены»; «без пары» у ловушки; ошибки required-for-mark у полей; jest-моки — только из `step6CourseBankExamples` (C25), своих литералов ответа нет
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T026 [V] Итоговые задачи: позиции КИМ и образцы (фронт R-50)
  Срез: US11 (клиент US10)
  Контракт: C6 (форма ответа), C25
  Файлы: FE/overview/FinalTasksBlock.tsx, FE/overview/finalTasks.ts, FE/overview/ExamPositionPicker.tsx, FEA/__tests__/overview/finalTaskPositions.test.tsx
  Зависит от: T067
  Приёмка: AC-50 (UI) (тесты из T010 [T]; вливается после них)
  Готово-когда: выбор позиций связанных экзаменов, до 3 образцов, exam_linked:false показан; jest; jest-моки — только из `step6CourseBankExamples` (C25), своих литералов ответа нет
  Риск: обычный
  Размер: S
  Тест-группа: frontend
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T027 [V] Учебный процесс: проверки, запись под версией курса, чтение, решатель (R-1…R-6 сервер, R-0, R-21)
  Срез: US1
  Контракт: C1, C2, C14, C16, C17
  Файлы: BE/learning_process/validation.py, BE/learning_process/writers.py, BE/learning_process/api.py, BE/learning_process/views_process.py, BE/learning_process/tests/test_validation.py, BE/learning_process/tests/test_writers.py
  Зависит от: T001, T004, T067
  Приёмка: AC-1…AC-6, AC-21 (тесты из T005 [T]; вливается после них)
  Готово-когда: снять xfail AC-1…AC-6, AC-21 в TA1/TA3; test_writers_lock_order (строка курса первой); hold: откат validation.py/writers.py краснит тесты; `api.detail_fields` переключён с DEFAULTS на `read.settings_for`; ответы ручек — `assert_matches_example`
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 39

- [ ] T028 [V] Экзамены курса: каталог, список, связать, снять, создание с exam_ids, слияние ответа (R-10…R-14, R-12а)
  Срез: US2
  Контракт: C2, C16, C17, C24
  Файлы: BE/learning_process/exam_links.py, BE/learning_process/views_exams.py, BE/learning_process/catalog.py, BE/learning_process/tests/test_exam_links.py, BE/learning_process/tests/test_exam_links_race.py
  Зависит от: T001, T004, T016, T067
  Приёмка: AC-8, AC-10…AC-13, AC-15, AC-18 (тесты из T005 [T]; вливается после них)
  Готово-когда: снять xfail AC-8, AC-10…AC-13, AC-15, AC-18; 404/403 по правам (AC-12); version +1 и learning_process в ответе; ответы ручек — `assert_matches_example` (C25)
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 54

- [ ] T029 [V] Гейт отправки learning-process-exam-missing и готовность заранее (R-7)
  Срез: US1
  Контракт: C2, C14, C15
  Файлы: BE/course_pipeline/gates/rules_learning_process.py, BE/course_pipeline/gate_journal.py, BE/publication/views.py#SubmitForReviewView, BE/course_pipeline/gating.py#lifecycle, FE/tabs/PublishTab.tsx, BE/course_pipeline/tests/test_submit_own_refuses.py
  Зависит от: T001, T004
  Приёмка: AC-9 (тесты из T005 [T]; вливается после них)
  Готово-когда: SubmitCheck.own_refuses; порядок витрина → собственные → перепроверка; 409 gate-blocked с gate_title без gate; /lifecycle can_submit_for_review=false и блокер в списке; PublishTab не пишет «Всё готово» при блокере
  Риск: обычный
  Размер: S
  Тест-группа: saga
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 80

- [ ] T030 [V] Вход в «Тренажёр ЕГЭ» из курса (Е-15)
  Срез: US1
  Контракт: C2 (settings_for)
  Файлы: BE/exam_trainer/services.py#start_session, BE/exam_trainer/tests/test_entry_from_course.py, FEA/app/courses/[courseId]/ExamTrainerEntry.tsx, FEA/app/courses/[courseId]/page.tsx
  Зависит от: T001
  Приёмка: — (R-9; приёмка — e2e) (тесты из T005 [T]; вливается после них)
  Готово-когда: start_session(entry=course) отказывает при exam_trainer_enabled=false; кнопка на странице курса ученика по каждому связанному экзамену только при включённом
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T031 [V] Режимы сняты из записи: бриф, правка курса, копия полей, админка, сиды (R-43, сервер)
  Срез: US9
  Контракт: C17
  Файлы: BE/services.py#brief_sync, BE/course_pipeline/course_patch.py#modes, BE/admin.py, BE/domain_errors/__init__.py, BE/management/commands/seed_course_pipeline.py, BE/management/commands/seed_tariff_testbed.py, BE/management/commands/seed_ksa_tc_testbed.py, BE/management/commands/prepare_t1142_manual.py, BE/management/commands/prepare_t1144_purchase_manual.py, BE/tests/test_brief_schema.py, BE/course_pipeline/tests/test_methodology_patch.py, BE/tests/test_main.py#modes, BE/access_registry/course_access/tests/test_course_access.py, BE/subject_areas/tests/test_course_subject_areas.py
  Зависит от: T004
  Приёмка: AC-43 (API), AC-48 (сиды работают) (тесты из T009 [T]; вливается после них)
  Готово-когда: _BRIEF_SYNC_FIELDS, _POST_PUBLICATION_BLOCKED_FIELDS, update_course_brief, course_patch без режимов; присланное поле игнорируется; сиды и prepare_* проходят; test_course_access и test_course_subject_areas без allowed_lesson_modes
  Риск: обычный
  Размер: M
  Тест-группа: structure, saga, core, platform, graph
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 85

- [ ] T032 [V] Выключатель ФИПИ только для задач с собственным происхождением ФИПИ (Е-17)
  Срез: US8
  Контракт: C12
  Файлы: BE/exam_tasks/services.py#_learner_origin_q, BE/exam_tasks/tests/test_fipi_switch_own_origin.py
  Зависит от: T003
  Приёмка: AC-40 (вторая часть), AC-70 (тесты из T008 [T]; вливается после них)
  Готово-когда: задача ФИПИ скрыта при выключенной выдаче, вариант authored на её основе виден
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T033 [V] Порт: CRUD и API своих задач (services_learning_tasks, ручки, права)
  Срез: US4
  Контракт: C8, C11, C17
  Файлы: BE/services_learning_tasks.py, BE/views.py#learning_tasks, BE/permissions.py, BE/tests/test_learning_tasks_api.py, BE/tests/test_learning_task_version.py, BE/learning_tasks/answer_forms.py
  Зависит от: T002, T004
  Приёмка: AC-58, AC-60 (автор), AC-72, AC-73 (тесты из T007 [T]; вливается после них)
  Готово-когда: ни одного обращения к task_class/is_transfer/is_trap/trap_note LearningTask в файлах задачи (grep в тесте); PATCH ступени+шагов → version ровно +1; ответ API прежний; `learning_tasks/answer_forms.response_marks` берёт is_transfer/is_trap/trap_note через порт (до T045, иначе удаление колонок краснеет)
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 79

- [ ] T034 [V] Порт: генерация, недостача, добор
  Срез: US4
  Контракт: C8, C11, C18 (точка вызова)
  Файлы: BE/tasks.py, BE/learning_tasks/selection.py, BE/learning_tasks/deficit.py, BE/learning_tasks/top_up.py, BE/learning_tasks/generation_marks.py, BE/learning_tasks/solution_check.py, BE/learning_tasks/genre_fields.py, BE/learning_tasks/run_outcome.py, BE/learning_tasks/tests/, BE/tests/test_learning_tasks_deficit.py
  Зависит от: T002, T004, T021
  Приёмка: AC-60 (генерация) (тесты из T007 [T]; вливается после них)
  Готово-когда: файлы задачи читают ступень только через порт; генерация зовёт placement.register; тесты learning_tasks на make_learning_task
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T035 [V] Порт: решатель своих задач, биллинг, реестр транспорта
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/learning_task_solver/, BE/billing/learning_tasks.py, BE/ml_transport/registry.py
  Зависит от: T002
  Приёмка: AC-73 (решатель читает по новой версии) (тесты из T007 [T]; вливается после них)
  Готово-когда: то же правило grep; тесты learning_task_solver зелёные
  Риск: обычный
  Размер: M
  Тест-группа: banks, billing
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T036 [V] Порт: перекладка ступеней шагов 3а/4 (rung_switch, target_ksa, topic_merge, services ступени)
  Срез: US4
  Контракт: C8, C11, C19 (точка вызова)
  Файлы: BE/task_classes/rung_switch.py, BE/task_classes/target_ksa.py, BE/task_classes/topic_merge.py, BE/task_classes/services.py, BE/task_classes/predicates.py, BE/task_classes/delete_preview.py, BE/task_classes/rung_layout_db.py, BE/task_classes/tests/
  Зависит от: T002, T021, T022
  Приёмка: AC-67 (rung_switch) (тесты из T007 [T]; вливается после них)
  Готово-когда: detach_or_delete зовёт placement.detach и course_bank.detach.detach_links; relocate — move с version +1 один раз
  Риск: обычный
  Размер: M
  Тест-группа: banks, saga, documents
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T037 [V] Порт: удаление ступеней и тем, редактор графа
  Срез: US4
  Контракт: C8, C11, C19
  Файлы: BE/course_structure/deletion.py, BE/course_structure/rung_layout.py, BE/course_graph_editor/write.py, BE/course_graph_editor/read.py, BE/course_graph_editor/delete_preview.py, BE/course_structure/tests/test_deletion*.py, BE/course_structure/tests/test_rung_layout*.py, BE/course_graph_editor/tests/
  Зависит от: T002, T021, T004
  Приёмка: AC-60 (сохранение графа, bulk_create), AC-67 (deletion.py, rung_layout.py) (тесты из T007 [T]; вливается после них)
  Готово-когда: обработчик before_delete для TaskClass зовёт detach_links; write.py после bulk_create зовёт register
  Риск: обычный
  Размер: M
  Тест-группа: content, structure, graph, banks, platform
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T038 [V] Порт: гейты и сага
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/course_pipeline/gating.py#rung, BE/course_pipeline/gates/rules_stages.py, BE/course_pipeline/gates/facts.py, BE/course_pipeline/auto_pipeline.py, BE/course_pipeline/methodology_locks.py, BE/course_pipeline/views.py, BE/saga/reopen.py, BE/saga/state_machine.py, BE/course_pipeline/tests/test_gating_*.py, BE/course_pipeline/tests/test_rules_stages*.py, BE/course_pipeline/tests/test_auto_pipeline*.py, BE/saga/tests/, BE/publication/tests/, BE/methodology_params/tests/, BE/course_pipeline/gates/rules_structure.py
  Зависит от: T002, T004, T029
  Приёмка: AC-63 (часть: счёт по порту) (тесты из T007 [T]; вливается после них)
  Готово-когда: rules_stages.rung_count/rung_exists через порт; reopen и auto_pipeline без колонок; `gates/rules_structure.py` (RUNG_REGEN_TASKS_RELOCATED, «без ступени») считает через `placement.q_without_rung`, а не `task_class__isnull`
  Риск: обычный
  Размер: M
  Тест-группа: saga
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T039 [V] Порт: уроки, диалог, трек, материал, документы
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/lesson/streaming.py, BE/lesson/mode_a/services.py, BE/dialogue/item_materialization.py, BE/dialogue/lesson_setup.py, BE/dialogue/orchestrator_b.py, BE/track_manage/read.py, BE/track_manage/validation.py, BE/track_manage/models.py, BE/topic_content/passthrough.py, BE/topic_content/lesson_modes.py, BE/topic_content/generation/, BE/documents/services.py, BE/documents/views.py, BE/dialogue/tests/, BE/lesson/tests/, BE/track_manage/tests/, BE/documents/tests/
  Зависит от: T002, T020
  Приёмка: AC-66 (урок по ступени) (тесты из T007 [T]; вливается после них)
  Готово-когда: dialogue/lesson_setup получает задачи ступени через порт; тесты lessons зелёные
  Риск: обычный
  Размер: M
  Тест-группа: lessons, graph, documents, billing, content, banks, saga, platform, vision
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T040 [V] Порт: импорт, команды, сиды, админка
  Срез: US4
  Контракт: C8, C11
  Файлы: BE/_lt_import.py, BE/lt_import.py, BE/services_lt_import.py, BE/admin.py, BE/management/commands/archive_non_whole_task_learning_tasks.py, BE/management/commands/repair_structure_links.py, BE/management/commands/rung_rule_report.py, BE/management/commands/learning_task_target_audit.py, BE/management/commands/solution_steps_report.py, BE/management/commands/cleanup_tc_role_anomalies.py, BE/management/commands/backfill_adr087_projection.py, BE/management/commands/seed_t815_demo.py, BE/management/commands/seed_ksa_tc_testbed.py, BE/management/commands/seed_course_pipeline.py, BE/management/commands/_seed_lifecycle.py, BE/structure_gen/semantics.py, BE/tests/test_lt_import.py, BE/management/commands/tests/test_archive_non_whole_task_lt_command.py, BE/management/commands/tests/test_learning_task_target_audit.py, BE/management/commands/tests/test_rung_rule_report.py
  Зависит от: T002, T031
  Приёмка: AC-60 (импорт, сид) (тесты из T007 [T]; вливается после них)
  Готово-когда: импорт и сиды создают задачи через порт; команды отчётов читают через порт; тесты команд (archive_non_whole_task, learning_task_target_audit, rung_rule_report) на make_learning_task
  Риск: обычный
  Размер: M
  Тест-группа: banks, documents, platform
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T041 [V] Порт: общие тесты courses/tests на фикстуру make_learning_task
  Срез: US4
  Контракт: C11
  Файлы: BE/tests/test_integration.py, BE/tests/test_main.py, BE/tests/test_structure_gen.py, BE/tests/_course_structure_audit_fixture.py, BE/tests/test_backfill_adr087.py, BE/structure_gen/tests/test_sync_topic_links.py, BE/matching/tests/, BE/ml_transport/tests/
  Зависит от: T002, T020, T021, T031
  Приёмка: AC-68 (тесты) (тесты из T007 [T]; вливается после них)
  Готово-когда: в перечисленных файлах нет LearningTask(task_class=…) и прямых полей роли
  Риск: обычный
  Размер: M
  Тест-группа: graph, transport, core, structure, platform, billing
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T068 [V] Тесты гейтов и пайплайна — на помощник make_learning_task (course_pipeline/tests, 9 модулей)
  Срез: US4
  Контракт: C11
  Файлы: BE/course_pipeline/tests/test_gate2_content_reading.py, BE/course_pipeline/tests/test_gate_approve_clears_refusal.py, BE/course_pipeline/tests/test_gate_approve_events.py, BE/course_pipeline/tests/test_gate_rules_parity.py, BE/course_pipeline/tests/test_gate_views.py, BE/course_pipeline/tests/test_genre_approval_a2.py, BE/course_pipeline/tests/test_phase3_no_target_ksa.py, BE/course_pipeline/tests/test_reopen_views.py, BE/course_pipeline/tests/test_transfer_trap_rules.py
  Почему не в T038: тесты не зависят от кода порта, только от помощника C11; отдельная задача — параллельно T038, не на её пути (в бейзлайне — три такие задачи)
  Зависит от: T002
  Приёмка: AC-68 (тесты)
  Готово-когда: в файлах задачи нет `LearningTask(...task_class=...)`, `LearningTask.objects.create(task_class=…)` и прямых чтений is_transfer/is_trap/trap_note/allowed_lesson_modes; группа saga зелёная до и после T045
  Риск: обычный
  Размер: M
  Тест-группа: saga
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T069 [V] Тесты API, импорта и генерации своих задач — на помощник (courses/tests, 9 модулей)
  Срез: US4
  Контракт: C11
  Файлы: BE/tests/test_learning_tasks_endpoints.py, BE/tests/test_learning_tasks_filters.py, BE/tests/test_learning_tasks_generation_reservation.py, BE/tests/test_learning_tasks_generator_kind.py, BE/tests/test_learning_tasks_import.py, BE/tests/test_learning_tasks_old_steps_closed.py, BE/tests/test_learning_tasks_target_degraded.py, BE/tests/test_learning_tasks_billing_refusal.py, BE/tests/test_lt_import_automapping.py
  Зависит от: T002
  Приёмка: AC-68 (тесты)
  Готово-когда: то же правило; группы banks, documents, billing зелёные
  Риск: обычный
  Размер: M
  Тест-группа: banks, documents, billing
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 70

- [ ] T070 [V] Тесты фазы 3, структуры и разрывов — на помощник (8 модулей)
  Срез: US4
  Контракт: C11
  Файлы: BE/tests/_phase3_fixtures.py, BE/tests/_target_ksa_fixtures.py, BE/tests/test_phase3_fanout.py, BE/tests/test_task_class_lesson_models.py, BE/tests/test_course_graph_display_order.py, BE/structure_gen/tests/test_phase1_wiring.py, BE/structure_gen/tests/test_rung_layout_phase1.py, BE/gap_ingestion/tests/test_gap_ingestion.py
  Зависит от: T002
  Приёмка: AC-68 (тесты)
  Готово-когда: то же правило; группы structure, graph, lessons зелёные
  Риск: обычный
  Размер: S
  Тест-группа: structure, graph, lessons
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 65

- [ ] T042 [S] Перенос своих задач в задачи курса: миграция RunPython и проверочная команда (R-22а)
  Срез: US4
  Контракт: C4, C7
  Файлы: BE/migrations/0302_course_task_from_learning_task.py, BE/management/commands/check_learning_task_course_alignment.py, BE/tests/test_migration_0302.py
  Миграция: 0302
  Почему не срез: перенос данных одной миграцией, цепочка миграций линейна
  Зависит от: T001
  Приёмка: AC-56, AC-57 (тесты из T007 [T]; вливается после них)
  Готово-когда: снять xfail AC-56, AC-57; миграция на исторических моделях, идемпотентна, обратима, сверка (а)–(д); check_learning_task_course_alignment: код 1 при рассогласовании
  Риск: deep
  Размер: M
  Тест-группа: platform
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 79

- [ ] T043 [S] Хранение приёма размещения и вида смены своих задач в CourseTask
  Срез: US4, US6
  Контракт: C4, C8, C9
  Файлы: BE/course_bank/placement.py, BE/course_bank/reader.py, BE/course_bank/tests/test_placement_storage.py
  Почему не срез: меняет внутренности порта K2, вызывающий код не трогает
  Зависит от: T001, T002, T067
  Приёмка: AC-60 (у новой — задача курса), AC-62 (сброс) (тесты из T007 [T]; вливается после них)
  Готово-когда: register создаёт CourseTask (placed_by=with_task, ready_for_review), строка на старую задачу — get_or_create по правилу миграции; approve_placement, сброс при place/move/set_marks, transfer_change_kind в set_marks/marks; reader отдаёт placement_status своих
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 79

- [ ] T044 [S] Порт и читатель переключены на CourseTask (ступень и роль своих задач)
  Срез: US4
  Контракт: C8, C9
  Файлы: BE/course_bank/placement.py, BE/course_bank/reader.py, BE/course_bank/tests/test_port_switch.py
  Почему не срез: точка схождения всех потребителей порта
  Зависит от: T042, T043, T033, T034, T035, T036, T037, T038, T039, T040, T041, T068, T069, T070
  Приёмка: AC-58, AC-73 (тесты из T007 [T]; вливается после них)
  Готово-когда: снять xfail AC-58 и AC-73; порт и читатель не читают колонки LearningTask; полный прогон courses в партии зелёный; все 39 тест-модулей, создающих LearningTask через ORM на базе, к этому моменту переведены (T033–T041, T068–T070), проверка — grep в тесте T044
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 55

- [ ] T045 [S] Удаление колонок своих задач и режимов; сторож чтений (R-22б, R-47, R-49 часть 2)
  Срез: US4, US9
  Контракт: C7
  Файлы: BE/migrations/0303_drop_step6_columns.py, BE/models.py, BE/course_goal/models.py#none, BE/tests/test_migration_0303.py, scripts/check_course_bank_writes.py
  Миграция: 0303
  Почему не срез: стягивание схемы после перехода всех читателей
  Зависит от: T044, T020, T021, T031, T022, T017, T004
  Приёмка: AC-48, AC-59, AC-68 (тесты из T009 [T]; вливается после них)
  Готово-когда: миграция RemoveField learning_task.(task_class, is_transfer, is_trap, trap_note), course/brief.(allowed_lesson_modes, prefer_pbl); обратная — AddField и заполнение из course_task; сторож `check_course_bank_writes.py`: режимы не читаются нигде, поля LearningTask вне миграций — нет; полный прогон django отдельной партией из одной ветки
  Риск: deep
  Размер: S
  Тест-группа: platform
  Оценка: вес 16, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 31

- [ ] T046 [V] Выбранные банки: список, выбрать, снять; число задач курса по экзамену (R-17…R-20, course_task_count)
  Срез: US3
  Контракт: C3, C4, C16, C18 (schedule), C24
  Файлы: BE/course_bank/banks.py, BE/course_bank/views_banks.py, BE/course_bank/tests/test_banks.py
  Почему не по контракту (ребро T016): список экзаменов курса — функция C24 модуля банка
  Зависит от: T001, T004, T016, T067
  Приёмка: AC-19, AC-19а, AC-20 (связи на месте), AC-65 (тесты из T006 [T]; вливается после них)
  Готово-когда: снять xfail AC-19, AC-19а, AC-65; выбор после гейта 1 зовёт layout.schedule(trigger=bank_selected); ответы ручек — `assert_matches_example` (C25)
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 45

- [ ] T047 [V] Читатель связей, места ступени, видимость (R-23 связи, R-28, R-40)
  Срез: US5, US8
  Контракт: C4, C9, C10, C13; владеет C21
  Файлы: BE/course_bank/reader_links.py, BE/course_bank/places.py, BE/course_bank/tests/test_reader_links.py, BE/course_bank/tests/test_places.py
  Зависит от: T001, T002, T003, T067
  Приёмка: AC-20 (active=false), AC-36 (has_steps), AC-40 (тесты из T006 [T]; вливается после них)
  Готово-когда: reader_links пакетно (без запроса на задачу — assertNumQueries); rung_places 11/15; occupancy под замком вызывающего; аудитория student одной константой
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 60

- [ ] T048 [S] Раскладка, расчёт: кандидаты ступеней, правило ФИПИ, приоритет (R-25, R-26, R-29, R-30)
  Срез: US5
  Контракт: C13; владеет C22
  Файлы: BE/course_bank/candidates.py, BE/course_bank/tests/test_candidates.py
  Почему не срез: раскладка — один алгоритм в две фазы; цепочка [S] T048 → T049, стек разрешён
  Зависит от: T003
  Приёмка: AC-25, AC-27…AC-30 (тесты из T006 [T]; вливается после них)
  Готово-когда: candidates() без записи; один кандидат → moved, два → ambiguous; ФИПИ только верх линии, ≤ 3; порядок ответ → шаги → видна → номера КИМ по кругу → id
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 54

- [ ] T049 [S] Раскладка, запись: замок курса, места, журнал прогонов, Celery, запуски gate1/bank_selected/generation/manual, ожидание генерацией (R-27, R-28)
  Срез: US5
  Контракт: C5, C18, C21, C22
  Файлы: BE/course_bank/layout.py, BE/course_bank/tasks.py, BE/course_bank/views_layout.py, BE/course_bank/tests/test_layout_write.py, BE/course_bank/tests/test_layout_concurrency.py
  Почему не по контракту (ребро T047): счёт мест C21 — один на раскладку, недостачу и отчёт
  Зависит от: T048 (стек), T047, T004
  Приёмка: AC-22 (API), AC-23, AC-24, AC-26, AC-31, AC-32 (тесты из T006 [T]; вливается после них)
  Готово-когда: снять xfail TA5; два прогона в потоках не превышают мест; повтор ничего не меняет; отклонённую не возвращает; генерация ждёт прогон не дольше предела, по пределу — failed в журнале; ответы ручек — `assert_matches_example` (C25)
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 39

- [ ] T050 [V] Связи: ручное добавление, правка, отклонение и возврат, приём размещения пачкой, после публикации закрыто; detach_links (R-31…R-35, R-38, R-22 detach)
  Срез: US6
  Контракт: C14, C16, C19, C20, C21, C22
  Файлы: BE/course_bank/links.py, BE/course_bank/detach.py, BE/course_bank/views_links.py, BE/course_bank/tests/test_links.py, BE/course_bank/tests/test_detach.py
  Зависит от: T047, T048, T004
  Приёмка: AC-33, AC-42, AC-64 (связь), AC-67 (связи) (тесты из T007 [T]; вливается после них)
  Готово-когда: снять xfail AC-33, AC-42, AC-64; гонка добавления → already-taken; rung-ksa-mismatch с candidates; R-41а через marks.validate_marks; ответы ручек — `assert_matches_example` (C25)
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T051 [V] Новые ревизии и смена KSA без ревизии (R-36)
  Срез: US8
  Контракт: C13, C16, C21, C22
  Файлы: BE/course_bank/revisions.py, BE/course_bank/views_revisions.py, BE/course_bank/tests/test_revisions.py
  Зависит от: T047, T048, T004
  Приёмка: AC-37…AC-39 (тесты из T008 [T]; вливается после них)
  Готово-когда: apply под select_for_update по каждой связи; concurrent-change при гонке; размещение остаётся принятым; ответы ручек — `assert_matches_example` (C25)
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 39

- [ ] T052 [V] Отчёт покрытия D-033 (R-37)
  Срез: US8
  Контракт: C16, C21, C22, C23
  Файлы: BE/course_bank/coverage.py, BE/course_bank/views_coverage.py, BE/course_bank/tests/test_coverage.py
  Зависит от: T047, T048, T053
  Приёмка: AC-36 (отчёт) (тесты из T008 [T]; вливается после них)
  Готово-когда: все строки R-37 считаются из читателя, мест, кандидатов и квот; «выдача закрыта» — не из fipi_open_bank; ответы ручек — `assert_matches_example` (C25)
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T053 [V] Гейт 3 по задачам курса и квоты по ступени (R-24)
  Срез: US7
  Контракт: C9, C14, C15; владеет C23
  Файлы: BE/course_bank/quotas.py, BE/course_pipeline/gates/rules_course_task.py, BE/course_pipeline/gates/rules_stages.py#quotas, BE/course_bank/tests/test_quotas.py, BE/course_pipeline/tests/test_gate3_course_tasks.py
  Почему не по контракту (ребро T038): квоты живут в rules_stages.py, который T038 переводит на порт
  Зависит от: T047, T043, T038, T004
  Приёмка: AC-34, AC-63, AC-71, AC-76, AC-77 (тесты из T008 [T]; вливается после них)
  Готово-когда: course-task-placement-unreviewed только у стоящих на ступени, принятых в банке, у связи — активных; шаги и ключ — только свои; квоты по ступени, trap_quota_applies ложна
  Риск: обычный
  Размер: M
  Тест-группа: banks, saga
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 45

- [ ] T054 [V] Один счёт недостачи для генерации, «Догенерировать» и гейта 3 (R-39)
  Срез: US7
  Контракт: C9, C21, C23
  Файлы: BE/learning_tasks/deficit.py, BE/learning_tasks/top_up.py, BE/learning_tasks/generation_marks.py, BE/learning_tasks/tests/test_deficit_one_count.py
  Зависит от: T053, T047, T034
  Приёмка: AC-35, AC-23 (вторая часть) (тесты из T008 [T]; вливается после них)
  Готово-когда: три потребителя дают один дефицит; невидимые и без ответа место занимают, недостачу не закрывают; ловушки генерации до каталога не пишутся
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T055 [V] Приём своих задач: «Принять задачу» ставит и размещение, approve-placement, сброс при смене ступени или роли (R-34а)
  Срез: US6
  Контракт: C8, C14
  Файлы: BE/services_learning_tasks.py#bulk, BE/tests/test_learning_task_placement.py
  Почему не по контракту (ребро T033): тот же файл services_learning_tasks.py
  Зависит от: T043, T033
  Приёмка: AC-61, AC-62, AC-66 (approve на старом пути), AC-71 (тесты из T007 [T]; вливается после них)
  Готово-когда: снять xfail AC-61, AC-62, AC-71; без флага approve-placement → 422 action not-applicable; version +1 за пункт; ответы ручек — `assert_matches_example` (C25)
  Риск: deep
  Размер: M
  Тест-группа: banks
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 49

- [ ] T056 [V] Отметки своих задач: проверка R-41а, вид смены в создании, PATCH и ответе (R-41, R-41а, R-41б)
  Срез: US7
  Контракт: C8, C20
  Файлы: BE/services_learning_tasks.py#marks, BE/learning_tasks/answer_forms.py, BE/tests/test_learning_task_marks.py
  Почему не по контракту (ребро T055): тот же файл services_learning_tasks.py
  Зависит от: T055, T004
  Приёмка: AC-74, AC-75 (свои) (тесты из T008 [T]; вливается после них)
  Готово-когда: снять xfail AC-74, AC-75; снятие переноса без вида сбрасывает вид; генерация и импорт пишут без проверки
  Риск: обычный
  Размер: S
  Тест-группа: banks
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T057 [V] Копия курса нового пути: одна транзакция, флаг сразу, KSA без темы, рёбра, ступени и связи ступеней (R-12в)
  Срез: US10
  Контракт: C17
  Файлы: BE/course_structure/clone.py, BE/services.py#clone, BE/course_structure/tests/test_clone_v2.py
  Почему не по контракту (ребро T031): тот же create_course
  Зависит от: T004, T031
  Приёмка: AC-54 (ступени, граф, откат) (тесты из T009 [T]; вливается после них)
  Готово-когда: task_class_map отдаётся в create_course; whole_task_template переводится по картам (relative_to, involves_skill_ids); источник с нарушениями — наследуются, отказ только на новых
  Риск: deep
  Размер: M
  Тест-группа: structure
  Оценка: вес 24, исполнитель ≈ 17 мин, ревью ≈ 8 мин; ранг пути 54

- [ ] T058 [V] Копия курса нового пути: учебный процесс, экзамены, банки, связи на ступенях копии (R-12б пп. 1–3)
  Срез: US10
  Контракт: C1, C3, C4, C24
  Файлы: BE/course_bank/copy.py, BE/learning_process/copy.py, BE/course_bank/tests/test_copy.py
  Почему не по контракту (рёбра T057, T028, T046): копия — сборка писателей трёх срезов
  Зависит от: T057, T028, T046, T001
  Приёмка: AC-54 (остальное) (тесты из T009 [T]; вливается после них)
  Готово-когда: связи копии — те же exam_task и revision, ступени по карте, placement_status всегда ready_for_review; экзамен вне каталога пропущен и пробники выключены
  Риск: обычный
  Размер: M
  Тест-группа: banks
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T059 [V] Позиции КИМ и образцы у итоговой задачи, копия этих полей (R-50, R-12б п. 4)
  Срез: US10
  Контракт: C6, C12, C14
  Файлы: BE/course_goal/services.py, BE/course_goal/serializers.py, BE/course_goal/exam_refs.py, BE/course_goal/tests/test_exam_refs.py
  Зависит от: T001, T004
  Приёмка: AC-50 (тесты из T009 [T]; вливается после них)
  Готово-когда: not-allowed для несвязанного экзамена, unknown-reference для номера вне плана, too-many при 4 образцах; exam_linked:false у снятого; ответы ручек — `assert_matches_example` (C25)
  Риск: обычный
  Размер: M
  Тест-группа: structure
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 40

- [ ] T060 [V] «Подобрать умения» по позиции КИМ из банка (R-51)
  Срез: US10
  Контракт: C12, C14
  Файлы: BE/course_goal/services.py#suggest, BE/course_goal/suggest_errors.py, BE/course_goal/tests/test_suggest_by_position.py
  Почему не по контракту (ребро T059): тот же course_goal/services.py
  Зависит от: T059, T003
  Приёмка: AC-51 (тесты из T009 [T]; вливается после них)
  Готово-когда: без вызова ml-llm и без учёта расхода; позиция без KSA → 409 goal-exam-position-ksa-missing, suggest_status=failed
  Риск: обычный
  Размер: S
  Тест-группа: structure
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T061 [V] Автопроверки цели: не на верху линии, позиции экзамена без итоговой задачи (R-52)
  Срез: US10
  Контракт: C6, C15
  Файлы: BE/course_pipeline/gates/rules_goal_exam.py, BE/course_pipeline/tests/test_goal_exam_rules.py
  Зависит от: T001, T004
  Приёмка: AC-52 (тесты из T009 [T]; вливается после них)
  Готово-когда: две причины-предупреждения только на флаге
  Риск: обычный
  Размер: S
  Тест-группа: saga
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T062 [V] Форма создания: блоки «Экзамены» и «Учебный процесс» (R-6, R-12а клиент)
  Срез: US11 (клиент US1, US2)
  Контракт: C16, C17, C25
  Файлы: NEW/page.tsx, NEW/LearningProcessFields.tsx, NEW/ExamPicker.tsx, FEA/types/learningProcess.ts, FEA/lib/api/learningProcess.ts, FEA/__tests__/new/learningProcessFields.test.tsx
  Почему не по контракту (ребро T023): тот же page.tsx
  Зависит от: T023, T067, T001
  Приёмка: AC-7 (создание) (тесты из T010 [T]; вливается после них)
  Готово-когда: блоки только при pipelineV2 && !areasWithoutCatalog; пробники и тренажёр недоступны до выбора экзамена; одна отправка с exam_ids и learning_process; общие компоненты LearningProcessFields и ExamPicker; jest-моки — только из `step6CourseBankExamples` (C25), своих литералов ответа нет
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 55

- [ ] T063 [V] Панель брифа: «Учебный процесс» и «Экзамены», опора и черновик, окно О-3 (R-6, R-13а)
  Срез: US11 (клиент US1, US2)
  Контракт: C16, C25
  Файлы: FE/overview/CourseBriefPanel.tsx, FE/overview/ExamsBlock.tsx, FE/overview/useExamMerge.ts, FE/overview/BanksBlock.tsx, FEA/__tests__/overview/examMergeForm.test.ts
  Почему не по контракту (ребро T062): общие компоненты блока
  Зависит от: T062
  Приёмка: AC-7 (панель), AC-16, AC-17 (тесты из T010 [T]; вливается после них)
  Готово-когда: слияние ответа записи экзамена с несохранённой формой; окно «Экзамен снят… Снять и банк?» только при bank_selected; заглушка BanksBlock смонтирована; jest-моки — только из `step6CourseBankExamples` (C25), своих литералов ответа нет
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 40

- [ ] T064 [V] Панель брифа: блок «Банки задач» и решатель (R-18…R-21 клиент)
  Срез: US11 (клиент US3)
  Контракт: C16, C25
  Файлы: FE/overview/BanksBlock.tsx, FEA/types/courseBanks.ts, FEA/lib/api/courseBanks.ts, FEA/__tests__/overview/banksBlock.test.tsx
  Почему не по контракту (ребро T063): BanksBlock смонтирован в панели T063
  Зависит от: T063
  Приёмка: AC-19 (UI), AC-21 (UI) (тесты из T010 [T]; вливается после них)
  Готово-когда: выбранные, предложения, прочие; решатель с одним вариантом «Общий»; jest-моки — только из `step6CourseBankExamples` (C25), своих литералов ответа нет
  Риск: обычный
  Размер: S
  Тест-группа: frontend
  Оценка: вес 10, исполнитель ≈ 8 мин, ревью ≈ 8 мин; ранг пути 25

- [ ] T065 [V] Экран «Задачи»: окно ревизий и отчёт покрытия (R-36, R-37 клиент)
  Срез: US11 (клиент US8)
  Контракт: C16, C25
  Файлы: FE/tasks/RevisionsModal.tsx, FE/tasks/CoverageReport.tsx, FE/tasks/TaskClassCoveragePanel.tsx, FE/tabs/TasksTab.tsx#mount2, FEA/__tests__/tasks/coverage.test.tsx
  Почему не по контракту (ребро T024): монтирование в TasksTab.tsx после T024
  Зависит от: T024
  Приёмка: AC-36 (UI), AC-37 (UI) (тесты из T010 [T]; вливается после них)
  Готово-когда: «в банке новые версии задач: N», «изменились умения», «Перейти на новые версии»; отчёт по ступеням и строки курса; jest-моки — только из `step6CourseBankExamples` (C25), своих литералов ответа нет
  Риск: обычный
  Размер: M
  Тест-группа: frontend
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 30

- [ ] T066 [H] Хвост: реестры документов, журнал, CHANGELOG, README пакетов, правка Пар §3.2, записи ADR-121, передачи шагам 8–10; находки «хвост» дословно
  Срез: —
  Контракт: —
  Файлы: docs/INDEX.md, docs/TAGS.md, docs/journal/, CHANGELOG.md, BE/learning_process/README.md, BE/course_bank/README.md, docs/architecture/methodology/2026-11-17_parametry-i-model-dannyh-kursa.md, docs/architecture/decisions/ADR-121-kurs-banki-zadach-i-reshateli.md
  Зависит от: все задачи
  Приёмка: —
  Готово-когда: все находки ревью с вердиктом «можно сливать, хвост» закрыты дословно; docs/INDEX.md и TAGS.md сверены; README пакетов описывают фактическое
  Риск: обычный
  Размер: M
  Тест-группа: governance
  Оценка: вес 15, исполнитель ≈ 12 мин, ревью ≈ 8 мин; ранг пути 15
## 7. Расписание по слотам

HLFET (`sched.py`): готовая задача с наибольшим рангом пути идёт в свободный слот, сдача на
ревью освобождает слот. Числа — без доработок и накладных: это порядок раздачи, а не прогноз.
Прогноз с доработками, координатором и вливанием — в §11. Ребро ворот `[T]` учтено:
срез может начаться до своей `[T]`, но вливается после неё.

Порядок раздачи, которого держится сценарий:

1. В момент 0 — T001, T002, T004 (затем T067, T003).
2. По освобождении слота — `[T]` с наибольшим рангом (T009 и T007 первыми: они ворота критического пути).
3. Далее веер по рангу.

Хвост T044 → T045 → T066 занимает один слот, остальные слоты в нём простаивают. Его
сокращает только ранний старт T066: документы ADR-121 и передачи шагам 8–10 пишутся после
T049, а вливается T066 последней.

**K = 3, R = 2** — главный вариант (слот 4 у шага 8 или сессии ЕГЭ)

```
end 380
slot1: T001@0, T021@24, T009@39, T010@54, T042@69, T006@93, T036@108, T039@123, T068@138, T070@153, T047@163, T044@178, T024@202, T017@217, T059@227, T049@242, T045@266, T052@282, T065@297, T030@312, T061@322, T066@354
slot2: T002@0, T020@24, T022@34, T005@44, T029@59, T043@69, T034@93, T037@108, T040@123, T069@138, T016@153, T048@163, T062@178, T055@193, T053@217, T027@232, T019@256, T050@272, T058@287, T018@302, T056@312, T064@322
slot3: T004@0, T067@15, T031@30, T007@45, T033@60, T003@84, T035@99, T038@114, T041@129, T023@144, T008@154, T057@169, T028@193, T046@217, T063@232, T051@247, T025@271, T054@286, T032@301, T026@311, T060@321
   0-30   avg busy 3.00
  30-60   avg busy 3.00
  60-90   avg busy 3.00
  90-120  avg busy 3.00
 120-150  avg busy 3.00
 150-180  avg busy 3.00
 180-210  avg busy 3.00
 210-240  avg busy 3.00
 240-270  avg busy 3.00
 270-300  avg busy 3.00
 300-330  avg busy 3.00
 330-360  avg busy 0.37
 360-390  avg busy 0.30
 390-420  avg busy 0.00
end 380
slot1: T001@0, T021@24, T009@39, T010@54, T042@69, T006@93, T036@108, T039@123, T068@138, T070@153, T047@163, T044@178, T024@202, T017@217, T059@227, T049@242, T045@266, T052@282, T065@297, T030@312, T061@322, T066@354
slot2: T002@0, T020@24, T022@34, T005@44, T029@59, T043@69, T034@93, T037@108, T040@123, T069@138, T016@153, T048@163, T062@178, T055@193, T053@217, T027@232, T019@256, T050@272, T058@287, T018@302, T056@312, T064@322
slot3: T004@0, T067@15, T031@30, T007@45, T033@60, T003@84, T035@99, T038@114, T041@129, T023@144, T008@154, T057@169, T028@193, T046@217, T063@232, T051@247, T025@271, T054@286, T032@301, T026@311, T060@321
   0-30   avg busy 3.00
  30-60   avg busy 3.00
  60-90   avg busy 3.00
  90-120  avg busy 3.00
 120-150  avg busy 3.00
 150-180  avg busy 3.00
 180-210  avg busy 3.00
 210-240  avg busy 3.00
 240-270  avg busy 3.00
 270-300  avg busy 3.00
 300-330  avg busy 3.00
 330-360  avg busy 0.37
 360-390  avg busy 0.30
 390-420  avg busy 0.00
```

**K = 4, R = 3** — если соседи не держат слот

```
end 292
slot1: T001@0, T022@24, T016@34, T005@44, T033@59, T035@83, T039@98, T069@113, T028@128, T046@152, T059@167, T051@182, T052@206, T032@221, T026@231, T061@241, T066@266
slot2: T002@0, T003@24, T009@39, T029@54, T043@64, T037@88, T041@103, T008@118, T048@133, T055@148, T063@172, T019@187, T050@203, T065@218, T056@233
slot3: T004@0, T021@15, T031@30, T007@45, T042@60, T036@84, T040@99, T070@114, T047@124, T057@139, T053@163, T049@178, T025@202, T058@217, T030@232, T064@242
slot4: T067@0, T020@15, T023@25, T024@35, T010@50, T006@65, T034@80, T038@95, T068@110, T062@125, T044@140, T017@164, T027@174, T045@198, T054@214, T018@229, T060@239
   0-30   avg busy 4.00
  30-60   avg busy 4.00
  60-90   avg busy 4.00
  90-120  avg busy 4.00
 120-150  avg busy 4.00
 150-180  avg busy 4.00
 180-210  avg busy 4.00
 210-240  avg busy 4.00
 240-270  avg busy 1.30
 270-300  avg busy 0.37
 300-330  avg busy 0.00
```
## 8. Тесты и документы

**Где пишутся тесты.**

- **Приёмочные** — шесть `[T]` T005–T010 сразу после T001: модули в
  `BE/tests/acceptance/step6/` (группа banks по C26) и `FEA/tests/e2e/step6-*.spec.ts`. Строгий
  xfail: тест, который неожиданно прошёл, валит прогон. Срез снимает xfail своих AC в своей
  ветке, ревьюер сверяет снятые AC со списком в `Приёмка:`.
- **Модульные** — в самом срезе, в каталоге `tests/` своего пакета. Проба `hold`
  (`task_pairs.py`) откатывает рабочие файлы среза и требует, чтобы его тесты покраснели.
- **Перевод существующих тестов на помощник C11** — 12 задач:
  - T033–T041 по своим модулям;
  - T068–T070 — 26 модулей, где нет кода, только тесты.

  До T044 все 39 модулей, создающих `LearningTask` через ORM на базе, переведены. T044
  проверяет это grep-тестом.
- **Тесты миграций** (0301, 0302, 0303) — у владельца миграции, по
  `scripts/check_migration_tests.py`.
- **Стык сервер ∥ клиент** — примеры C25 (T067). Это ответ на замечание 9:
  - серверный срез сверяет ответ ручки с примером (`assert_matches_example`: лишний или
    пропавший ключ, другой тип, другой код ошибки — красное);
  - клиентский срез строит jest-мок только из `step6CourseBankExamples`, своих литералов
    ответа нет;
  - форма ломается на одной стороне — краснеет её CI, а не e2e на приёмке.

  e2e T010 остаётся для склейки экранов на стенде, но первая линия теперь в CI.
- **Группы тестов.** Правило C26 в T001. `check.sh` по `Тест-группе:` задачи гоняет группу до
  вливания. Две задачи (T031, T041) правят общие модули `test_main.py`, `test_integration.py`:
  они уже в core на базе, правило их не трогает. Эти задачи гоняют core целиком.

**Где пишутся документы.**

- В срезе — только то, что ревьюер обязан увидеть вместе с кодом: docstring функций
  контракта, строки реестра кодов (их пишет T004).
- README и AGENTS.md пакетов: перечень модулей — T001, описание — T066.
- `docs/INDEX.md`, `TAGS.md`, журнал, CHANGELOG, ADR-121, передачи шагам 8–10 — T066, единственный
  владелец реестров документов.
- `module-map.md` — генерируемый. При rebase не сливается, а перестраивается
  (`pair-rules.txt` → `generated`).

## 9. Ревью и вливание

Главная правка круга 2 (замечание 1): **вливание — не работа координатора.**

- **Координатор** (сессия или, лучше, сценарий workflow) только раздаёт задачи по порядку §7
  и принимает отчёты. Это ≈ 0.2–0.5 мин на действие вместо 1 мин в модели оценщика.
- **Очередь вливания — сценарий**, один на фичу, работает последовательно. Сценарий —
  последовательность уже существующих шагов, а не новый инструмент:
  1. rebase ветки на ветку фичи;
  2. `task_pairs.py merge` против веток в работе;
  3. проба `hold`;
  4. `check.sh` по `Тест-группе:`;
  5. `git merge --no-ff` в ветку фичи;
  6. push.

  Красный шаг возвращает задачу исполнителю тем же сообщением, что ревью. Время на одну ветку
  2–4 мин. Встроенная очередь GitHub (merge queue) здесь не годится без правки CI: на базе
  `cicd.yml` не слушает `merge_group`.
- **CI партиями.** CI на базе запускается на каждый push, а сценарий пушит ветку фичи раз в
  3 вливания.
  - Красную партию делим пополам: в модели r = 0.08 против 0.15, потому что каждая ветка до
    вливания прошла свою группу.
  - Полный прогон — отдельной партией из одной ветки после T044 и после T045, а также после
    каждой миграции (T001, T042, T045).
- **Ревью.**
  - Пул R = K − 1.
  - При очереди R = 2 и R = 3 при K = 4 дают одно время (≤ 1%): ревью — не узкое место.
  - Не больше двух кругов, на втором — только дифф доработки (база 0.23.13). Хвостовые находки
    дословно забирает T066.
- **`deep`** (14 задач): T001, T002, T019, T027, T028, T033, T042–T045, T049, T051, T055, T057.
  Их ведёт `implementer-deep`, у ревьюера право спросить `architect` по шву.
- **Порядок вливания К:** T004 → T001 → T002 → T003 → T067. После снятия C2 из T004 T001
  заглушки T004 не наполняет. Общие только пустые `__init__.py` (`shared`).

## 10. Проба плана (`design.md` §5) — самопроверка

| Проверка | Значение | Норма | Итог |
|---|---|---|---|
| У каждой `[V]` есть `[T]` своей истории | 43 из 47 через ворота. T018 (фикстура стенда) и T068–T070 (тесты) ворот не имеют: AC не снимают | все с AC | да |
| Ребро V → V с причиной | все рёбра (§4 круга 1 + §4 здесь) | все | да |
| `[S]` с «Почему не срез:» | 6 из 6 | все | да |
| `(стек)` только в цепочке `[S]` | 1: T048 → T049 | да | да |
| Пересечение `Файлы:` без пути в графе (`paths.py`, с вложенностью каталогов) | 0 | 0 | да |
| Каждый файл-потребитель полей `LearningTask` имеет переводчика до T045 (`cover2.py`) | 24 задачи-переводчика, все предки T045; поздние редакторы (T053–T057) — после переводчика | все | да |
| Тест-модули с `LearningTask(...)` на базе (39) с владельцем до T044 | 39 из 39 | все | да |
| Объединение списков потребителей оценщика (215) | без владельца 39: 36 без единого обращения к `LearningTask`, 3 — комментарий или историческая миграция | 0 настоящих | да |
| Новые тест-модули в core | 0 из 65 (без C26 было бы 10) | 0 (`core_ceiling` = 2) | да |
| Правило C26 меняет группу существующих модулей | 0 из 731 | 0 | да |
| Скрытое K → K | нет: T004 без C2 | нет | да |
| Миграции на одном пути | 0301 → 0302 → 0303 | да | да |
| Рост одного реестра в двух задачах | нет: коды и маршруты — T004, группы тестов и границы модулей — T001, примеры — T067 | нет | да |
| Глубина К / доля К | 1 / 9% | 1 / ≤ 20% | да |
| Число задач К | 5 | 1–3 | **отклонение**, §13 |
| P = W/S | 8.15 | ≥ 2K: 6 (K = 3), 8 (K = 4) | да |
| R | K − 1 | ≥ K − 1 | да |

## 11. Прогноз времени, качества и простоя

**Модель.** Симулятор оценщика (`evalchk/f1/sim.py`) запущен без изменений на графе круга 2
со стеком T048 → T049, 200 прогонов. Модель такая:

- координатор — одна последовательная очередь, c мин на действие;
- вливание m мин;
- CI партиями с долей красных r и делением пополам;
- p — доля задач, вернувшихся с первого ревью.

Вариант «C/D» — та же модель, но вливание идёт отдельной очередью сценария, а не через
координатора (`evsim2.py`, `sepmq=True`).

Медиана / p90 / средняя занятость исполнителей, минуты:

| Сценарий | K, R | p = 0.3 | p = 0.43 | **p = 0.5** | **p = 0.6** |
|---|---|---|---|---|---|
| A. Вручную: m = 3–8, c = 1, r = 0.15 (параметры оценщика) | 3, 2 | 885/971/1.73 | 945/1038/1.76 | 987/1068/1.78 | 1023/1101/1.83 |
| | 4, 3 | 798/871/1.93 | 836/921/1.99 | 864/937/2.04 | 898/980/2.10 |
| | 5, 4 | 785/872/1.96 | 819/901/2.05 | 843/932/2.09 | 868/984/2.16 |
| B. Очередь у координатора: m = 2–4, c = 0.5, r = 0.08 | 3, 2 | 679/741/2.21 | 723/793/2.25 | 756/833/2.25 | 795/871/2.29 |
| | 4, 3 | 578/642/2.65 | 620/688/2.70 | 628/708/2.75 | 668/742/2.78 |
| **C. Очередь сценарием отдельно: m = 2–4, c = 0.5, r = 0.08** | **3, 2** | 632/695/2.38 | 681/739/2.41 | **722/785/2.41** | **758/836/2.42** |
| | 4, 3 | 536/604/2.85 | 566/634/2.95 | 591/654/3.00 | 623/681/3.03 |
| | 5, 4 | 492/569/3.11 | 515/597/3.26 | 531/595/3.33 | 556/641/3.36 |
| D. То же, r = 0.05 | 3, 2 | 604/667/2.44 | 663/724/2.44 | 687/755/2.45 | 735/796/2.47 |
| | 4, 3 | 521/575/2.95 | 546/620/3.00 | 567/630/3.07 | 597/665/3.09 |

Пол без накладных (r = 0, c = 0, m = 2), K = 4, p = 0.5: 495 мин, занятость 3.45. Отдельно
красный CI r = 0.08 добавляет ≈ 80 мин, координатор c = 0.5 — ≈ 22 мин. Раздача сценарием
workflow (c = 0.2) при K = 3 и p = 0.5 даёт 691 мин против 722.

**Главный прогноз:** K = 3, R = 2, очередь вливания сценарием, p = 0.5–0.6:

- **722–758 мин медианой (p90 785–836), ≈ 12.0–12.6 ч активного времени** плюс приёмка
  последней истории на стенде ≈ 20 мин;
- против ≈ 21 ч у базовой линии это −40%;
- если вливание остаётся ручным — 987–1023 мин (≈ 16.5–17 ч, −20%);
- K = 4 (соседи не держат слот) — 591–623 мин с очередью.

**Что следует из таблицы.**

1. **Вливание — первая мера, слоты — вторая.** При ручном вливании переход K = 3 → 4 даёт
   −12%, K = 4 → 5 — −2…−3%, исполнители заняты ≈ 2 из K. С очередью K = 3 → 4 даёт −18%,
   K = 4 → 5 — −10%.
2. **Совет «K = 5, R = 4» снят** (замечание 1). Пятый слот имеет смысл только при очереди и
   только если шаг 8 и сессия ЕГЭ не ждут исполнителя. Сегодня они ждут.
3. **Красный CI — главный остаток накладных.** Его снижает прогон группы до вливания: он
   ловит красное в ветке, а не в партии.
4. **Цена.** ≈ 65 задач × (1 + 0.7p) запусков исполнителя и ≈ 65 × (1 + p) ревью. При
   p = 0.55 это ≈ 90 запусков исполнителя (18 deep) и ≈ 100 ревью.

**Качество.**

- В главный прогноз заложено p = 0.5–0.6: у этой фичи в базовой линии вернулось 72% задач.
- p = 0.3 — цель, и в прогноз она не заложена. Чем её добиваться:
  - узкие `Готово-когда` с названными тестами;
  - `[T]` до кода;
  - примеры C25 вместо чтения форм из спеки;
  - группа тестов до вливания;
  - вычисленные, а не вписанные руками `Тест-группы`;
  - самопроверка исполнителя (база 0.23.13).
- Чего план не ловит:
  - **ошибку в шве C8** — её чинят 9 потребителей; против этого `test_port_equals_columns` и
    `deep` у T002;
  - **неверный пример в C25** — сервер и клиент согласятся на неверной форме; против этого
    самопроверка T067 по полям §6 и e2e T010 на приёмке;
  - **смысловой конфликт с шагом 8** в одних и тех же правилах ступеней (§12) — его не видит
    ни один тест шага 6.

**Простой.**

- **Слоты.** 2.4 из 3 с очередью. Остаток уходит на ожидание ревью и вливания на доработках,
  на хвост T044 → T045 → T066 и на красные партии.
- **CI.** ≈ 22 партии по 3 ветки плюс 5 одиночных полных прогонов. Стену держит только красная
  партия и последняя.
- **Документы.** Узкого места нет: все реестры у T066.

## 12. Пересечение с шагом 8 и сессией ЕГЭ (замечание 10)

`overlap.py` сверил `Файлы:` этого плана с путями в планах соседей по точному пути или
префиксу каталога:

| План соседа | Общих путей |
|---|---|
| шаг 8, `f2-A-r1` | 22 |
| шаг 8, `f2-B-r1` | 33 |
| шаг 8, `f2-A-r2` | 28 |
| шаг 8, `f2-B-r2` | 35 |
| сессия ЕГЭ, `f3-A-r2` | 10 |
| сессия ЕГЭ, `f3-B-r1` | 7 |
| сессия ЕГЭ, `f3-B-r2` | 11 |

Главное:

| Общий файл | Наши задачи | Сосед | Мера |
|---|---|---|---|
| `config/response-codes.json`, `api-problems.json`, `gates/registry.py`, `scripts/test_registry.py`, `module-tiers.json`, `module-boundaries.json`, `apps.py` | T001, T004 | шаг 8, ЕГЭ | только дописывание: строки разных фич не пересекаются. `pair-rules.txt` → `shared`, конфликт rebase механический. Вливать К шага 6 первыми, это 24 мин от старта |
| `BE/migrations/` | T001, T042, T045 | шаг 8, ЕГЭ | номер на момент вливания (C7); очередь вливания одна на репозиторий, а не на фичу, иначе две 0301 |
| `course_pipeline/gating.py`, `auto_pipeline.py`, `gates/facts.py`, `saga/reopen.py` | T004, T029, T038 | шаг 8 | **смысловое пересечение**: оба шага меняют счёт ступеней и гейты. Вливаем T038 до задач шага 8 в этих файлах, а шаг 8 читает через порт C8. Сверку делает `architect` обеих фич до старта T038 |
| `task_classes/rung_layout*.py`, `services.py`, `predicates.py`, `structure_gen/skeleton.py`, `graph_invariants/structure_gate.py`, `course_graph_editor/read.py` | T021, T022, T036, T037 | шаг 8 | то же: режимы-константа (T021, T022) вливаются рано (в первые 40 мин), шаг 8 стартует свои правки этих файлов после |
| `topic_content/lesson_modes.py`, `passthrough.py`, `lesson/mode_a/services.py`, `lesson/serializers.py` | T020, T039 | шаг 8 | T020 рано; T039 после — rebase на шаг 8 |
| `BE/services.py`, `models.py`, `serializers.py`, `urls.py`, `views.py` | T004, T031, T033, T057, T001, T045 | шаг 8, ЕГЭ | разные функции; корневые файлы под `loc-budget.json` с запретом роста, поэтому все три фичи кладут новое в пакеты, а в корне остаются вызовы |
| `exam_tasks/services.py` | T003, T032 | ЕГЭ (K3, E2) | функции C12 дописываются в конец файла; вливать T003 первым |
| `FEA/utils/auth.ts`, `TaskClassModal.tsx`, `TopicTreePanel.tsx` | T023 | шаг 8 | T023 рано |
| `docs/INDEX.md`, `TAGS.md`, `module-map.md` | T066, T001 | все | `generated` / дописывание |

**Лимит исполнителей.** Четыре слота на машине общие. Отсюда главный прогноз при K = 3: один
слот остаётся соседу. Если сосед стоит, сценарий отдаёт слот шагу 6 — это 591–623 мин вместо
722–758.

## 13. Отклонения от процесса и спеки

1. **К — 5 задач, а не 1–3.** Причина та же, что в круге 1, плюс T067 (примеры). Глубина 1,
   9% W.
2. **`[T]` на пару историй (П-3)**, а не на историю: 6 вместо 11, вливаний на 5 меньше.
3. **`[T]` зависят от T001** (C26). Предкоммитная проверка групп тестов на базе не пропустит
   модуль в core. Цена — 24 вес-мин на пути, выигрыша от выделения в микро-задачу нет (§2).
4. **Тестовые задачи T068–T070 без ворот `[T]`:** они не снимают AC, а переводят тесты на
   помощник. Их держит T044, проверяя, что ни один модуль не создаёт `LearningTask(task_class=…)`.
5. Остальное — как в круге 1 (§12 там): `transfer_change_kind` сразу в 0301, перенос данных
   разделён на T042/T043, C21–C24 у срезов, фронт против контракта, порт сначала на старых
   колонках.

## 14. Раскрытие

Круг 2 не открывал запретных файлов, задач Narta и стенограмм. Код читался из `git archive`
базового коммита `06a0bbdf4` в `f1A2/base/`. Использованы:

- отчёт оценщика `f1-eval-r1.md` и его скрипты в `evalchk/` — списки потребителей,
  симулятор;
- планы соседей `f2-*`, `f3-*` — только для сверки путей.

Число 72% возвратов базовой линии и ≈ 21 ч взяты из отчёта оценщика, а не из базовой линии
напрямую. Раскрытие круга 1 (zsh `$C:`) остаётся в силе.
