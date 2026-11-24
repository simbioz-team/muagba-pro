# Фича 1 (шаг 6 пайплайна курса): разложение и план. Команда B, круг 2

Дата 2026-11-24. Процесс: `design.md`. Прошлая версия: `f1-B-r1.md`. Вход тот же:
`feature-1-description.md`, санированная спека, документ «перенос и ловушки», код наставника
**только на `06a0bbdf4`** (`git show`, `git ls-tree`, `git grep`). Запрещённые пути, ветки,
задачи Narta и baseline я не открывал. Отчёт оценщика по кругу 1 (`f1-eval-r1.md`) тоже не
открывал: в нём есть сравнение с baseline. Работал только по замечаниям из задания.

Скрипты (все цифры ниже взяты из них):
- `decomp/f1B2/tasks.py` — граф: 76 задач, у каждой `Файлы:` **и тест-файлы**;
- `decomp/f1B2/probe.py` — проба по §5 design. Считает пересечения по коду и тестам, группы CI
  каждой задачи **настоящим классификатором наставника** (`scripts/test_registry.py` с
  `06a0bbdf4`) с правилом T019, а также пересечение с планами шага 8 и сессии ЕГЭ;
- `decomp/f1B2/sim.py`, `run_d.py` — событийная модель, 80–200 прогонов. Учитывает
  координатора, очередь вливаний и CI как отдельные последовательные ресурсы;
- `decomp/f1B2/sched.py` — точечное расписание HLFET;
- `decomp/f1B/reg/newrule.py` — проверка правила группы тестов на всех 731 тест-модулях базы.

## 0. Итог за минуту

| Мера | Значение |
|---|---|
| Задач | **76**: 7 `[K]`, 11 `[T]`, 52 `[V]`, 5 `[S]`, 1 `[H]`. Из `[V]` 11 переводят код на порт, 7 переводят тесты, 1 чистит тесты от режимов |
| W / S / P | W = 1212 мин-весов; S = **106**: T001 → T003 → T042 → T033 → T065; **P = 11.4** (норма ≥ 2K для K = 4 и 5) |
| Фаза К | 136 = 11% W; глубина 2 у T003 и T006, порядок вливаний T019 → T001 → T002 (§2) |
| Пересечения `Файлы:` + тест-файлы у задач без пути | **0 из 2850 пар**; тесты теперь входят в проверку (§5, §6) |
| Новые тест-модули в `core` | **0**; в `core` остаются те же 2 (`test_main`, `test_integration`), правило T019 не сдвигает ни одного из 731 модуля |
| Точечно, без доработок, без CI | K = 3: 436 мин, K = 4: 335, K = 5: 275 |
| **Прогноз, K = 4, R = 3, p = 0.43, r = 0.10** | вручную, как сейчас: **~950 мин (15.8 ч)**; поезд вливаний и выдача скриптом при нынешнем CI: **~743 мин (12.4 ч)**; плюс CI по пакету 6–10 мин: **~612 мин (10.2 ч)** |
| K = 5 вместо 4 | при нынешнем CI ±0% (743 → 755: шум). При быстром CI −16% (612 → 513) |
| K = 3 (слоты делятся с шагом 8) | ~849 мин при нынешнем CI, ~778 при быстром |
| Запусков исполнителя / ревью | ~133 / ~133 при p = 0.43; ~108 / ~108 при p = 0.25 |
| Деньги | ~$470 при p = 0.43, ~$380 при p = 0.25 |

Главное, что изменилось в выводе. **Узкое место этой фичи — CI и вливания, а не число
исполнителей.** 76 задач — это 80–90 вливаний. Проверка ветки занимает 15–28 мин и идёт по
одной. При партии 4 и красной партии в 10% по каждому вливанию (r = 0.10) CI сам по себе
занимает ~800 мин. Ручной координатор (1 мин на выдачу, 3–8 мин на вливание) занят
~730 мин из ~950. Пока не сделаны поезд вливаний и выдача скриптом, пятый исполнитель ничего
не даёт. Мой совет из круга 1 «K = 5, R = 4» отозван.

Совет: **K = 4, R = 3.** Порядок рычагов по выигрышу:
1. Выдача и вливание скриптом: 950 → 864 мин при партии 4.
2. Партия CI до 8 с делением пополам: 864 → 743.
3. Отпечаток CI по пакету, вне базы: 743 → 612.
4. Только после этого K = 5: 612 → 513.

## 1. Замечания оценщика: что принято, что оспорено

| # | Замечание | Ответ |
|---|---|---|
| 1 | Координатор и вливания в модели бесплатны; при K = 4, p = 0.43–0.6 выходит 806–870 мин, занято 2.2; очередь скриптом — 608–653; K = 5 даёт −3…−4%; партии до 6 краснеют чаще | **Принято целиком, кроме партий.** Модель переписана (`sim.py`): ручной режим при быстром CI даёт 828 мин и 2.38 занятых, координатор занят 736 мин. Это совпадает с оценщиком. Отозван совет K = 5. **Партии — оспорено расчётом (§8.4).** Вероятность красной партии из 6 при r = 0.15 действительно ≈ 62%. Но цена на одно вливание (1 + P_red · ⌈log₂ n⌉) / n при n = 6 равна 0.48 проверки, при n = 4 — 0.49. При r = 0.05: 0.30 против 0.34. Партия больше **не дороже** на вливание, а CI здесь узкое место. В модели при r = 0.10 партия 8 даёт 743 мин, партия 4 — 864, партия 3 — 1017. Задержка вливания внутри партии растёт, но её никто не ждёт: зависимые стартуют от ветки плана, а не от зелёного CI |
| 2 | Владение переводом тестов неявное; тест-файлов нет в `Файлы:`; «0 из 1953 пар» о тестах ничего не говорит; 9 сквозных модулей `courses/tests` без владельца; критерий T052 невыполним | **Принято.** Тесты, которые пишут или читают поля `LearningTask` о ступени и роли, найдены grep'ом по базе: 59 модулей, ~430 строк (`f1B/lt_tests.txt`). Они розданы 7 задачам перевода тестов **T066–T072** с поимённым списком файлов. `courses/tests` разложены на три задачи: T066 — только `test_integration.py` (57 строк), T067 — семейство learning_tasks, T068 — остальные. Тесты, которые читают режимы урока, получили владельцев: поведенческие правят T020/T021/T022 в своих файлах, остальные чистит T074. Проба теперь проверяет пересечения по коду **и** тестам: 0 из 2850 пар. Критерий T052 переписан: «тест-файлы не правит; сторож `--tests` пуст» (§5) |
| 3 | Групп `django:courses` и других нет; `django:acceptance` никто не создаёт; acceptance и learning_process уходят в `core` при `core_ceiling = 2`; `test-registry.json` — ручной храповик, а не генерируемый файл | **Принято.** `Тест-группа:` теперь не пишется руками: проба выводит её из тест-файлов задачи классификатором наставника. Новой группы нет. `[T]` лежат в пакете своей истории и попадают в существующие группы. Правило в `GROUP_RULES` (`learning_process\|course_goal\|step6` → `structure`, `exam_trainer` → `banks`) заводит **T019 [K]** вместе с тестом в `scripts/tests/test_test_registry.py`. Проверено на всех 731 модулях базы: ни один не сменил группу, `core` осталось 2. `test-registry.json` из списка генерируемых убран, в плане его никто не правит |
| 4 | `strict=True` — это pytest, а проект гоняет `manage.py test` (unittest) | **Принято.** Сервер: `@unittest.expectedFailure`. Django ≥ 4.1 считает неожиданный успех ошибкой прогона (release notes 4.1: «DiscoverRunner now returns a non-zero error code for unexpected successes»), а у проекта `django>=4.2,<5.0`. Jest 30: `test.failing`. Playwright: `test.fail()`. Ограничение я назвал: `expectedFailure` засчитывает **любое** исключение, в том числе ImportError. Поэтому срез, снимая метку, прикладывает вывод `hold` (тест краснеет на откате кода) |
| 5 | T050 (17 файлов, ~344 строки), T048 (~246), T049 (~176) — это L вместе с тестами зоны; они нарушают §4 и стоят перед сходкой T052 | **Принято.** Код и тесты разделены: срезы кода тестов не правят, тесты переводят T066–T072. Код разрезан: T048 → T048 + T075 (по файлам `task_classes`), T049 → T049 + T076 (`course_graph_editor`), T050 → T050 (`topic_content`) + T077 (диалог, трек, команды и сиды). Самый большой срез кода теперь T043: `services_learning_tasks.py`, ~64 строки по полям |
| 6 | T003 на пути ждёт T004 — код соседней сессии ЕГЭ | **Принято.** T004 стал нашим `[K]` размера S: интерфейс C15 (`exam_tasks/course_api.py`) и фейк в памяти под тем же контрактным тестом. Реализацию в банке делает **T018**, помеченный как внешний (сессия ЕГЭ или мы). От T018 зависят только T028, T039, T040, T063 и приёмка, а не путь. Проверка: задержка T018 на 300 мин меняет итог на 611 против 612 мин, то есть никак |
| 7 | У клиентских срезов против C25 нет общих примеров ответов; e2e только на приёмке; шов сервер/клиент всплывает поздно | **Принято.** **C27**: JSON-примеры ответов всех ручек §6 в `courses/step6_examples/`, их копия для jest в `__tests__/fixtures/step6/`, сверка копии `scripts/check_step6_examples.py` в быстрой группе. Владелец — T019. Серверный срез проверяет, что ответ ручки совпадает с примером по ключам и типам. Клиентский мокает ответ этим же примером. Расхождение сторон краснеет у того, кто его внёс, ещё до ревью |
| 8 | T021/T050 трогают `topic_content/*` (зона шага 8, в baseline там уже был конфликт) и `exam_tasks/*` (сессия ЕГЭ); нет проверки пересечения с планами в полёте; лимит слотов общий с шагом 8; дать прогноз при K = 3 | **Принято.** Проба считает пересечение с зонами шага 8 (из `feature-2-description.md`) и сессии ЕГЭ: 17 и 6 задач (§6.2). Предложены межплановые рёбра и `task_pairs.py plan --with` (§6.2, §11). Прогноз при K = 3 — в §10 |

## 2. Где я отступаю от `design.md` и почему

| Пункт design | Отступление | Довод |
|---|---|---|
| §3.2 п. 3: задач К 1–3, глубина 1 | 7 задач К; T003 и T006 — глубина 2; порядок вливаний T019 → T001 → T002 | Фича втрое больше модели design (78 AC). Одна К на всё — это L. Фаза К — 11% W при пороге 20%. Порядок T019 → T001 — только порядок вливания: T019 (S, 15 мин) влит к 24-й минуте, T001 сдаётся к 24-й, расписание задержки не показывает. T002 → T001 — общий `course_bank/__init__.py` |
| §3.2 п. 5: по сторонам режем, только если срезов < 2K | Не применяю. Сервер ∥ клиент остался только у T055 ∥ T056 | Карта владения разводит клиентские файлы, а C27 заменяет склейку. Клиентские срезы банка (T031, T034–T038) несут свой компонент. Это M, а не L |
| §3.2 п. 1: одна история — один `[V]` | US7 — 11 срезов кода и 7 срезов тестов **по владению файлами** | У перевода нет сценария. Деление по владению даёт ширину 18 на месте цепочки |
| §3.2 п. 9: тест среза в файле среза | Перевод тестов вынесен в отдельные задачи | Перевод — механика, без смены ожиданий. Сквозные модули (`test_integration.py` на 9 тыс. строк) не принадлежат ни одной зоне кода. Срез кода с тестами зоны становится L (замечание 5) |
| §3 шаг 12: CI партиями 3–4 | Партия — всё накопленное, до 8, красная делится пополам | Расчёт в §8.4: CI здесь узкое место, а большая партия не дороже на одно вливание |
| §7 п. 1: W' = W(1 + 0.7p) | Модель с повторными отказами | При p = 0.43 модель даёт 133 запуска на 76 задач, то есть 1.75 на задачу. Формула даёт 1.3. Проверить на baseline |

## 3. Истории и критерии приёмки

| Ист. | Что | AC | `[T]` (модуль → группа) |
|---|---|---|---|
| US1 | Учебный процесс | 1–7, 9 | T007 `learning_process/tests/test_acceptance_us1.py` → structure; e2e `us1.spec.ts` |
| US2 | Экзамены курса | 8, 10–18 | T008 `learning_process/tests/test_acceptance_us2.py` → structure; e2e `us2.spec.ts` |
| US3 | Выбранные банки, решатель | 19, 19а, 20, 21, 65 | T009 `course_bank/tests/test_acceptance_us3.py` → banks |
| US4 | Раскладка | 22–32 | T010 `course_bank/tests/test_acceptance_us4.py` → banks (AC-26 — `TransactionTestCase`) |
| US5 | Связи, ревизии, покрытие, видимость | 33, 36–42, 64, 70 | T011 `course_bank/tests/test_acceptance_us5.py` → banks |
| US6 | Гейт 3, недостача, квоты | 34, 35, 63, 76, 77 | T012 `course_pipeline/tests/test_acceptance_us6.py` → saga |
| US7 | Задача курса | 55–60, 66–68, 71–73 | T013 `course_bank/tests/test_acceptance_us7.py` → banks (тест миграции — у T051, имя по номеру) |
| US8 | Приём своих задач | 61, 62, 69, 74, 75, 78 | T014 `course_bank/tests/test_acceptance_us8.py` → banks; e2e `us8.spec.ts` |
| US9 | Режимы урока, старые курсы | 43–49 | T015 `lesson/tests/test_acceptance_us9.py` → lessons |
| US10 | Цель и экзамен | 50–53 | T016 `course_goal/tests/test_acceptance_us10.py` → structure |
| US11 | Копирование курса | 54 | T017 `course_structure/tests/test_acceptance_us11.py` → structure |

Метки xfail. Сервер — `@unittest.expectedFailure` на методе, импорт кода фичи внутри теста.
jest — `test.failing`. e2e — `test.fail()`. Среда e2e в CI не входит (`default=False` в
реестре), поэтому e2e гоняет роль `acceptance` на стенде `cc-*` :8092. `[T]` вливаются после
T019: их модули названы под правило группы. Это порядок вливания, а не зависимость от кода К.

## 4. Карта швов (`contracts.md`)

Изменения против круга 1 выделены **жирным**.

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| C1 | `CourseLearningProcess`, умолчания, `settings_for(course)` | T001 | T025, T027, T028, T060 |
| C2 | `has_current_exam`, `linked_exam_count` (через C15) | T006 | T025, T027, T029, T060 |
| C3 | `concurrency.lock_course` и порядок замков R-0 | T001 | T025, T029, T033, T037 |
| C4 | `CourseBank` | T001 | T003, T031, T033, T061 |
| C5 | `CourseTask`, перечисления, ограничения R-22 | T001 | T003, T035–T038, T051, T052, T054, T061 |
| C6 | `CourseBankLayoutRun` | T001 | T033, T034 |
| C7 | `CourseFinalTask.exam_position_refs`, `exemplar_task_ids` | T001 | T060, T062–T064 |
| C8 | `ExamCourse.course` → CASCADE | T001 | — |
| C9 | Порт `course_bank/placement.py`, методы R-23а; до T052 — на колонках | T002; переключает T052 | **T043–T050, T075–T077**, T054, T055 |
| C10 | Помощник `make_learning_task(**kw)` и чтение отметок через порт в тестах | T002 | **T066–T072**, все `[T]` US7/US8 |
| C11 | `course_bank.reader.course_tasks(...)` → `CourseTaskItem` | T003 | T031, T034–T038, T041, T042, T052, T061 |
| C12–C14 | Квоты, проверка отметок, места ступени | T003 | T032, T033, T035, T038, T041, T042, T055 |
| **C15** | **Интерфейс API банка (`exam_tasks/course_api.py`) и фейк под общим контрактным тестом**; реализация — T018 | **T004 (интерфейс), T018 (реализация)** | T003, T006, T028, T029, T039, T040, T063 |
| C16–C17 | Коды, подписи, регистрация правил гейтов с заглушками | T005 | T027, T041, T064 и все, кто отдаёт коды |
| C18–C24 | Маршруты с 501, поля сериализаторов, `create_course` одной транзакцией, перенос `_clone_…`, заглушки раскладки, слушатель, ветка подбора умений | T006 | см. задачи |
| C25 | Клиент: типы, точки монтирования, `api.ts`, `MarksFields` | T005 | T023, T026, T030, T031, T034–T038, T056, T062 |
| C26 | Сторож `scripts/check_step6_writes.py`; **режим `--tests`**: тест-модуль не пишет и не читает `task_class`/`is_trap`/`is_transfer`/`trap_note` у `LearningTask` | T002 → T052 → T053 | все; **критерий T066–T072** |
| **C27** | **JSON-примеры ответов ручек §6 (`courses/step6_examples/*.json`), копия для jest, сверка копии** | **T019** | серверные срезы (ответ = пример по ключам и типам), клиентские срезы (мок = пример) |
| **C28** | **Правило группы тестов в `GROUP_RULES`: `learning_process\|course_goal\|step6` → structure, `exam_trainer` → banks** | **T019** | все задачи, чьи модули названы под правило (`mdeps`) |

Правило поправки — только добавлением (ADR-0019).

## 5. Задачи

Вес: 10 мин × 1.6 (deep) × 1.5 (M). Ожидаемая длительность запуска: S обычный 7–10 мин,
M обычный 10–15, S deep 11–17, M deep 16–25. `BE/` = `services/django-api/courses/`,
`FE/` = `services/frontend/app/(lk)/my-courses/`, `CID/` = `FE/[courseId]/_components/`,
`JT/` = `services/frontend/__tests__/step6/`. В `Тесты:` перечислены тест-файлы задачи,
и проба считает пересечения и по ним. `Тест-группа:` вывел классификатор наставника, руками
её не писали. `Влить после:` — только порядок вливания.

### Фаза К

- [ ] **T019 [K] Правило группы тестов и примеры ответов §6**
  Контракт: владелец C27, C28 · Файлы: `scripts/test_registry.py` (две альтернативы в `GROUP_RULES`), `BE/step6_examples/`, `services/frontend/__tests__/fixtures/step6/`, `scripts/check_step6_examples.py`, `scripts/ci_quick_checks.py` (команда сверки в группе `codes`)
  Тесты: `scripts/tests/test_test_registry.py` (случай: `courses.learning_process.tests.test_x` → structure, существующие модули не сдвигаются), `scripts/tests/test_check_step6_examples_drift.py`
  Зависит от: — · Готово-когда: `test_registry.py --check` зелёный, `core` = 2; на каждую ручку §6 есть пример со всеми полями спеки; сверка краснеет на правке копии
  Риск: обычный · Размер: M · Тест-группа: saga (scripts)
- [ ] **T001 [K] Схема шага 6: модели, одна миграция, каркас пакетов**
  Контракт: C1, C3–C8 · Файлы: `BE/learning_process/{__init__,models,settings}.py`, `BE/course_bank/{__init__,models}.py`, `BE/migrations/0301_step6_schema.py`, `BE/course_goal/models.py`, `BE/exam_codifier/models.py` (CASCADE — согласовать с сессией ЕГЭ, §6.2), `BE/concurrency.py`, `BE/tests/_step6_factories.py`, `docs/engineering/module-{tiers,boundaries}.json`
  Тесты: `BE/learning_process/tests/{test_models,test_lock_order}.py`, `BE/course_bank/tests/test_models.py`
  Влить после: T019 · Готово-когда: миграция накатывается и откатывается; ограничения `CourseTask` ловят обе ссылки, ни одной, повтор, `approved` без даты (тесты краснеют на откате); `settings_for` без строки отдаёт умолчания
  Риск: deep · Размер: M · Тест-группа: banks, structure
- [ ] **T002 [K] Порт на колонках, помощник тестов, сторож**
  Контракт: C9, C10, C26 (с режимом `--tests`) · Файлы: `BE/course_bank/placement.py`, `BE/tests/_learning_tasks_fixture.py` (`make_learning_task` через порт), `scripts/check_step6_writes.py`, `.pre-commit-config.yaml`
  Тесты: `BE/course_bank/tests/test_placement_columns.py`, `scripts/tests/test_check_step6_writes.py`
  Влить после: T001 · Готово-когда: каждый метод R-23а покрыт на колонках; правило версии Р-CT12; сторож ловит запись новых моделей вне пакета; `--tests` на базе печатает список модулей, совпадающий с `f1B/lt_tests.txt` (это опись для T066–T072)
  Риск: deep · Размер: M · Тест-группа: banks, saga (scripts)
- [ ] **T004 [K] Интерфейс API банка для курса и фейк**
  Контракт: C15 (интерфейс) · Файлы: `BE/exam_tasks/course_api.py` (сигнатуры R-23/§12 спеки; тело делегирует в `_backend`, до T018 — фейк)
  Тесты: `BE/exam_tasks/tests/test_course_api_fake.py`: **контрактный набор параметризован по бэкенду**, T018 подключит к нему реальный
  Зависит от: — · Готово-когда: фейк проходит весь контрактный набор (пакетность — одним вызовом; ФИПИ — только собственное происхождение; гонка `link_course` — своё исключение)
  Риск: обычный · Размер: S · Тест-группа: banks
- [ ] **T005 [K] Реестры и регистрация: коды, подписи, гейты, точки клиента**
  Контракт: C16, C17, C25 · Файлы: `config/{response-codes,api-problems}.json`, `config/locale/ru/problems.json`, `.claude/response-codes.json`, `BE/course_pipeline/gates/{registry,rules_lp_exam,rules_course_task,rules_goal_exam}.py`, `services/frontend/types/{courses,step6}.ts`, `FE/new/page.tsx`, `CID/overview/CourseBriefPanel.tsx`, `CID/tabs/TasksTab.tsx`, `CID/step6/{api.ts,MarksFields.tsx,mounts.tsx}`, `services/frontend/utils/problemLabels.ts`
  Тесты: `JT/MarksFields.test.tsx`, `BE/course_pipeline/tests/test_step6_rules_registered.py`
  Влить после: T019 · Готово-когда: `check_codes.py`, `check_problem_catalog.py` зелёные; правила-заглушки зарегистрированы и молчат; точки монтирования на флаге пустые, без флага ничего
  Риск: обычный · Размер: M · Тест-группа: saga, frontend
- [ ] **T003 [K] Читатель задач курса, квоты, места, проверка отметок**
  Почему не одна: читатель читает таблицу T001, свои задачи берёт через порт T002, приём — через C15; вместе это L
  Контракт: C11–C14 · Файлы: `BE/course_bank/{reader,quotas,marks,places}.py`
  Тесты: `BE/course_bank/tests/{test_reader,test_marks_places_rungs}.py` (имя без `quota`: иначе модуль уходит в billing)
  Зависит от: T001, T002, **T004 (интерфейс, не T018)** · Готово-когда: один запрос на вид источника (50 задач); DTO своей задачи до T052 — из порта; `trap_quota_applies` ложна; `rung_places` 11/15
  Риск: deep · Размер: M · Тест-группа: banks
- [ ] **T006 [K] Точки подключения в общих файлах сервера**
  Почему не одна: правит существующие горячие файлы, T001 — новые
  Контракт: C2, C18–C24 · Файлы: `BE/{urls,serializers,services,views}.py`, `BE/course_structure/{clone,clone_rungs}.py`, `BE/course_goal/{views_tasks,exam_ksa}.py`, `BE/learning_process/{urls,views,exams,services,copy}.py`, `BE/course_bank/{urls,views,layout,listeners,copy}.py`
  Тесты: `BE/learning_process/tests/test_routes_stub.py`, `BE/tests/test_create_course_atomic_step6.py`, `BE/course_structure/tests/test_clone_moved.py`
  Зависит от: T004; T001 (стек) · Готово-когда: ручки §6 — 501 на флаге, прежнее без флага; `create_course` — одна транзакция (сбой в заглушке копии → курса нет); перенос `_clone_…` без изменения поведения
  Риск: deep · Размер: M · Тест-группа: structure

### `[T]` — независимые приёмочные тесты (Sonnet, в окне фазы К)

11 задач T007–T017 (таблица §3). Риск у всех обычный. Размер M у T010, T013, T015, T017,
у остальных S. Код К не читают, пишут по `contracts.md`, C27 и спеке. Каждая `[T]` вливается
до срезов своей истории.

### Внешняя реализация C15

- [ ] **T018 [V] Реализация API банка для курса** (соседняя сессия ЕГЭ; в эксперименте — часть фичи)
  Файлы: `BE/exam_tasks/{services,course_api}.py`, `BE/exam_codifier/services.py` · Тесты: `BE/exam_tasks/tests/test_course_api.py`, `BE/exam_codifier/tests/test_course_api.py` (реальный бэкенд подключён к контрактному набору T004)
  Зависит от: T004 · Риск: обычный · Размер: M · Тест-группа: banks

### US9 Режимы урока

| Задача | Что | Файлы кода | Тесты | Зависит от | Риск/Размер | Группа |
|---|---|---|---|---|---|---|
| T020 [V] | Запись и ответы без режимов (R-43, сервер) | `BE/{serializers,services,views,admin}.py`, `course_pipeline/course_patch.py`, `domain_errors/__init__.py`, команды `seed_tariff_testbed`, `seed_ksa_tc_testbed`, `prepare_t1142_manual`, `prepare_t1144_purchase_manual` | **новый** `tests/test_course_detail_no_lesson_modes.py`; **правит** `tests/test_integration.py` (проверки `prefer_pbl` в ответах, стр. ~8991–9248), `tests/test_brief_schema.py` | T006, T077 (сид `seed_course_pipeline`), **T066** (тот же `test_integration.py`) | обычный M | core, lessons, structure |
| T021 [V] | Читатели режимов — константа (R-42) | `topic_content/lesson_modes.py`, `lesson/{serializers,streaming}.py`, `lesson/mode_a/services.py`, `track_manage/{read,serializers}.py`, `structure_gen/{skeleton,tasks}.py`, `task_classes/{rung_layout,rung_layout_db}.py`, `course_graph_editor/read.py` | **новый** `lesson/tests/test_lesson_modes_constant.py`; **правит** `tests/test_structure_gen.py` (курс режима B), `tests/test_lesson_mode_selection.py` (выбор режима) | — | обычный M | lessons, structure |
| T022 [V] | Инвариант «линия А без чтения» по флагу (R-44, R-48) | `graph_invariants/structure_gate.py`, `task_classes/services.py` | **новый** `graph_invariants/tests/test_structure_gate_flag.py`; **правит** `graph_invariants/tests/test_adr087_gate.py` | — | обычный S | saga |
| T023 [V] | Клиент без режимов (R-43, R-48 клиент) | `CID/structure/{TaskClassModal,TopicTreePanel}.tsx`, `FE/new/page.tsx`, `CID/overview/{CourseBriefPanel.tsx,briefFieldLabels.ts,briefConsistency.ts}`, `config/courseCreation.ts`, `utils/{auth,tracks}.ts`, `types/courses.ts`, страница урока и `lessonStopPlan.ts` | `JT/no_lesson_modes.test.tsx` | T005 | обычный M | frontend |
| T024 [V] | Команда `unpublish_legacy_courses` (R-47а) | `management/commands/unpublish_legacy_courses.py` | `management/commands/tests/test_unpublish_legacy_courses.py` | — | deep M | platform |
| **T074 [V]** | **Тесты: убрать режимы из подготовки данных** (ожидания не меняются) | — | `tests/{test_main,test_backfill_adr087}.py`, `subject_areas/tests/test_course_subject_areas.py`, `structure_gen/tests/{test_sync_topic_links,test_phase1_flag_autopath,test_phase1_brief_params}.py`, `access_registry/course_access/tests/test_course_access.py`, `course_pipeline/tests/{test_gate_rules_parity,test_methodology_patch}.py`, `lesson/tests/{test_refusal_codes,test_multi_carrier}.py`, `task_classes/tests/test_rung_regen_knowledge.py` | T020, T021, T022 | обычный S | 8 групп (весь django) |

Готово-когда у T074: `git grep -E "allowed_lesson_modes|prefer_pbl"` по тестам пуст, кроме
тестов миграции T053. Проверки `assert*` в диффе не менялись (скрипт `assert-unchanged`, §8.1).

### US1, US2, US3–US5, US6, US8, US10, US11 — срезы поведения

Поля, общие для всех: `Срез: USn / <сценарий>`. `Приёмка:` — AC своей `[T]`. Серверный
срез сверяет ответ ручки с примером C27. Клиентский мокает ответ этим же примером.
Готово-когда: тесты среза зелёные и краснеют на откате (`hold`), xfail своих AC сняты.

| Задача | Что | Файлы кода | Тесты | Зависит от | `[T]` | Риск/Размер | Группа |
|---|---|---|---|---|---|---|---|
| T025 [V] | Учебный процесс, сервер (R-1…R-5) | `learning_process/{services,validation,serializers}.py` | `learning_process/tests/{test_services,test_validation}.py` | T006 | T007 | deep M | structure |
| T026 [V] | Блок «Учебный процесс» (R-6) | `CID/step6/LearningProcessBlock.tsx` | `JT/LearningProcessBlock.test.tsx` | T005, T019 | T007 | обычный M | frontend |
| T027 [V] | Гейт отправки «пробники ⇒ экзамен» (R-7) | `course_pipeline/{gate_journal,gating}.py`, `publication/views.py`, `gates/rules_lp_exam.py`, `CID/tabs/PublishTab.tsx` | `course_pipeline/tests/test_lp_exam_gate.py` | T005, T006, T046 | T007 | deep M | saga |
| T028 [V] | Вход в «Тренажёр ЕГЭ» (Е-15) | `exam_trainer/services.py`, страница курса ученика, `ExamTrainerEntry.tsx` | `exam_trainer/tests/test_course_entry.py` | T001, **T018** | T007 | обычный M | banks |
| T029 [V] | Экзамены курса, сервер (R-10…R-14) | `learning_process/{exams,views_exams,catalog}.py` | `learning_process/tests/{test_exams,test_exam_catalog}.py` | T006 | T008 | deep M | structure |
| T030 [V] | Экзамены курса, клиент (R-6, R-13а) | `CID/step6/{CourseExamsBlock.tsx,briefDraftMerge.ts,ExamUnlinkDialog.tsx}` | `JT/{CourseExamsBlock.test.tsx,briefDraftMerge.test.ts}` | T005, T019 | T008 | обычный M | frontend |
| T031 [V] | Выбранные банки и решатель (R-17…R-21) | `course_bank/{banks,views_banks}.py`, `CID/step6/CourseBanksBlock.tsx` | `course_bank/tests/test_banks.py`, `JT/CourseBanksBlock.test.tsx` | T003, T006, T019 | T009 | обычный M | banks, frontend |
| T032 [S] | Раскладка: расчёт кандидатов | `course_bank/layout_calc.py` | `course_bank/tests/test_layout_calc.py` | T003 | T010 | обычный M | banks |
| T033 [S] | Раскладка: запись под замком, Celery, журнал | `course_bank/{layout_run,layout,listeners,tasks}.py` | `course_bank/tests/test_layout_run.py` | T006, T042; T032 (стек) | T010 | deep M | banks |
| T034 [V] | «Подобрать ещё» и блок «Задачи из банка» | `course_bank/{candidates,views_layout}.py`, `CID/step6/CourseBankBlock.tsx` | `course_bank/tests/test_candidates.py`, `JT/CourseBankBlock.test.tsx` | T032, T006, T005, T019 | T010 | обычный M | banks, frontend |
| T035 [V] | Ручное добавление и правка связи | `course_bank/{links,views_links}.py`, `CID/step6/LinkDialogs.tsx` | `course_bank/tests/test_links.py`, `JT/LinkDialogs.test.tsx` | T003, T006, T005, T019 | T011 | обычный M | banks, frontend |
| T036 [V] | Приём и отклонение размещения связей | `course_bank/{links_bulk,views_bulk}.py`, `CID/step6/LinkBulkBar.tsx` | `course_bank/tests/test_links_bulk.py`, `JT/LinkBulkBar.test.tsx` | то же | T011 | обычный M | banks, frontend |
| T037 [V] | Новые ревизии, «изменились умения» | `course_bank/{revisions,views_revisions}.py`, `CID/step6/RevisionsModal.tsx` | `course_bank/tests/test_revisions.py`, `JT/RevisionsModal.test.tsx` | то же | T011 | deep M | banks, frontend |
| T038 [V] | Отчёт покрытия D-033 | `course_bank/{coverage,views_coverage}.py`, `CID/step6/CoverageReport.tsx` | `course_bank/tests/test_coverage.py`, `JT/CoverageReport.test.tsx` | то же | T011 | обычный M | banks, frontend |
| T039 [V] | Видимость задач ФИПИ (Е-17) | `exam_tasks/services.py` | `exam_tasks/tests/test_learner_origin_fipi.py` | **T018** | T011 | обычный S | banks |
| T040 [V] | Фикстура стенда Е-10 | `exam_tasks/management/commands/seed_step6_exam_fixture.py` | `exam_tasks/tests/test_seed_step6_fixture.py` | **T018** | — | обычный S | banks |
| T041 [V] | Гейт 3 по задачам курса, квоты по ступени | `gates/{rules_stages,rules_course_task}.py`, `course_pipeline/gating.py`, `meaning`/`title` двух кодов | `course_pipeline/tests/test_gate3_course_tasks.py` | T003, T005, T046, T027 | T012 | обычный M | saga |
| T042 [V] | Один счёт недостачи; генерация после раскладки | `learning_tasks/{deficit,top_up,generation_marks}.py`, `services_learning_tasks.py` | `learning_tasks/tests/test_deficit_single_count.py` | T003, T006, T045, T043 | T012 | deep M | banks |
| T055 [V] | Приём своей задачи и размещения, сервер | `services_learning_tasks.py`, `course_bank/placement.py` (вызов методов T052) | `learning_tasks/tests/test_accept_own_task.py` | T052, T042 | T014, T012 | deep M | banks |
| T056 [V] | Экран «Задачи» для своих задач | `CID/tasks/{EditLearningTaskModal,BulkBar,InboxLT,CreateLearningTaskModal,TreeGroupedPool}.tsx` | `JT/tasks_own_marks.test.tsx` | T005, T019 | T014 | обычный M | frontend |
| T057 [V] | Копия графа (R-12в пп. 3, 8) | `course_structure/clone.py` | `course_structure/tests/test_clone_graph_step6.py` | T006 | T017 | deep M | structure |
| T058 [V] | Копия ступеней по картам | `course_structure/clone_rungs.py` | `course_structure/tests/test_clone_rungs.py` | T006 | T017 | deep M | structure |
| T059 [V] | Копия наследует нарушения источника | `course_structure/guard.py` | `course_structure/tests/test_guard_inherits.py` | — | T017 | deep S | structure |
| T060 [V] | Копия учебного процесса, экзаменов, ссылок | `learning_process/copy.py`, `course_goal/services.py` | `learning_process/tests/test_copy.py` | T006, T029 | T017 | обычный M | structure |
| T061 [V] | Копия банков и связей | `course_bank/copy.py` | `course_bank/tests/test_copy.py` | T006, T003, T031, T058 | T017 | deep M | banks |
| T062 [V] | Позиции КИМ и образцы у итоговой задачи | `course_goal/{services_tasks,serializers_positions}.py`, `CID/overview/{FinalTasksBlock.tsx,finalTasks.ts}` | `course_goal/tests/test_final_task_positions.py`, `JT/FinalTasksPositions.test.tsx` | T006, T005, T019 | T016 | обычный M | banks, frontend |
| T063 [V] | «Подобрать умения» по позиции КИМ | `course_goal/exam_ksa.py` | `course_goal/tests/test_exam_ksa.py` | T006, **T018** | T016 | обычный S | structure |
| T064 [V] | Две автопроверки цели | `gates/rules_goal_exam.py` | `course_pipeline/tests/test_goal_exam_rules.py` | T005 | T016 | обычный S | saga |

### US7 Задача курса

**Перевод кода на порт** (11 срезов). Каждый зависит от T002 и от того, кто раньше держал
его файл. Тесты зоны срез **не правит**: порт на колонках, поведение то же. `Приёмка:` AC-68
по зоне. Готово-когда: grep по файлам среза не находит ORM-обращений к полям отметок
`LearningTask`; модули тестов зоны зелёные без правки. Риск обычный, кроме T047.

| Задача | Файлы | Строк по полям (grep, база) | Доп. зависимость | Размер | Группа зоны (для `check.sh`) |
|---|---|---|---|---|---|
| T043 | `services_learning_tasks.py` | 64 | — | M | banks, `test_integration` (core) по классам LT |
| T044 | `_lt_import.py`, `lt_import.py`, `services_lt_import.py`, `documents/{models,services}.py` | 27 | — | S | documents |
| T045 | `learning_tasks/{answer_forms,deficit,generation_marks,selection,solution_check,top_up}.py`, `learning_task_solver/{author,button,generation,solve_job}.py` | 37 | — | M | banks |
| T046 | `course_pipeline/{auto_pipeline,gating,views}.py`, `gates/{facts,rules_stages,rules_structure}.py`, `saga/{events,reopen}.py`, `publication/views.py` | 49 | — | M | saga |
| T047 | `task_classes/{rung_switch,delete_preview}.py` | 24 | — | S (deep) | banks |
| T048 | `task_classes/{predicates,rung_layout_db}.py` | 47 | T021 | M | banks |
| **T075** | `task_classes/{rung_rule,services,topic_merge}.py` | 38 | T022 | M | banks |
| T049 | `course_structure/{editor,generation,rung_layout}.py`, `structure_gen/{skeleton,tasks}.py` | 32 | T021 | M | structure |
| **T076** | `course_graph_editor/{delete_preview,read,write}.py` | 24 | T021 | S | content |
| T050 | `topic_content/{generation/context,generation/services,lesson_modes,passthrough,services}.py` | 56 | T021 | M | content |
| **T077** | `dialogue/{item_materialization,lesson_setup,orchestrator_b}.py`, `track_manage/{models,planner}.py`, команды и сиды (`archive_non_whole_task_learning_tasks`, `learning_task_target_audit`, `repair_tc_complexity_per_line`, `rung_rule_report`, `seed_course_pipeline`, `seed_t815_demo`, `solution_steps_report`) | ~20 + команды | — | M | lessons |

Строки посчитаны широким шаблоном `is_trap|is_transfer|trap_note|task_class__|task_class=|task_class_id|.task_class`.
Он ловит и собственные поля `TaskClass`, поэтому это верхняя граница. Дифф ≈ 2–3 строки на
находку, то есть самый большой срез T043 даёт ≤ ~190 строк, это M.

**Перевод тестов на помощник порта** (7 срезов, Sonnet). Каждый зависит от T002 (C10).
Код **не правит**. Готово-когда: `check_step6_writes.py --tests` по файлам задачи пуст;
проверки `assert*` в диффе не менялись (скрипт `assert-unchanged`, §8.1); модули зелёные на
колонках. `Приёмка:` AC-68 (тесты). Риск обычный, размер M.

| Задача | Тест-файлы (`BE/…`) | Строк | Доп. зависимость | Группа |
|---|---|---|---|---|
| **T066** | `tests/test_integration.py` (только `LearningTask`-фикстуры и чтения отметок) | 57 | — | core (гонять только классы LT модуля) |
| **T067** | `tests/test_learning_tasks_{deficit,endpoints,generation_reservation,generator_kind,import,old_steps_closed,target_degraded}.py`, `tests/test_learning_task_description_length.py`, `tests/test_lt_import_automapping.py`, `tests/_phase3_fixtures.py`, `tests/_target_ksa_fixtures.py` | 45 | — | banks, documents, graph, structure |
| **T068** | `tests/test_task_class_lesson_models.py`, `tests/test_phase3_fanout.py`, `tests/test_generation_context.py`, `tests/test_lesson_mode_selection.py` | 49 | T021 (тот же `test_lesson_mode_selection.py`) | lessons, structure |
| **T069** | `learning_tasks/tests/{_solution_case,test_answer_form_fields,test_generation_marks,test_initiator_mismatch,test_phase3_failure_outcome,test_solution_rules}.py`, `learning_task_solver/tests/{_case,test_author_write,test_followup_unit,test_generation}.py` | 64 | — | banks, billing |
| **T070** | `course_pipeline/tests/{test_auto_pipeline,test_gate2_content_reading,test_gate_rules_moved_to_server,test_gate_views,test_genre_approval_a2,test_lifecycle_views,test_phase3_no_target_ksa,test_reopen_views,test_transfer_trap_rules}.py`, `publication/tests/test_moderation_views.py`, `methodology_params/tests/test_readers.py` | 47 | — | saga |
| **T071** | `task_classes/tests/{_rung_layout_fixtures,_rung_switch_fixtures,test_learning_tasks_target_request,test_rung_layout_button,test_rung_regen_cascade,test_rung_regen_db,test_rung_switch_import,test_rung_layout_db}.py`, `course_graph_editor/tests/{test_topic_merge_delete,_topic_merge_fixtures}.py`, `course_structure/tests/test_deletion.py`, `structure_gen/tests/{test_augment_upsert,test_rung_layout_phase1}.py` | 42 (+3 режимы) | T021 (убирает и режимы из подготовки в трёх модулях) | banks, content, documents, structure |
| **T072** | `dialogue/tests/{_mode_b_e2e_fixture,_orchestrator_b_fixture,test_e2e_mode_b,test_lesson_setup,test_orchestrator_b}.py`, `lesson/tests/{test_lesson_lifecycle,test_lesson_runtime_canon,test_topic_modes}.py`, `gap_ingestion/tests/test_gap_ingestion.py`, `management/commands/tests/test_archive_non_whole_task_lt_command.py` | 70 | — | banks, graph, lessons, saga |

Опись — grep по базе: модули, где есть `LearningTask` **и** поле отметки (`f1B/lt_tests.txt`,
59 модулей). Модули, которые достают задачу через связь и не называют `LearningTask`, grep
пропускает. Их найдёт `--tests` сторожа T002: он печатает опись при сдаче T002, до старта
T066–T072. Остаток, если он появится, получает задачу T078 [V] S до T052. Это названный
предел, а не дыра.

**Последовательные задачи US7:**

- [ ] **T051 [S] Перенос своих задач в задачи курса (R-22а), проверочная команда.** Почему не срез: миграция данных. Файлы: `BE/migrations/0302_course_task_from_learning_task.py` (номер — при вливании), `BE/management/commands/check_learning_task_course_alignment.py`. Тесты: `BE/tests/test_migration_0302_course_task_transfer.py` (имя — по правилу `check_migration_tests.py`, переименовывается вместе с номером). Зависит от: T001. Риск: deep · M · группа banks.
- [ ] **T052 [S] Переключение порта и читателя на `CourseTask`; `register` пишет; сторож полей.** Почему не срез: точка, где исчезает вторая правда о ступени. Файлы: `BE/course_bank/{placement,reader}.py`, `scripts/check_step6_writes.py`. Тесты: `BE/course_bank/tests/test_placement_switch.py`. Зависит от: T043–T050, T075–T077, T066–T072, T051, T003. **Готово-когда: все группы django зелёные; T052 не правит ни одного тест-файла, кроме своего; сторож `--tests` по всему дереву пуст; новые методы `approve_placement`, `placement_of`.** Риск: deep · M · группа banks + полный прогон партии.
- [ ] **T053 [S] Удаление колонок `learning_task` и режимов курса и брифа.** Файлы: `BE/models.py`, `BE/migrations/0303_drop_lt_marks_and_lesson_modes.py`, `scripts/check_step6_writes.py`. Тесты: `BE/tests/test_migration_0303_drop_lt_marks.py`. Зависит от: T052, T020–T024, T074. Риск: deep · S · группа platform + полный прогон.
- [ ] **T054 [V] Удаление ступени и темы при задачах курса.** Файлы: `BE/course_bank/detach.py`, `BE/course_structure/{deletion,rung_layout}.py`, `BE/task_classes/rung_switch.py`. Тесты: `BE/course_bank/tests/test_detach.py`. Зависит от: T003, T047, T049. Риск: deep · S · banks.

### Хвост

- [ ] **T065 [H] Реестры документов, журнал, находки «хвост», правки источников по §8 спеки.** Файлы: `docs/INDEX.md`, `CHANGELOG.md`, `docs/journal/`, README и AGENTS новых пакетов, записи в Ж, Пар §3.2, ADR-121 (отметки «Спросить»). Зависит от: все `[V]`/`[S]`. Обычный · S.

## 6. Карта владения

### 6.1. Горячие файлы внутри плана (порядок = путь в графе)

| Файл | Владельцы по порядку |
|---|---|
| `courses/{services,serializers,views}.py` | T006 → T020 |
| `services_learning_tasks.py` | T043 → T042 → T055 |
| `course_pipeline/gating.py` | T046 → T027 → T041 |
| `gates/rules_stages.py` | T046 → T041 |
| `publication/views.py` | T046 → T027 |
| `task_classes/services.py` | T022 → T075 |
| `task_classes/rung_layout_db.py` | T021 → T048 |
| `task_classes/rung_switch.py` | T047 → T054 |
| `course_structure/rung_layout.py` | T049 → T054 |
| `course_structure/clone.py` | T006 → T057 |
| `structure_gen/{skeleton,tasks}.py` | T021 → T049 |
| `course_graph_editor/read.py` | T021 → T076 |
| `topic_content/lesson_modes.py` | T021 → T050 |
| `learning_tasks/{deficit,top_up,generation_marks}.py` | T045 → T042 |
| `seed_course_pipeline.py` | T077 → T020 (T020 его не трогает; ребро ради сидов режимов) |
| `exam_tasks/services.py` | T018 → T039 |
| `exam_tasks/course_api.py` | T004 → T018 |
| `course_bank/placement.py` | T002 → T052 → T055 |
| `course_bank/reader.py` | T003 → T052 |
| `scripts/check_step6_writes.py` | T002 → T052 → T053 |
| `models.py` | только T053 |
| `FE/new/page.tsx`, `CourseBriefPanel.tsx`, `types/courses.ts` | T005 → T023 |
| `config/response-codes.json`, `locale/ru/problems.json` | T005 → T041 |
| **`tests/test_integration.py`** | **T066 → T020** |
| **`tests/test_lesson_mode_selection.py`** | **T021 → T068** |
| **`task_classes/tests/{test_rung_regen_db,test_rung_layout_db,_rung_layout_fixtures}.py`** | **только T071** (и отметки, и режимы; ребро T021 → T071) |
| **`graph_invariants/tests/test_adr087_gate.py`** | **только T022** |
| **`scripts/test_registry.py`** | **только T019** |

Генерируемые файлы (`shared` в `pair-rules.txt`): `docs/engineering/module-map.md` и схема
API. При rebase их перегенерируют. **`test-registry.json` в этот список больше не входит:**
это ручной храповик. В плане его не правит никто: правило T019 раскладывает новые модули без
исключений, а `core_ceiling` остаётся 2.

Что карта не видит:
- **смысловое пересечение** — швы C11–C14 в К; ревьюеру среза называются ветки в полёте с тем
  же `Контракт:`;
- **поломка тестов зоны от перевода кода** (например, `assertNumQueries` после порта). Срез кода
  тест не правит: он докладывает, координатор ставит ребро «тест-задача зоны → срез», срез
  делает rebase. Это смена порядка одного ребра, а не два владельца сразу.

### 6.2. Пересечение с планами в полёте (шаг 8, сессия ЕГЭ)

Проба (`probe.py`) сверила `Файлы:` и тесты с зонами шага 8 из `feature-2-description.md` и
сессии ЕГЭ из описания фичи 1.

| План | Наши задачи, задевающие его зону | Главные общие файлы |
|---|---|---|
| Шаг 8 | 17: T005, T006, T017, T021, T022, T023, T041, T048, T049, T050, T054, T057, T058, T059, T071, T074, T075 | `topic_content/services.py` и `generation/*` (T050), `task_classes/{services,predicates}.py` (T022, T075, T048), `course_structure/*` (T049, T054, T057–T059), `gates/registry.py` и `response-codes.json` (T005, T041), `TaskClassModal.tsx` и `utils/auth.ts` (T023), `lesson/mode_a/` (T021) |
| ЕГЭ | 6: T001, T004, T018, T028, T039, T040 | `exam_codifier/models.py` (CASCADE в T001), `exam_tasks/services.py` (T018, T039), `exam_trainer/services.py` (T028) |

Как закрыто:
1. **Межплановые рёбра.** Координатор держит общий для обоих планов файл `plan-edges.md` со
   строками `шаг6:T050 → шаг8:Txxx (topic_content/services.py)`. `task_pairs.py plan --with
   <tasks.md соседа>` краснит пересечение `Файлы:` у задач разных планов без ребра — как
   внутри плана. Кто первый, решает ранг в объединённом графе. Наши T050, T048, T075, T049
   стоят на пути к сходке T052, поэтому по умолчанию первые они. `TaskClassModal.tsx` — T023,
   потом шаг 8 (передача §8 спеки).
2. **Реестры** (`response-codes.json`, `gates/registry.py`) между планами — `serial`: одна
   правка за раз. Наша правка T005 — одна, и в фазе К.
3. **ЕГЭ.** `exam_tasks/course_api.py` — новый файл, он наш. В `exam_tasks/services.py` и
   `exam_codifier/models.py` правка согласуется с владельцем сессии строкой в `plan-edges.md`.
   Если сессия не отдаёт файл, T018 делает она, а наш путь от этого не зависит (замечание 6).
4. **Слоты общие.** Если шаг 8 идёт одновременно и лимит 4–5 на обе фичи, этой фиче
   достаётся 3. Прогноз для K = 3 — в §10.

## 7. Расписание по слотам (точечное, HLFET, без доработок)

K = 4, R = 3, ревью 8, вливание поездом 1.5 мин по одному, выдача скриптом, CI не на пути.
Окончание — 335 мин (K = 3 — 436, K = 5 — 275, K = 6 — 235). Полный вывод:
`decomp/f1B2/sched4.txt`, `sched5.txt`.

```
T019 [K] слот 1:    0–  15, влита   24      T066 [V] слот 1:   71–  86, влита   96
T001 [K] слот 2:    0–  24, влита   34      T067 [V] слот 3:   73–  88, влита   98
T002 [K] слот 3:    0–  24, влита   35      T069 [V] слот 2:   78–  93, влита  102
T015 [T] слот 4:    0–  15, влита   26      T070 [V] слот 4:   79–  94, влита  104
T013 [T] слот 1:   15–  30, влита   42      T072 [V] слот 1:   86– 101, влита  110
T004 [K] слот 4:   15–  25, влита   36      T075 [V] слот 3:   88– 103, влита  112
T021 [V] слот 2:   24–  39, влита   48      T048 [V] слот 2:   93– 108, влита  118
T022 [V] слот 3:   24–  34, влита   44      T049 [V] слот 4:   94– 109, влита  119
T017 [T] слот 4:   25–  40, влита   50      T050 [V] слот 1:  101– 116, влита  126
T012 [T] слот 1:   30–  40, влита   52      T068 [V] слот 3:  103– 118, влита  128
T051 [S] слот 3:   34–  58, влита   68      T071 [V] слот 2:  108– 123, влита  134
T003 [K] слот 2:   39–  63, влита   72      T044 [V] слот 4:  109– 119, влита  129
T047 [V] слот 1:   40–  56, влита   66      T076 [V] слот 1:  116– 126, влита  136
T006 [K] слот 4:   40–  64, влита   74      T005 [K] слот 3:  118– 133, влита  142
T043 [V] слот 1:   56–  71, влита   80      ...
T045 [V] слот 3:   58–  73, влита   82      T052 [S] слот 1:  136– 160, влита  174
T046 [V] слот 2:   63–  78, влита   88      T053 [S] слот 2:  241– 257, влита  266
T077 [V] слот 4:   64–  79, влита   89      T065 [H] слот 1:  316– 326, влита  335
```

Все 4 слота заняты от 0 до ~303. Окно фазы К (0–74) заполняют `[T]`, T021, T022, T051 и T047.
HLFET ставит T005 поздно (118): у его потребителей, клиентских срезов, низкий ранг. Это
правильно, они не на пути. Сходка перед T052 наступает в 136: восемнадцать срезов перевода
плюс T051 и T003 сделаны к ~136. В круге 1 это было 96, но тогда не было перевода тестов,
который требовался для честного критерия T052.

## 8. Тесты, документы, ревью, вливания

### 8.1. Тесты

- `[T]` по истории пишутся до кода, другим агентом (Sonnet). Метки: `@unittest.expectedFailure`
  на сервере, `test.failing` в jest, `test.fail()` в e2e. Модуль лежит в пакете истории и
  попадает в существующую группу через правило C28. Срез снимает метки своих AC и прикладывает
  `hold`: откат кода среза к базе → тесты `Готово-когда:` краснеют. Это закрывает слабость
  `expectedFailure`, который засчитывает любое исключение.
- Тест среза лежит в файле среза. Перевод старых тестов на порт — задачи T066–T072. Чистка
  режимов из подготовки данных — T074. Поведенческие тесты режимов правят T020–T022.
- **Скрипт `assert-unchanged`** для задач перевода тестов: в диффе нет изменённых или удалённых
  строк `self.assert*`, `assertNumQueries`, `expect(`. Нарушение уходит в `доработка` без
  ревью. Ревьюер такой задачи смотрит одно: подготовка данных та же по смыслу.
- `check.sh` исполнителя гоняет **модули своих `Тесты:`** и модули зоны (для срезов кода), а не
  всю группу. Исключение — `test_integration.py` (группа `core`, ~1500 с). T043 и T066 гоняют
  только классы модуля про learning tasks. Полный прогон — у партии CI и у T052, T053.
- `Тест-группа:` пишет не человек: проба выводит её из `Тесты:` классификатором проекта. Если
  у проекта нет `scripts/test_registry.py`, поле пустое и проба молчит (no-op, правило базы).

### 8.2. Документы

README и AGENTS новых пакетов — в T001 (каркас) и в срезе, если тот меняет поведение пакета.
Общие реестры (INDEX, CHANGELOG, журнал) и правки источников по §8 спеки — только T065.

### 8.3. Ревью

Пул R = K − 1. Одна линза: логика, `Контракт:`, `Готово-когда:`/AC. Механику (поезд, `hold`,
`assert-unchanged`, сверку с примером C27, `check.sh`) сделал скрипт при сдаче. Для `[K]` —
линза «хватит ли срезам», для `[T]` — «каждый AC покрыт, тест бьёт обе стороны», для перевода
тестов — «подготовка та же». Вердикт «можно сливать, хвост» уводит мелочи в T065. Второй
круг — только по находкам, третий — человек.

### 8.4. Вливания и CI

**Поезд вливаний.** Скрипт держит очередь. Последовательно идёт только `rebase` +
`merge --ff-only` + пуш, ~1–2 мин. `check.sh` после rebase запускается в рабочем дереве
задачи параллельно с другими: только если rebase задел файлы её групп, иначе пропускается.
Это то же устройство, что у merge train в GitLab
([merge trains](https://docs.gitlab.com/ci/pipelines/merge_trains/): конвейеры кандидатов
идут параллельно, каждый поверх предыдущих) и у очереди GitHub
([merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue):
группы до заданного размера, сборка параллельно). Ручное вливание 3–8 мин силами
координатора в модели занимает ~460 мин из ~900: это последовательный ресурс размером с
половину фичи.

**Выдача скриптом.** `task_pairs.py next` выдаёт и запускает исполнителей и ревьюеров из
скрипта процесса. Координатор (LLM-сессия) включается только на исключениях: третий круг,
конфликт поезда, красный CI, поправка шва. В модели это 0.3 мин на событие против 1 мин.

**CI.** Партия — всё, что влито с начала прошлой проверки, **до 8**. Красная партия делится
пополам, виновника исправляют вперёд (новая задача, ранг виновника). Зависимые CI не ждут:
они стартуют от ветки плана после поезда. Ждёт только конец фичи. Расчёт цены одного
вливания в проверках, (1 + P_red · ⌈log₂ n⌉) / n:

| r (доля вливаний, ломающих чужую группу) | n = 3 | n = 4 | n = 6 | n = 8 |
|---|---|---|---|---|
| 0.05 | 0.43 | 0.34 | 0.30 | 0.25 |
| 0.10 | 0.51 | 0.42 | 0.40 | 0.34 |
| 0.15 | 0.59 | 0.49 | 0.48 | 0.40 |

На ~85 вливаний при r = 0.10 это 44 проверки при n = 3, 36 при n = 4, 29 при n = 8. Умножить
на 15–28 мин. При нынешнем отпечатке CI **сам** занимает 600–950 мин, больше всей работы
исполнителей. Модель это подтверждает (K = 4, p = 0.43, r = 0.10): n = 3 → 1017 мин, n = 4 →
864, n = 6 → 820, n = 8 → 743. При r = 0.05: 839 / 698 / 691 / 663. Довод оценщика верен
наполовину. Красная партия из 6 действительно вероятнее (62% при r = 0.15), но на одно
вливание она не дороже, а когда CI — узкое место, это и решает.

Рычаг больше, чем партия, лежит вне базы. Это отпечаток групп CI у наставника: любая правка
`services/` сбрасывает все группы django. При проверке 6–10 мин (группы по пакету) K = 4 даёт
612 мин вместо 743. Предложение для проекта, не для базы.

## 9. Конфликты и простой — где они будут

1. **CI.** Главный простой этой фичи: после ~550-й минуты исполнители почти свободны, а CI
   дочищает партии. Лечится партией до 8 и отпечатком по пакету (§8.4).
2. **Координатор и вливания вручную.** ~730 мин занятости координатора при K = 4. Лечится
   поездом и выдачей скриптом. Без этого K = 5 не нужен.
3. **Сходка перед T052**: 18 срезов перевода плюс T051 и T003. При p = 0.43 в среднем 7–8 из 18
   уйдут на доработку, и T052 ждёт последнего. Смягчение: у перевода тестов p ниже (механика,
   `assert-unchanged`), в модели я этого не учёл, то есть оценка консервативна. Срезы перевода
   первые по рангу.
4. **Шаг 8 в `topic_content/*`, `task_classes/*`, `course_structure/*`.** 17 наших задач.
   Закрыто межплановыми рёбрами (§6.2). Без них пересечение повторит конфликт, который был у
   baseline: предупреждение оценщика.
5. **`services_learning_tasks.py`**: три владельца подряд (T043 → T042 → T055). T055 ждёт T042.
6. **`test_integration.py`**: два владельца (T066 → T020). T020 не на пути, но T053 его ждёт.
7. **Миграции**: три миграции фичи на одном пути (T001 → T051 → T052 → T053) плюс соседи по
   цепочке. Номер даётся в поезде. У тестов миграций имя с номером: поезд переименовывает их
   вместе с файлом миграции (`check_migration_tests.py`).
8. **Стек T006 от T001**: каскад, если T001 вернётся по смыслу шва. Координатор пишет каждый
   такой отказ в журнал (q).
9. **Стенд e2e** — один `cc-*` :8092. Приёмка историй идёт последовательно, ~30 мин хвоста.

## 10. Оценка времени

Модель `sim.py`: ревью 5–12 мин, исполнитель — вес × U(0.7, 1.4), доработка 0.7 × вес,
CI 15–28 мин (или 6–10 при отпечатке по пакету), приёмка 30 мин. 80 прогонов на клетку, шум
±30 мин. Цифры — минуты до зелёного CI на всём плюс приёмка.

| Режим | K = 3, R = 2 | K = 4, R = 3 | K = 5, R = 4 |
|---|---|---|---|
| Вручную (коорд. 1 мин/выдача, вливание 3–8), CI 15–28, партия 4, p = 0.43 | 1000 | **948** | 967 |
| Вручную, CI 6–10, партия 6, p = 0.43 (координатор — узкое место) | 936 | 828 | 830 |
| Очередь скриптом 3–8, коорд. 1, CI 6–10, партия 6, p = 0.43 | 834 | 668 | 592 |
| Поезд 1–2, выдача скриптом 0.3, CI 15–28, партия 8, p = 0.43 | 849 | **743** | 755 |
| то же, p = 0.25 | 784 | 735 | 732 |
| Поезд, выдача скриптом, **CI 6–10**, партия 6, p = 0.43 | 778 | **612** | **513** |
| то же, p = 0.25 | 653 | 525 | 445 |
| Нижняя граница: CI не на пути, p = 0.43 | 715 | 564 | 468 |
| Точечно, без доработок и CI | 436 | 335 | 275 |

Выводы:
- **K = 4, R = 3.** Пятый слот окупается только при быстром CI и скриптовой выдаче (−16%).
  При нынешнем CI он даёт 0%.
- **K = 3** (слоты делятся с шагом 8): 849 мин при нынешнем CI, 778 при быстром. От K = 4 это
  +14…+27%. Если обе фичи идут одновременно, им выгоднее делить 5 слотов как 3 + 2, чем
  ставить 4 + 4: CI у них общий, и он не растягивается.
- Средняя занятость исполнителей за всю фичу — 2.4–3.2 из 4. Во время веера (до ~500 мин) она
  близка к 4. Хвост тянет CI, а не граф: P = 11.4.

Деньги по медианам наблюдений (implementer ~$0.94, deep ~$4.9, reviewer ~$1.5; 1.75 запуска на
задачу при p = 0.43): 21 deep × 1.75 × $4.9 ≈ $180, 55 обычных × 1.75 × $0.94 ≈ $90, ~133 ревью ×
$1.5 ≈ $200. Итого **~$470**. При p = 0.25 (1.42 запуска) — ~$380. Против круга 1 добавилось 13
задач, из них 8 дешёвых Sonnet-задач перевода тестов.

## 11. Что меняется в базе (дополнительно к §8 design)

| Файл | Изменение |
|---|---|
| `scripts/task_pairs.py` | `plan`: пересечения по `Файлы:` **и тест-файлам**; `--with <tasks.md>` — пересечение с планами в полёте, межплановые рёбра из `plan-edges.md`; поле `Тесты:`; `Тест-группа:` выводится классификатором проекта, если он есть (иначе no-op); `Влить после:`. `train`: очередь вливаний (последовательно только rebase + ff + пуш, `check.sh` после rebase — только при задетых группах). `next --launch` — выдача из скрипта процесса |
| `scripts/` (новое) | `assert_unchanged.py`: в диффе задачи перевода тестов нет изменённых проверок |
| `skills/day/SKILL.md` | координатор только на исключениях; CI партией «всё накопленное, до 8», красная — пополам, исправление вперёд; K = 4 по умолчанию, K = 5 только при CI ≤ 10 мин и скриптовой выдаче |
| `agents/architect.md` | при переводе на новый шов — отдельные задачи перевода тестов с поимённой описью (grep + сторож), сквозные тест-модули — своей задачей; JSON-примеры ответов — шов К |
| `agents/implementer*.md`, `agents/reviewer.md` | метки xfail по раннеру проекта (`expectedFailure` / `test.failing` / `test.fail()`), а не pytest; линза ревью «подготовка та же» для перевода тестов |
| `scripts/tests/` | случаи: пересечение по тест-файлу без ребра → красное; межплановое пересечение без ребра → красное; `assert-unchanged` ловит правку `assert` |

Все пробы — отчёт, не гейт, поэтому выпуск патчевый.

## 12. Что проверить по baseline

- Сколько у baseline вливаний и проверок CI, какой был простой на CI и на ручном вливании.
  По модели это главный источник времени, больше доработок.
- Какой у baseline r — доля вливаний, после которых CI краснел. От неё зависит партия.
- Сколько у baseline задач перевода тестов и были ли они отдельными. Если нет, сколько отказов
  ревью пришлось на тесты, переделанные внутри срезов кода.
- Какое у baseline p на механических задачах (перевод) и на задачах поведения. Если у
  механических p < 0.15, моя оценка завышена на ~50–80 мин.
- Пересекались ли у baseline задачи шага 6 и шага 8 по `topic_content/*` и сколько это стоило.
