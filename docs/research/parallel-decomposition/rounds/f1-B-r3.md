# Фича 1 (шаг 6 пайплайна курса): разложение и план. Команда B, круг 3

Дата 2026-11-24. Процесс: `design.md`. Прошлая версия: `f1-B-r2.md`. Вход тот же:
`feature-1-description.md`, санированная спека, код наставника **только на `06a0bbdf4`**
(`git show`, `git ls-tree`, `git grep`). Запрещённые пути, ветки, задачи Narta и baseline я не
открывал. Отчёты оценщика (`f1-eval-r*.md`) и его сверочные файлы (`evalchk/`) тоже не открывал,
кроме модели `evalchk/r2/simB_poison.py`, на которую ссылается замечание 3. Работал только по
замечаниям из задания.

Скрипты (все цифры ниже взяты из них), каталог `decomp/f1B3/`:
- `tasks3.py` — граф круга 2 с правками этого круга, по пунктам, с комментарием к каждой;
- `probe3.py` — проба по §5 design. Путь считается **тремя способами**: только по рёбрам старта
  (так было в круге 2), по всем рёбрам со сложением (так считает оценщик) и по двум временам
  (старт и вливание). P берётся от худшего из трёх;
- `sim3.py`, `run3.py` — событийная модель, 150 прогонов на клетку. Новое в ней: откат
  виновника красной партии, исправление вперёд с отравлением ветки для сравнения, приоритет фаз
  К и `[T]`, проверка групп при сдаче. Вывод — `run3.out`;
- `sched3.py` — точечное расписание HLFET (`sched4.txt`, `sched5.txt`);
- `ltcls2.py` — разбор AST 59 тест-модулей описи: к какой модели относятся поля отметки.
  Списки — `drop.txt`, `keep.txt`, `read_without_rung.txt`.

## 0. Итог за минуту

| Мера | Значение |
|---|---|
| Задач | **76**: 7 `[K]`, 11 `[T]`, 52 `[V]`, 5 `[S]`, 1 `[H]` |
| W / S / P | W = 1202 мин-весов. S = **106** по всем трём способам: T001 → T003 → T042 → T033 → T065. **P = 11.3**, это норма P ≥ 2K и для K = 4 (8), и для K = 5 (10). С ревью и вливаниями на пути (5 звеньев × ~10 мин) путь занимает ~155 мин реального времени |
| Фаза К | 136 = 11% W. Все 7 `[K]` выданы до 24-й минуты, последняя влита на 72-й (T003). T005 стартует на **10-й** минуте, в круге 2 стартовала на 118-й |
| Стек | Одно ребро: T032 → T033 внутри `[S]`-цепочки (разрешено design §4). Стек T006 от T001 **снят** |
| Пересечения `Файлы:` и тестов у задач без пути | **0 из 2850 пар**. README, AGENTS, `loc-budget.json` и `test_registry.py` теперь входят в `Файлы:` своих владельцев |
| Точечно, без доработок, без CI | K = 3: 434 мин, K = 4: 333, K = 5: 272 |
| **Главный прогноз, K = 4, p = 0.55** (середина 0.5–0.6) | как сейчас (узкий `check.sh`, r = 0.15, CI 15–28, партия 4, откат виновника): **~1190 мин (~20 ч)**, и пятый слот ничего не даёт. Проверка групп задачи при сдаче (r = 0.05): **~750 мин (12.5 ч)**. Плюс CI по пакету 6–10 мин: **~660 мин (11 ч)**. K = 5 при этом: ~560 |
| При p = 0.72 (факт этой фичи) | 1210 / 830 / 780 мин. K = 5: 1165 / 740 / 660 |
| Запусков исполнителя и ревью | ~151 и ~151 при p = 0.55; ~186 и ~186 при p = 0.72 |
| Деньги | ~$530 при p = 0.55, ~$660 при p = 0.72 |

Главный вывод не изменился, но стал жёстче. **Время этой фичи определяет CI, а не число
исполнителей.** При честном r = 0.15 CI занят ~51 проверку по ~21 мин, то есть ~1100 мин, и это
последовательный ресурс. K = 3, 4 и 5 дают одно и то же: 1157–1194 мин. Рычаги по порядку:
1. Проверка групп своей задачи при сдаче, скриптом и параллельно ревью: 1194 → 754 мин при r =
   0.05, → 951 при r = 0.10. Это главное.
2. Отпечаток CI по пакету (вне базы, у проекта): 754 → 660.
3. Только после этого K = 5: 660 → 562 (−15%).

## 1. Замечания оценщика по кругу 2: что принято, что оспорено

| # | Замечание | Ответ |
|---|---|---|
| 1 | Путь занижен: 106 вместо 145, рёбра «Влить после» не учтены. P = 8.4, совет K = 5 противоречит P ≥ 10 | **Принято по существу, рёбра сняты.** Довод о способе счёта я бы оспорил: «Влить после» не задерживает старт, и по двум временам путь был 106 и в круге 2 (T019 влита на 24-й минуте, T001 сдана на 24-й). Но оценщик прав в том, что ребро порядка — это риск: доработка T019 задержала бы T001. Поэтому рёбра убраны, а не переименованы. (а) Правило группы тестов (C28) переехало из T019 в **T001**: кто заводит пакет, тот заводит и его группу. (б) Ребро T002 → T001 держалось на общем `course_bank/__init__.py`. Теперь пустые `__init__.py` новых пакетов (`course_bank`, `course_bank/tests`, `learning_process`, `learning_process/tests`) объявлены одинаковым добавлением: каждая задача создаёт пустой файл, а git сливает два одинаковых добавления без конфликта. Проверено: rebase ветки с тем же пустым файлом проходит чисто (`scratchpad/gitaa`). Правило в `pair-rules.txt` — `shared-empty`, содержимое в них запрещено. (в) T006 больше не ждёт T019. Итог: S_start = S_add = S_merge = **106**, P = 11.3 ≥ 10. Совет K = 5 при быстром CI теперь укладывается в норму P ≥ 2K |
| 2 | Стек T006 от T001 при 52 срезах — красное по §2.1 и §5, в отступлениях не назван. T006 — deep, ~20 горячих файлов, 18 потребителей, каскад | **Принято, стек снят.** T006 зависит только от T004. Заглушки ручек §6 отдают 501 и моделей T001 не импортируют. `create_course` одной транзакцией и перенос `_clone_…` модели шага 6 не трогают. Пакетные `__init__` — по пункту 1(б). Семь срезов, которые раньше получали модели T001 через стек (T025, T027, T029, T060, T062, T063, T064), теперь называют T001 в `Зависит от:` сами. `views.py` из `Файлы:` T006 убран: маршруты идут в `urls.py` пакетов. Цена — ноль: в расписании круга 2 T006 и так стартовала на 40-й минуте, теперь стартует на 24-й и влита на 58-й. Отказ T001 по смыслу шва больше не задевает работу, уже начатую поверх неё. T006 остаётся deep M с 18 прямыми потребителями. Это обычный риск `[K]`, он стоит в предупреждениях пробы |
| 3 | Исправление вперёд при партии до 8: виновник в ветке плана краснит следующие. С поправкой 892 вместо 749 (r = 0.10), 1211 вместо 938 (r = 0.20). Нужен откат виновника, как в GitLab merge train | **Принято.** Красную партию делят пополам. Найденного виновника **откатывают** с ветки плана через поезд (1–2 мин) вместе с его потомками, влитыми после него. Потомки ждут повторного вливания виновника и вливаются заново без доработки. Остальные члены партии считаются зелёными: деление их проверило. В модели (`sim3.py`) у каждого вливания свой признак «ломает» с вероятностью r, разыгранный один раз. В круге 2 и в `simB_poison.py` он разыгрывался заново на каждой проверке, и повторная проверка невиновных могла покраснеть снова. При K = 4, p = 0.43: откат при r = 0.15 и партии 4 даёт **1178 мин**, исправление вперёд — **1521**. Откат выигрывает −23%. Модель оценщика подтверждена по направлению. Партия: при r = 0.15 лучше 4 (1178 против 1226 у партии 8), при r = 0.05 — 8 |
| 4 | README и AGENTS пакетов правят срезы, «если меняют поведение»: в `course_bank` до 10 параллельных задач без пути, файла нет в `Файлы:`, а `check_module_readme` стоит в pre-commit | **Принято.** README и AGENTS новых пакетов (`learning_process`, `course_bank`) создаёт **T019** вне пути, со всеми четырьмя обязательными разделами `check_module_readme.py` и перечнем модулей из `contracts.md`: план их уже знает. Хук срабатывает только на `README.md` и `__init__.py`, а срезы не трогают ни то, ни другое. Описание устройства по итогам дописывает **T065**, единственный второй владелец, после всех срезов. Срезам правка README и AGENTS запрещена. Своё «как устроено» они кладут в доклад, T065 собирает. Путь T019 → T065 в графе есть |
| 5 | Главный прогноз при p = 0.43 и 0.25. Факт фичи — 0.72, просили 0.5–0.6 | **Принято.** Главная строка — p = 0.55. Таблица §10 считает p = 0.25, 0.43, 0.55 и 0.72 для каждого режима и K = 3, 4, 5, с 90-м перцентилем |
| 6 | `check.sh` гоняет только модули своих `Тесты:` и зоны — это уже, чем группа у A, а r = 0.10. Должен быть ≥ 0.15 | **Принято.** Режим «как есть» считается при r = 0.15, чувствительность — при 0.20. Вывод из этого жёсткий: при r = 0.15 фича идёт ~1190 мин при любом K. Отсюда предложение (§8.4): при сдаче скрипт гоняет **группы** задачи (`Тест-группа:`), параллельно ревью, не занимая слот. Остаточное r не мерили, поэтому считаю 0.05 и 0.10 |
| 7 | 6 тест-модулей создают `LearningTask` через ORM без полей отметки, владельца нет, сторож `--tests` их не видит | **Принято, и шире.** Модулей, которые называют `LearningTask`, но полей отметки не пишут, оказалось **38**: 30 по grep и 12, убранных из описи по замечанию 8. Это все шесть названных и ещё 32 (`read_without_rung.txt`). Закрыто двумя строками. **T003**: тест `course_bank/tests/test_reader_without_course_task.py` проверяет, что задача без строки `CourseTask` читается как задача без ступени и без отметок, со значениями, равными нынешним умолчаниям колонок. **T052 и T053**: `Готово-когда` — 38 модулей зелёные **без правки** на переключённом порте (T052) и после удаления колонок (T053). Они гоняются поимённо в `check.sh` задачи, а не только в партии CI |
| 8 | Опись из 59 модулей шире нужной: 5 модулей упоминают `task_class` у `TopicContent` и `TaskClassKSA` | **Принято.** Разбор AST (`ltcls2.py`) по каждому вызову с полем отметки нашёл модель-получателя. 9 модулей пишут поля только у `TopicContent`, `TaskClassKSA` и `UserTaskClass`. Ещё 3 создают задачу через API с `task_class_id` в теле, а контракт API фича не меняет. Убрано **12** модулей, в описи осталось **47**. T067 −2, T068 −1, T069 −1, T070 −2, T071 −2, T072 −4. T071 (36 находок) и T072 (29) стали S. W −10 |
| 9 | `loc-budget.json` никому не принадлежит. T006 растит `urls`, `serializers`, `services`, `views.py`, цепочка `services_learning_tasks.py`; про потолок ни слова | **Принято.** Запас на `06a0bbdf4`: `urls.py` 0 строк, `views.py` 0, `models.py` 0, `admin.py` 0, `services_learning_tasks.py` 1, `services.py` 3, `services_lt_import.py` 4, `serializers.py` 23. Владелец `loc-budget.json` — **T006**: одна правка, `urls.py` 245 → 247 (два `include`) с записью в `_note`. Рост `services.py` (атомарный `create_course`) T006 покрывает выносом `_clone_course_structure_from_source` (125 строк) в `course_structure/clone.py`. `views.py` T006 больше не трогает. Остальные задачи по файлам бюджета обязаны уложиться в потолок без правки `loc-budget.json`, и это стоит в их `Готово-когда:`. T020 и T053 файлы бюджета уменьшают. Цепочка T043 → T042 → T055 по `services_learning_tasks.py` в сумме ≤ +1 строки: новая логика идёт в `learning_tasks/` (так требует `courses/AGENTS.md`). Второй владелец — **T065**: `--relax` опускает потолки до факта. Путь T006 → T065 есть (через T020) |
| 10 | T005 стартует на 118-й минуте, от неё 13 срезов. Считать её фазой К неточно | **Принято.** Выдача теперь по фазам: сначала все `[K]`, потом `[T]`, внутри фазы — ранг пути. T005 идёт 10–25, влита на 36-й. `[T]` все стартуют до 60-й минуты, в круге 2 последняя стартовала на 192-й. Конец точечного расписания тот же: 333 мин. В модели разница в пределах шума (744 против 756) |

## 2. Где я отступаю от `design.md` и почему

| Пункт design | Отступление | Довод |
|---|---|---|
| §3.2 п. 3: задач К 1–3, глубина 1 | 7 задач К. Глубина 2 у T003 (от T001, T002, T004) и у T006 (от T004) | Фича втрое больше модели design (78 AC). Одна К на всё — это L. Фаза К — 11% W при пороге 20%, все К влиты к 72-й минуте. У T003 и T006 стоит `Почему не одна:` |
| §2.1, §5: `(стек)` от `[K]` при срезах ≥ 2K — красное | **Отступления больше нет**, стек T006 снят | — |
| §5: пересечение `Файлы:` без пути — красное | Пустые `__init__.py` четырёх новых пакетов создают сразу несколько задач (`shared-empty`) | Одинаковое добавление пустого файла git сливает без конфликта, это проверено. Без этого правила T002 ждёт T001, и путь растёт на 24 мин. Содержимое в таких файлах запрещено, проба это проверяет |
| §3.2 п. 5: по сторонам режем, только если срезов < 2K | Не применяю. Сервер ∥ клиент остался только у T055 ∥ T056 | Карта владения разводит клиентские файлы, а C27 заменяет склейку |
| §3.2 п. 1: одна история — один `[V]` | US7 — 11 срезов кода и 7 срезов тестов **по владению файлами** | У перевода нет сценария. Деление по владению даёт ширину 18 на месте цепочки |
| §3.2 п. 9: тест среза — в файле среза | Перевод тестов вынесен в отдельные задачи | Перевод — механика без смены ожиданий. Сквозные модули (`test_integration.py`) не принадлежат ни одной зоне кода |
| §3 шаг 12: CI партиями 3–4 | Партия 4 при узком `check.sh`, до 8 при проверке групп при сдаче. Красная — пополам, виновник **откатывается** | Расчёт в §8.4 и §10 |
| §7 п. 1: W' = W(1 + 0.7p) | Модель с повторными отказами | При p = 0.55 модель даёт ~2.0 запуска на задачу, формула — 1.39. Проверить на baseline |

## 3. Истории и критерии приёмки

| Ист. | Что | AC | `[T]` (модуль → группа) |
|---|---|---|---|
| US1 | Учебный процесс | 1–7, 9 | T007 `learning_process/tests/test_acceptance_us1.py` → structure (правило T001); e2e `us1.spec.ts` |
| US2 | Экзамены курса | 8, 10–18 | T008 `learning_process/tests/test_acceptance_us2.py` → structure (правило T001); e2e `us2.spec.ts` |
| US3 | Выбранные банки, решатель | 19, 19а, 20, 21, 65 | T009 `course_bank/tests/test_acceptance_us3.py` → banks |
| US4 | Раскладка | 22–32 | T010 `course_bank/tests/test_acceptance_us4.py` → banks (AC-26 — `TransactionTestCase`) |
| US5 | Связи, ревизии, покрытие, видимость | 33, 36–42, 64, 70 | T011 `course_bank/tests/test_acceptance_us5.py` → banks |
| US6 | Гейт 3, недостача, квоты | 34, 35, 63, 76, 77 | T012 `course_pipeline/tests/test_acceptance_us6.py` → saga |
| US7 | Задача курса | 55–60, 66–68, 71–73 | T013 `course_bank/tests/test_acceptance_us7.py` → banks |
| US8 | Приём своих задач | 61, 62, 69, 74, 75, 78 | T014 `course_bank/tests/test_acceptance_us8.py` → banks; e2e `us8.spec.ts` |
| US9 | Режимы урока, старые курсы | 43–49 | T015 `lesson/tests/test_acceptance_us9.py` → lessons |
| US10 | Цель и экзамен | 50–53 | T016 `course_goal/tests/test_acceptance_us10.py` → structure (правило T001) |
| US11 | Копирование курса | 54 | T017 `course_structure/tests/test_acceptance_us11.py` → structure |

Группы проверены классификатором наставника (`scripts/test_registry.py` на `06a0bbdf4`).
`course_bank`, `course_pipeline`, `course_structure` и `lesson` попадают в свои группы и без
правила. Правило C28 нужно только модулям `learning_process`, `course_goal` и `exam_trainer`.
Поэтому «Влить после: T001» стоит только у 10 задач с такими модулями (T006, T007, T008, T016,
T025, T028, T029, T060, T062, T063), а у большинства из них T001 и так в `Зависит от:`.

Метки xfail: сервер — `@unittest.expectedFailure` (Django ≥ 4.1 считает неожиданный успех
ошибкой прогона), jest — `test.failing`, e2e — `test.fail()`. Срез снимает метку и прикладывает
`hold`: `expectedFailure` засчитывает любое исключение.

## 4. Карта швов (`contracts.md`)

Изменения против круга 2 выделены **жирным**.

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
| C9 | Порт `course_bank/placement.py`, методы R-23а; до T052 — на колонках | T002; переключает T052 | T043–T050, T075–T077, T054, T055 |
| C10 | Помощник `make_learning_task(**kw)` и чтение отметок через порт в тестах | T002 | T066–T072, `[T]` US7/US8 |
| C11 | `course_bank.reader.course_tasks(...)` → `CourseTaskItem`; **задача без `CourseTask` = без ступени и без отметок** | T003 | T031, T034–T038, T041, T042, T052, T061; **38 модулей «без отметок» (`read_without_rung.txt`)** |
| C12–C14 | Квоты, проверка отметок, места ступени | T003 | T032, T033, T035, T038, T041, T042, T055 |
| C15 | Интерфейс API банка (`exam_tasks/course_api.py`) и фейк под общим контрактным тестом; реализация — T018 | T004, T018 | T003, T006, T028, T029, T039, T040, T063 |
| C16–C17 | Коды, подписи, регистрация правил гейтов с заглушками | T005 | T027, T041, T064 и все, кто отдаёт коды |
| C18–C24 | Маршруты с 501 **(в `urls.py` пакетов, без `views.py`)**, поля сериализаторов, `create_course` одной транзакцией, перенос `_clone_…`, заглушки раскладки, слушатель, ветка подбора умений | T006 **(без стека, от T004)** | см. задачи |
| C25 | Клиент: типы, точки монтирования, `api.ts`, `MarksFields` | T005 | T023, T026, T030, T031, T034–T038, T056, T062 |
| C26 | Сторож `scripts/check_step6_writes.py`, режим `--tests` | T002 → T052 → T053 | все; критерий T066–T072 |
| C27 | JSON-примеры ответов ручек §6, копия для jest, сверка копии; **README и AGENTS новых пакетов** | T019 | серверные и клиентские срезы; **T065** |
| C28 | Правило группы тестов в `GROUP_RULES`: `learning_process\|course_goal\|step6` → structure, `exam_trainer` → banks | **T001** | 10 задач с модулями этих пакетов |

Правило поправки — только добавлением (ADR-0019).

## 5. Задачи

Вес: 10 мин × 1.6 (deep) × 1.5 (M). Ожидаемая длительность запуска: S обычный 7–10 мин,
M обычный 10–15, S deep 11–17, M deep 16–25. `BE/` = `services/django-api/courses/`,
`FE/` = `services/frontend/app/(lk)/my-courses/`, `CID/` = `FE/[courseId]/_components/`,
`JT/` = `services/frontend/__tests__/step6/`. `Тесты:` — тест-файлы задачи, и проба считает
пересечения и по ним. `Тест-группа:` выводит классификатор наставника. `Влить после:` — только
порядок вливания, и путь от него не растёт ни одним из трёх способов счёта.

Общая строка в `Готово-когда:` у каждой задачи, которая правит файл из `loc-budget.json`, кроме
T006 и T065: `check_loc_budget.py` зелёный **без правки** `loc-budget.json`.

### Фаза К

- [ ] **T019 [K] Примеры ответов §6; README и AGENTS новых пакетов**
  Контракт: владелец C27 · Файлы: `BE/step6_examples/`, `services/frontend/__tests__/fixtures/step6/`, `scripts/check_step6_examples.py`, `scripts/ci_quick_checks.py`, `BE/learning_process/{README,AGENTS}.md`, `BE/course_bank/{README,AGENTS}.md`
  Тесты: `scripts/tests/test_check_step6_examples_drift.py`
  Зависит от: — · Готово-когда: на каждую ручку §6 есть пример со всеми полями спеки; сверка краснеет на правке копии; README обоих пакетов проходят `check_module_readme.py` (все четыре раздела, «Устройство» — перечень модулей из `contracts.md`), AGENTS — `check_module_coverage.py`
  Риск: обычный · Размер: M · Тест-группа: saga (scripts)
- [ ] **T001 [K] Схема шага 6: модели, одна миграция, правило группы тестов**
  Контракт: C1, C3–C8, **C28** · Файлы: `BE/learning_process/{models,settings}.py`, `BE/course_bank/models.py`, `BE/migrations/0301_step6_schema.py`, `BE/course_goal/models.py`, `BE/exam_codifier/models.py` (CASCADE, согласовать с сессией ЕГЭ, §6.2), `BE/concurrency.py`, `BE/apps.py` (регистрация моделей пакетов), `BE/tests/_step6_factories.py`, `docs/engineering/module-{tiers,boundaries}.json`, `scripts/test_registry.py` (две альтернативы в `GROUP_RULES`); пустые `__init__.py` пакетов — `shared-empty`
  Тесты: `BE/learning_process/tests/{test_models,test_lock_order}.py`, `BE/course_bank/tests/test_models.py`, `scripts/tests/test_test_registry.py` (модуль `courses.learning_process.tests.test_x` → structure; ни один из 731 существующих модулей не сдвинулся, `core` = 2)
  Зависит от: — · Готово-когда: миграция накатывается и откатывается; ограничения `CourseTask` ловят обе ссылки, ни одной, повтор, `approved` без даты (тесты краснеют на откате); `settings_for` без строки отдаёт умолчания; `test_registry.py --check` зелёный
  Риск: deep · Размер: M · Тест-группа: banks, structure, saga (scripts)
- [ ] **T002 [K] Порт на колонках, помощник тестов, сторож**
  Контракт: C9, C10, C26 · Файлы: `BE/course_bank/placement.py`, `BE/tests/_learning_tasks_fixture.py`, `scripts/check_step6_writes.py`, `.pre-commit-config.yaml`; пустые `__init__.py` — `shared-empty`
  Тесты: `BE/course_bank/tests/test_placement_columns.py`, `scripts/tests/test_check_step6_writes.py`
  Зависит от: — **(в круге 2 — «влить после T001»)** · Готово-когда: каждый метод R-23а покрыт на колонках; правило версии Р-CT12; сторож ловит запись новых моделей вне пакета; `--tests` на базе печатает опись, совпадающую с `keep.txt` (47 модулей)
  Риск: deep · Размер: M · Тест-группа: banks, saga (scripts)
- [ ] **T004 [K] Интерфейс API банка для курса и фейк**
  Контракт: C15 · Файлы: `BE/exam_tasks/course_api.py` · Тесты: `BE/exam_tasks/tests/test_course_api_fake.py` (контрактный набор параметризован по бэкенду)
  Зависит от: — · Готово-когда: фейк проходит контрактный набор (пакетность одним вызовом; ФИПИ — только собственное происхождение; гонка `link_course` — своё исключение)
  Риск: обычный · Размер: S · Тест-группа: banks
- [ ] **T005 [K] Реестры и регистрация: коды, подписи, гейты, точки клиента**
  Контракт: C16, C17, C25 · Файлы: `config/{response-codes,api-problems}.json`, `config/locale/ru/problems.json`, `.claude/response-codes.json`, `BE/course_pipeline/gates/{registry,rules_lp_exam,rules_course_task,rules_goal_exam}.py`, `services/frontend/types/{courses,step6}.ts`, `FE/new/page.tsx`, `CID/overview/CourseBriefPanel.tsx`, `CID/tabs/TasksTab.tsx`, `CID/step6/{api.ts,MarksFields.tsx,mounts.tsx}`, `services/frontend/utils/problemLabels.ts`
  Тесты: `JT/MarksFields.test.tsx`, `BE/course_pipeline/tests/test_step6_rules_registered.py` (→ saga без правила)
  Зависит от: — **(в круге 2 — «влить после T019»)** · Готово-когда: `check_codes.py`, `check_problem_catalog.py` зелёные; правила-заглушки зарегистрированы и молчат; точки монтирования на флаге пустые
  Риск: обычный · Размер: M · Тест-группа: saga, frontend
- [ ] **T003 [K] Читатель задач курса, квоты, места, проверка отметок**
  Почему не одна: читатель читает таблицу T001, свои задачи берёт через порт T002, приём — через C15; вместе это L
  Контракт: C11–C14 · Файлы: `BE/course_bank/{reader,quotas,marks,places}.py`
  Тесты: `BE/course_bank/tests/{test_reader,test_marks_places_rungs}.py`, **`BE/course_bank/tests/test_reader_without_course_task.py`**
  Зависит от: T001, T002, T004 · Готово-когда: один запрос на вид источника (50 задач); DTO своей задачи до T052 — из порта; `trap_quota_applies` ложна; `rung_places` 11/15; **задача без строки `CourseTask` читается как задача без ступени и без отметок, значения равны нынешним умолчаниям колонок (тест краснеет, если читатель падает или выдумывает ступень)**
  Риск: deep · Размер: M · Тест-группа: banks
- [ ] **T006 [K] Точки подключения в общих файлах сервера**
  Почему не одна: правит существующие горячие файлы, а T001 — новые
  Контракт: C2, C18–C24 · Файлы: `BE/{urls,serializers,services}.py` **(без `views.py`)**, `BE/course_structure/{clone,clone_rungs}.py`, `BE/course_goal/{views_tasks,exam_ksa}.py`, `BE/learning_process/{urls,views,exams,services,copy}.py`, `BE/course_bank/{urls,views,layout,listeners,copy}.py`, **`docs/engineering/loc-budget.json`**
  Тесты: `BE/learning_process/tests/test_routes_stub.py`, `BE/tests/test_create_course_atomic_step6.py`, `BE/course_structure/tests/test_clone_moved.py`
  Зависит от: **T004** (без стека) · Влить после: T001 (правило группы для `learning_process/tests`) · Готово-когда: ручки §6 отдают 501 на флаге, прежнее без флага; `create_course` — одна транзакция (сбой в заглушке копии → курса нет); перенос `_clone_…` без изменения поведения; **заглушки не импортируют модели T001** (`git grep` по своим файлам); **`loc-budget.json`: `urls.py` 245 → 247 с записью в `_note`, остальные файлы в потолке** (`services.py` покрыт выносом 125 строк `_clone_…`)
  Риск: deep · Размер: M · Тест-группа: structure

### `[T]` — независимые приёмочные тесты (Sonnet, в окне фазы К)

11 задач T007–T017 (таблица §3). Риск у всех обычный. Размер M у T010, T013, T015, T017, у
остальных S. Код К не читают, пишут по `contracts.md`, C27 и спеке. В выдаче идут сразу за `[K]`:
в точечном расписании все стартуют до 60-й минуты. Каждая `[T]` вливается до срезов своей
истории. T007, T008, T016 вливаются после T001 (правило группы).

### Внешняя реализация C15

- [ ] **T018 [V] Реализация API банка для курса** (соседняя сессия ЕГЭ; в эксперименте — часть фичи)
  Файлы: `BE/exam_tasks/{services,course_api}.py`, `BE/exam_codifier/services.py` · Тесты: `BE/exam_tasks/tests/test_course_api.py`, `BE/exam_codifier/tests/test_course_api.py`
  Зависит от: T004 · Риск: обычный · Размер: M · Тест-группа: banks

### US9 Режимы урока

| Задача | Что | Файлы кода | Тесты | Зависит от | Риск/Размер | Группа |
|---|---|---|---|---|---|---|
| T020 [V] | Запись и ответы без режимов (R-43, сервер) | `BE/{serializers,services,views,admin}.py` (все в потолке, файлы уменьшаются), `course_pipeline/course_patch.py`, `domain_errors/__init__.py`, команды `seed_tariff_testbed`, `seed_ksa_tc_testbed`, `prepare_t1142_manual`, `prepare_t1144_purchase_manual` | новый `tests/test_course_detail_no_lesson_modes.py`; правит `tests/test_integration.py` (проверки `prefer_pbl`), `tests/test_brief_schema.py` | T006, T077, T066 | обычный M | core, lessons, structure |
| T021 [V] | Читатели режимов — константа (R-42) | `topic_content/lesson_modes.py`, `lesson/{serializers,streaming}.py`, `lesson/mode_a/services.py`, `track_manage/{read,serializers}.py`, `structure_gen/{skeleton,tasks}.py`, `task_classes/{rung_layout,rung_layout_db}.py`, `course_graph_editor/read.py` | новый `lesson/tests/test_lesson_modes_constant.py`; правит `tests/test_structure_gen.py`, `tests/test_lesson_mode_selection.py` | — | обычный M | lessons, structure |
| T022 [V] | Инвариант «линия А без чтения» по флагу (R-44, R-48) | `graph_invariants/structure_gate.py`, `task_classes/services.py` | новый `graph_invariants/tests/test_structure_gate_flag.py`; правит `test_adr087_gate.py` | — | обычный S | saga |
| T023 [V] | Клиент без режимов | `CID/structure/{TaskClassModal,TopicTreePanel}.tsx`, `FE/new/page.tsx`, `CID/overview/{CourseBriefPanel.tsx,briefFieldLabels.ts,briefConsistency.ts}`, `config/courseCreation.ts`, `utils/{auth,tracks}.ts`, `types/courses.ts`, страница урока и `lessonStopPlan.ts` | `JT/no_lesson_modes.test.tsx` | T005 | обычный M | frontend |
| T024 [V] | Команда `unpublish_legacy_courses` (R-47а) | `management/commands/unpublish_legacy_courses.py` | `management/commands/tests/test_unpublish_legacy_courses.py` | — | deep M | platform |
| T074 [V] | Тесты: убрать режимы из подготовки данных | — | 12 модулей (список круга 2 без изменений) | T020, T021, T022 | обычный S | 8 групп |

### US1, US2, US3–US6, US8, US10, US11 — срезы поведения

Поля, общие для всех: `Срез: USn / <сценарий>`, `Приёмка:` — AC своей `[T]`. Серверный срез
сверяет ответ ручки с примером C27, клиентский мокает ответ этим же примером. Готово-когда: тесты
среза зелёные и краснеют на откате (`hold`), xfail своих AC сняты. **README и AGENTS пакетов срез
не правит**: своё «как устроено» он пишет в доклад для T065.

| Задача | Что | Файлы кода | Тесты | Зависит от | `[T]` | Риск/Размер | Группа |
|---|---|---|---|---|---|---|---|
| T025 [V] | Учебный процесс, сервер (R-1…R-5) | `learning_process/{services,validation,serializers}.py` | `learning_process/tests/{test_services,test_validation}.py` | T006, **T001** | T007 | deep M | structure |
| T026 [V] | Блок «Учебный процесс» (R-6) | `CID/step6/LearningProcessBlock.tsx` | `JT/LearningProcessBlock.test.tsx` | T005, T019 | T007 | обычный M | frontend |
| T027 [V] | Гейт отправки «пробники ⇒ экзамен» (R-7) | `course_pipeline/{gate_journal,gating}.py`, `publication/views.py`, `gates/rules_lp_exam.py`, `CID/tabs/PublishTab.tsx` | `course_pipeline/tests/test_lp_exam_gate.py` | T005, T006, T046, **T001** | T007 | deep M | saga |
| T028 [V] | Вход в «Тренажёр ЕГЭ» (Е-15) | `exam_trainer/services.py`, страница курса ученика, `ExamTrainerEntry.tsx` | `exam_trainer/tests/test_course_entry.py` | T001, T018 | T007 | обычный M | banks |
| T029 [V] | Экзамены курса, сервер (R-10…R-14) | `learning_process/{exams,views_exams,catalog}.py` | `learning_process/tests/{test_exams,test_exam_catalog}.py` | T006, **T001** | T008 | deep M | structure |
| T030 [V] | Экзамены курса, клиент | `CID/step6/{CourseExamsBlock.tsx,briefDraftMerge.ts,ExamUnlinkDialog.tsx}` | `JT/{CourseExamsBlock.test.tsx,briefDraftMerge.test.ts}` | T005, T019 | T008 | обычный M | frontend |
| T031 [V] | Выбранные банки и решатель (R-17…R-21) | `course_bank/{banks,views_banks}.py`, `CID/step6/CourseBanksBlock.tsx` | `course_bank/tests/test_banks.py`, `JT/CourseBanksBlock.test.tsx` | T003, T006, T019 | T009 | обычный M | banks, frontend |
| T032 [S] | Раскладка: расчёт кандидатов | `course_bank/layout_calc.py` | `course_bank/tests/test_layout_calc.py` | T003 | T010 | обычный M | banks |
| T033 [S] | Раскладка: запись под замком, Celery, журнал | `course_bank/{layout_run,layout,listeners,tasks}.py` | `course_bank/tests/test_layout_run.py` | T006, T042; T032 (стек) | T010 | deep M | banks |
| T034 [V] | «Подобрать ещё» и блок «Задачи из банка» | `course_bank/{candidates,views_layout}.py`, `CID/step6/CourseBankBlock.tsx` | `course_bank/tests/test_candidates.py`, `JT/CourseBankBlock.test.tsx` | T032, T006, T005, T019 | T010 | обычный M | banks, frontend |
| T035 [V] | Ручное добавление и правка связи | `course_bank/{links,views_links}.py`, `CID/step6/LinkDialogs.tsx` | `course_bank/tests/test_links.py`, `JT/LinkDialogs.test.tsx` | T003, T006, T005, T019 | T011 | обычный M | banks, frontend |
| T036 [V] | Приём и отклонение размещения связей | `course_bank/{links_bulk,views_bulk}.py`, `CID/step6/LinkBulkBar.tsx` | `course_bank/tests/test_links_bulk.py`, `JT/LinkBulkBar.test.tsx` | то же | T011 | обычный M | banks, frontend |
| T037 [V] | Новые ревизии, «изменились умения» | `course_bank/{revisions,views_revisions}.py`, `CID/step6/RevisionsModal.tsx` | `course_bank/tests/test_revisions.py`, `JT/RevisionsModal.test.tsx` | то же | T011 | deep M | banks, frontend |
| T038 [V] | Отчёт покрытия D-033 | `course_bank/{coverage,views_coverage}.py`, `CID/step6/CoverageReport.tsx` | `course_bank/tests/test_coverage.py`, `JT/CoverageReport.test.tsx` | то же | T011 | обычный M | banks, frontend |
| T039 [V] | Видимость задач ФИПИ (Е-17) | `exam_tasks/services.py` | `exam_tasks/tests/test_learner_origin_fipi.py` | T018 | T011 | обычный S | banks |
| T040 [V] | Фикстура стенда Е-10 | `exam_tasks/management/commands/seed_step6_exam_fixture.py` | `exam_tasks/tests/test_seed_step6_fixture.py` | T018 | — | обычный S | banks |
| T041 [V] | Гейт 3 по задачам курса, квоты по ступени | `gates/{rules_stages,rules_course_task}.py`, `course_pipeline/gating.py`, `meaning`/`title` двух кодов | `course_pipeline/tests/test_gate3_course_tasks.py` | T003, T005, T046, T027 | T012 | обычный M | saga |
| T042 [V] | Один счёт недостачи; генерация после раскладки | `learning_tasks/{deficit,top_up,generation_marks}.py`, `services_learning_tasks.py` (**в потолке: правка счёта сокращает, новое — в `learning_tasks/`**) | `learning_tasks/tests/test_deficit_single_count.py` | T003, T006, T045, T043 | T012 | deep M | banks |
| T055 [V] | Приём своей задачи и размещения, сервер | `services_learning_tasks.py` (**в потолке**), `course_bank/placement.py` | `learning_tasks/tests/test_accept_own_task.py` | T052, T042 | T014, T012 | deep M | banks |
| T056 [V] | Экран «Задачи» для своих задач | `CID/tasks/{EditLearningTaskModal,BulkBar,InboxLT,CreateLearningTaskModal,TreeGroupedPool}.tsx` | `JT/tasks_own_marks.test.tsx` | T005, T019 | T014 | обычный M | frontend |
| T057 [V] | Копия графа (R-12в пп. 3, 8) | `course_structure/clone.py` | `course_structure/tests/test_clone_graph_step6.py` | T006 | T017 | deep M | structure |
| T058 [V] | Копия ступеней по картам | `course_structure/clone_rungs.py` | `course_structure/tests/test_clone_rungs.py` | T006 | T017 | deep M | structure |
| T059 [V] | Копия наследует нарушения источника | `course_structure/guard.py` | `course_structure/tests/test_guard_inherits.py` | — | T017 | deep S | structure |
| T060 [V] | Копия учебного процесса, экзаменов, ссылок | `learning_process/copy.py`, `course_goal/services.py` | `learning_process/tests/test_copy.py` | T006, T029, **T001** | T017 | обычный M | structure |
| T061 [V] | Копия банков и связей | `course_bank/copy.py` | `course_bank/tests/test_copy.py` | T006, T003, T031, T058 | T017 | deep M | banks |
| T062 [V] | Позиции КИМ и образцы у итоговой задачи | `course_goal/{services_tasks,serializers_positions}.py`, `CID/overview/{FinalTasksBlock.tsx,finalTasks.ts}` | `course_goal/tests/test_final_task_positions.py`, `JT/FinalTasksPositions.test.tsx` | T006, T005, T019, **T001** | T016 | обычный M | structure, frontend |
| T063 [V] | «Подобрать умения» по позиции КИМ | `course_goal/exam_ksa.py` | `course_goal/tests/test_exam_ksa.py` | T006, T018, **T001** | T016 | обычный S | structure |
| T064 [V] | Две автопроверки цели | `gates/rules_goal_exam.py` | `course_pipeline/tests/test_goal_exam_rules.py` | T005, **T001** | T016 | обычный S | saga |

### US7 Задача курса

**Перевод кода на порт** (11 срезов, без изменений против круга 2, кроме строки о потолке).
Каждый зависит от T002 и от того, кто раньше держал его файл. Тесты зоны срез не правит.
`Приёмка:` AC-68 по зоне. Готово-когда: grep по файлам среза не находит ORM-обращений к полям
отметок `LearningTask`; модули тестов зоны зелёные без правки; **T043 и T044: файлы бюджета в
потолке** (`services_learning_tasks.py` +1, `services_lt_import.py` +4 строки запаса, импорт
порта заменяет прямой импорт полей).

| Задача | Файлы | Строк по полям (grep) | Доп. зависимость | Размер |
|---|---|---|---|---|
| T043 | `services_learning_tasks.py` | 64 | — | M |
| T044 | `_lt_import.py`, `lt_import.py`, `services_lt_import.py`, `documents/{models,services}.py` | 27 | — | S |
| T045 | `learning_tasks/{answer_forms,deficit,generation_marks,selection,solution_check,top_up}.py`, `learning_task_solver/{author,button,generation,solve_job}.py` | 37 | — | M |
| T046 | `course_pipeline/{auto_pipeline,gating,views}.py`, `gates/{facts,rules_stages,rules_structure}.py`, `saga/{events,reopen}.py`, `publication/views.py` | 49 | — | M |
| T047 | `task_classes/{rung_switch,delete_preview}.py` | 24 | — | S (deep) |
| T048 | `task_classes/{predicates,rung_layout_db}.py` | 47 | T021 | M |
| T075 | `task_classes/{rung_rule,services,topic_merge}.py` | 38 | T022 | M |
| T049 | `course_structure/{editor,generation,rung_layout}.py`, `structure_gen/{skeleton,tasks}.py` | 32 | T021 | M |
| T076 | `course_graph_editor/{delete_preview,read,write}.py` | 24 | T021 | S |
| T050 | `topic_content/{generation/context,generation/services,lesson_modes,passthrough,services}.py` | 56 | T021 | M |
| T077 | `dialogue/{item_materialization,lesson_setup,orchestrator_b}.py`, `track_manage/{models,planner}.py`, 7 команд и сидов | ~20 + команды | — | M |

**Перевод тестов на помощник порта** (7 срезов, Sonnet). Каждый зависит от T002 (C10). Код не
правит. Готово-когда: `check_step6_writes.py --tests` по файлам задачи пуст; проверки `assert*` в
диффе не менялись (`assert-unchanged`); модули зелёные на колонках. Опись — **47 модулей**
(`keep.txt`): из 59 модулей круга 2 убраны 12, где поля отметки относятся не к `LearningTask`
(`drop.txt`, §1 п. 8).

| Задача | Тест-файлы (`BE/…`) | Находок | Доп. зависимость | Размер | Группа |
|---|---|---|---|---|---|
| T066 | `tests/test_integration.py` (только `LearningTask`-фикстуры и чтения отметок) | 57 | — | M | core (только классы LT модуля) |
| T067 | `tests/test_learning_tasks_{deficit,endpoints,generation_reservation,generator_kind,import,target_degraded}.py`, `tests/test_lt_import_automapping.py`, `tests/_phase3_fixtures.py`, `tests/_target_ksa_fixtures.py` | 43 | — | M | banks, documents, graph, structure |
| T068 | `tests/test_task_class_lesson_models.py`, `tests/test_phase3_fanout.py`, `tests/test_lesson_mode_selection.py` | 44 | T021 | M | lessons, structure |
| T069 | `learning_tasks/tests/{_solution_case,test_answer_form_fields,test_generation_marks,test_initiator_mismatch,test_phase3_failure_outcome}.py`, `learning_task_solver/tests/{_case,test_author_write,test_followup_unit,test_generation}.py` | 61 | — | M | banks, billing |
| T070 | `course_pipeline/tests/{test_auto_pipeline,test_gate2_content_reading,test_gate_views,test_genre_approval_a2,test_phase3_no_target_ksa,test_reopen_views,test_transfer_trap_rules}.py`, `publication/tests/test_moderation_views.py`, `methodology_params/tests/test_readers.py` | 43 | — | M | saga |
| T071 | `task_classes/tests/{_rung_layout_fixtures,_rung_switch_fixtures,test_learning_tasks_target_request,test_rung_layout_button,test_rung_regen_cascade,test_rung_regen_db,test_rung_switch_import,test_rung_layout_db}.py`, `course_graph_editor/tests/{test_topic_merge_delete,_topic_merge_fixtures}.py`, `structure_gen/tests/test_rung_layout_phase1.py` | 36 | T021 | **S** | banks, content, structure |
| T072 | `dialogue/tests/{_mode_b_e2e_fixture,_orchestrator_b_fixture,test_e2e_mode_b,test_lesson_setup}.py`, `lesson/tests/test_lesson_lifecycle.py`, `management/commands/tests/test_archive_non_whole_task_lt_command.py` | 29 | — | **S** | banks, lessons, saga |

Убраны из описи (поля у `TopicContent`/`TaskClassKSA`/`UserTaskClass`): `course_pipeline/tests/
{test_gate_rules_moved_to_server,test_lifecycle_views}.py`, `course_structure/tests/test_deletion.py`,
`dialogue/tests/test_orchestrator_b.py`, `gap_ingestion/tests/test_gap_ingestion.py`,
`lesson/tests/{test_lesson_runtime_canon,test_topic_modes}.py`, `structure_gen/tests/test_augment_upsert.py`,
`tests/test_generation_context.py`. Задача создаётся через API с `task_class_id` в теле:
`learning_tasks/tests/test_solution_rules.py`, `tests/test_learning_task_description_length.py`,
`tests/test_learning_tasks_old_steps_closed.py`. Все 12 входят в 38 модулей «без отметок»,
которые T052 и T053 гоняют без правки.

**Последовательные задачи US7:**

- [ ] **T051 [S] Перенос своих задач в задачи курса (R-22а), проверочная команда.** Почему не срез: миграция данных. Файлы: `BE/migrations/0302_course_task_from_learning_task.py`, `BE/management/commands/check_learning_task_course_alignment.py`. Тесты: `BE/tests/test_migration_0302_course_task_transfer.py`. Зависит от: T001. Риск: deep · M · banks.
- [ ] **T052 [S] Переключение порта и читателя на `CourseTask`; `register` пишет; сторож полей.** Почему не срез: точка, где исчезает вторая правда о ступени. Файлы: `BE/course_bank/{placement,reader}.py`, `scripts/check_step6_writes.py`. Тесты: `BE/course_bank/tests/test_placement_switch.py`. Зависит от: T043–T050, T075–T077, T066–T072, T051, T003. Готово-когда: все группы django зелёные; T052 не правит ни одного тест-файла, кроме своего; сторож `--tests` по всему дереву пуст; новые методы `approve_placement`, `placement_of`; **38 модулей из `read_without_rung.txt` (в том числе `test_child_order`, `test_child_order_conflicts`, `test_hidden_ksa_outcomes`, `test_gate_approve_clears_refusal`, `test_gate_approve_events`, `test_learning_tasks_filters`) зелёные без правки, поимённо в `check.sh` задачи: задача без `CourseTask` читается как без ступени (C11).** Риск: deep · M · banks + полный прогон партии.
- [ ] **T053 [S] Удаление колонок `learning_task` и режимов курса и брифа.** Файлы: `BE/models.py` (уменьшается), `BE/migrations/0303_drop_lt_marks_and_lesson_modes.py`, `scripts/check_step6_writes.py`. Тесты: `BE/tests/test_migration_0303_drop_lt_marks.py`. Зависит от: T052, T020–T024, T074. Готово-когда: **те же 38 модулей зелёные без правки после удаления колонок**. Риск: deep · S · platform + полный прогон.
- [ ] **T054 [V] Удаление ступени и темы при задачах курса.** Файлы: `BE/course_bank/detach.py`, `BE/course_structure/{deletion,rung_layout}.py`, `BE/task_classes/rung_switch.py`. Тесты: `BE/course_bank/tests/test_detach.py`. Зависит от: T003, T047, T049. Риск: deep · S · banks.

### Хвост

- [ ] **T065 [H] Реестры документов, журнал, находки «хвост», README и AGENTS пакетов, потолок строк.** Файлы: `docs/INDEX.md`, `CHANGELOG.md`, `docs/journal/`, `BE/learning_process/{README,AGENTS}.md`, `BE/course_bank/{README,AGENTS}.md` (устройство по докладам срезов), `docs/engineering/loc-budget.json` (`check_loc_budget.py --relax`: потолки уменьшившихся файлов опускаются до факта), записи в Ж, Пар §3.2, ADR-121. Зависит от: все `[V]`/`[S]`. Обычный · S.

## 6. Карта владения

### 6.1. Горячие файлы внутри плана (порядок = путь в графе)

| Файл | Владельцы по порядку |
|---|---|
| `courses/{services,serializers}.py` | T006 → T020 |
| `courses/views.py`, `courses/admin.py` | только T020 (уменьшает) |
| `courses/models.py` | только T053 (уменьшает) |
| **`docs/engineering/loc-budget.json`** | **T006 (`urls.py` +2) → T065 (`--relax`)** |
| `services_learning_tasks.py` | T043 → T042 → T055 (вместе ≤ +1 строки) |
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
| `exam_tasks/services.py` | T018 → T039 |
| `exam_tasks/course_api.py` | T004 → T018 |
| `course_bank/placement.py` | T002 → T052 → T055 |
| `course_bank/reader.py` | T003 → T052 |
| `scripts/check_step6_writes.py` | T002 → T052 → T053 |
| **`scripts/test_registry.py`**, `scripts/tests/test_test_registry.py` | **только T001** |
| **`BE/apps.py`** | **только T001** |
| **README и AGENTS `learning_process`, `course_bank`** | **T019 → T065** |
| `FE/new/page.tsx`, `CourseBriefPanel.tsx`, `types/courses.ts` | T005 → T023 |
| `config/response-codes.json`, `locale/ru/problems.json` | T005 → T041 |
| `tests/test_integration.py` | T066 → T020 |
| `tests/test_lesson_mode_selection.py` | T021 → T068 |
| **пустые `__init__.py` `course_bank`, `course_bank/tests`, `learning_process`, `learning_process/tests`** | **`shared-empty`: создают T001, T002, T006 и `[T]`; содержимое запрещено** |

Генерируемые (`shared` в `pair-rules.txt`): `docs/engineering/module-map.md` и схема API.

Что карта не видит: смысловое пересечение (швы C11–C14 в К, ревьюеру называются ветки в
полёте с тем же `Контракт:`); поломку тестов зоны от перевода кода (срез тест не правит,
докладывает, координатор ставит ребро «тест-задача → срез»).

### 6.2. Пересечение с планами в полёте (шаг 8, сессия ЕГЭ)

Без изменений против круга 2: 17 задач задевают зону шага 8, 6 — зону сессии ЕГЭ. Закрыто
межплановыми рёбрами в `plan-edges.md` и `task_pairs.py plan --with`. Реестры между планами —
`serial`. Слоты общие: если шаг 8 идёт одновременно, этой фиче достаётся K = 3.
`loc-budget.json` — тоже `serial` между планами: шаг 8 растит `services.py` и `views.py` в той
же исторической зоне.

## 7. Расписание по слотам (точечное, HLFET с фазами, без доработок)

K = 4, R = 3, ревью 8, вливание поездом 1.5 мин, выдача скриптом, CI не на пути. Порядок выдачи:
`[K]`, затем `[T]`, затем ранг пути. Окончание — 333 мин (K = 3 — 434, K = 5 — 272). Полный
вывод: `decomp/f1B3/sched4.txt`, `sched5.txt`.

```
T001 [K] слот 1:   0– 24, влита  34     T046 [V] слот 1:  63– 78, влита  89
T002 [K] слот 2:   0– 24, влита  35     T045 [V] слот 2:  63– 78, влита  88
T004 [K] слот 3:   0– 10, влита  20     T077 [V] слот 3:  64– 79, влита  90
T019 [K] слот 4:   0– 15, влита  24     T066 [V] слот 4:  71– 86, влита  96
T005 [K] слот 3:  10– 25, влита  36     ... перевод кода и тестов 78–128 ...
T006 [K] слот 1:  24– 48, влита  58     T042 [V] слот 1: 133–157, влита 166
T003 [K] слот 2:  39– 63, влита  72     T052 [S] слот 2: 138–162, влита 172
[T] T007–T017:    15– 60                T033 [S] слот 1: 220–244, влита 254
T021, T022, T051, T047, T043: 25– 71    T053 [S] слот 4: 240–256, влита 266
                                        T065 [H] слот 1: 314–324, влита 333
```

Фаза К занимает 0–72 мин: все семь `[K]` и все `[T]` выданы к 60-й минуте, свободные слоты
занимают T021, T022, T051, T047 и первые срезы перевода. Сходка перед T052 — на 138-й минуте.
Все 4 слота заняты от 0 до ~300.

## 8. Тесты, документы, ревью, вливания

### 8.1. Тесты

- `[T]` по истории пишет до кода другой агент (Sonnet). Метки xfail — по раннеру проекта.
  Срез снимает метки своих AC и прикладывает `hold`.
- Тест среза лежит в файле среза. Перевод старых тестов на порт — T066–T072 (47 модулей).
  Чистка режимов — T074. **38 модулей «без отметок»** не правит никто: их держат тест T003 и
  `Готово-когда` T052 и T053.
- `assert-unchanged` для задач перевода: в диффе нет изменённых строк `self.assert*`,
  `assertNumQueries`, `expect(`.
- **`check.sh` при сдаче — два уровня.** Исполнитель гоняет модули своих `Тесты:` и зоны, как в
  круге 2. **Новое:** скрипт сдачи после освобождения слота гоняет в рабочем дереве задачи
  **все группы** её `Тест-группа:` параллельно с ревью. Красная группа отправляет задачу в
  `доработка` без ревью. Исключение — `core` (`test_integration.py`, ~25 мин): T043, T066, T020
  гоняют только классы LT, полный `core` — в партии CI. Это и снижает r, долю вливаний, которые
  краснят CI (§8.4).

### 8.2. Документы

README и AGENTS новых пакетов создаёт T019 со всеми разделами, которые требуют
`check_module_readme.py` и `check_module_coverage.py`. Срезы их не правят. Устройство по
докладам срезов дописывает T065. Общие реестры (INDEX, CHANGELOG, журнал), правки источников по
§8 спеки и `loc-budget.json --relax` — тоже T065.

### 8.3. Ревью

Пул R = K − 1, одна линза: логика, `Контракт:`, `Готово-когда:`/AC. Механику (поезд, `hold`,
`assert-unchanged`, сверку с C27, группы при сдаче, `check_loc_budget.py`) делает скрипт. Для
`[K]` линза «хватит ли срезам», для `[T]` — «каждый AC покрыт, тест бьёт обе стороны», для
перевода тестов — «подготовка та же». «Можно сливать, хвост» уводит мелочи в T065. Второй круг —
только по находкам, третий — человек.

### 8.4. Вливания и CI

**Поезд вливаний и выдача скриптом** — как в круге 2.

**CI: откат виновника, а не исправление вперёд.** Партия — всё накопленное с прошлой проверки:
**до 4** при узком `check.sh`, **до 8** при проверке групп при сдаче. Красная партия делится
пополам, на одного виновника уходит ⌈log₂ n⌉ проверок. Виновника поезд откатывает с ветки плана
(`git revert`, 1–2 мин) вместе с его **потомками**, влитыми после него. Потомки ждут повторного
вливания виновника и вливаются заново без доработки: их код не менялся. Невиновные члены партии
зелёные, деление их проверило. Виновник уходит в `доработка` с рангом своей задачи. Так
устроены [GitLab merge trains](https://docs.gitlab.com/ci/pipelines/merge_trains/): упавший
запрос выбывает из поезда, а поезд пересобирается без него. Исправление вперёд оставляет ветку
плана красной до исправления, и все следующие партии ничего не проверяют. В модели (K = 4,
p = 0.43, r = 0.15, партия 4) откат даёт 1178 мин, исправление вперёд — 1521.

**r — главная величина фичи.** При r = 0.15 CI делает ~51 проверку по 15–28 мин. Это ~1100 мин
последовательной работы, больше всей работы исполнителей при K = 4. Проверка групп при сдаче
переносит эту проверку из последовательного CI в параллельные рабочие деревья. Остаточное r —
поломка чужой группы и взаимодействие веток одной партии. Его никто не мерил, поэтому считаю
0.05 и 0.10. Ограничение: параллельные прогоны групп в 4 деревьях требуют отдельной тестовой
БД на дерево (`TEST_NAME` по имени дерева).

Рычаг вне базы — отпечаток групп CI у наставника: любая правка `services/` сбрасывает все группы
django. Проверка 6–10 мин по пакету даёт −12% (754 → 660 при K = 4, p = 0.55).

## 9. Конфликты и простой — где они будут

1. **CI.** Главный простой. При r = 0.15 исполнители заняты в среднем 1.5–2.4 из 4 на всей
   фиче, и K ничего не меняет. Лечится проверкой групп при сдаче, затем отпечатком по пакету.
2. **Откаты.** При r = 0.15 ~14 откатов на фичу (модель), каждый тянет за собой влитых потомков.
   Самые дорогие — у T001, T002, T003, T006: у них 10–19 прямых потребителей. Смягчение — у `[K]`
   полный прогон групп при сдаче обязателен, без исключения для `core`.
3. **Сходка перед T052**: 18 срезов перевода, T051 и T003. При p = 0.55 в среднем 10 из 18
   уходят на доработку. Срезы перевода стоят первыми по рангу. Для них p, скорее всего, ниже
   (механика, `assert-unchanged`), но модель этого не учитывает: оценка консервативна.
4. **T006 — 18 потребителей, deep M, ~19 файлов.** Без стека её доработка задерживает старт
   потребителей, но не ломает начатую работу.
5. **Потолок строк.** `urls.py`, `views.py`, `models.py`, `admin.py` без запаса. Срез, которому
   не хватило строки, выносит код в пакет и потолок не поднимает. Если вынести нельзя, он
   докладывает, и правку `loc-budget.json` делает T065 (или человек), а не срез.
6. **Шаг 8** в `topic_content/*`, `task_classes/*`, `course_structure/*`, а также общий
   `loc-budget.json` — межплановые рёбра (§6.2).
7. **`services_learning_tasks.py`**: три владельца подряд, вместе +1 строка.
8. **Миграции**: три на одном пути (T001 → T051 → T052 → T053). Номер даёт поезд, тест миграции
   переименовывается вместе с ней.
9. **Стенд e2e** — один `cc-*` :8092, приёмка историй идёт последовательно, ~30 мин хвоста.

## 10. Оценка времени

Модель `sim3.py`: ревью 5–12 мин, исполнитель — вес × U(0.7, 1.4), доработка 0.7 × вес,
исправление виновника 0.5 × вес, у `[T]`/`[H]` p = 0.15, у остальных p. Откат виновника,
выдача скриптом 0.3 мин, поезд 1–2 мин, приёмка 30 мин. 150 прогонов на клетку, в скобках
90-й перцентиль. Минуты до зелёного CI на всём плюс приёмка. Полный вывод — `run3.out`.

**K = 4, R = 3:**

| Режим | p = 0.25 | p = 0.43 | **p = 0.55** | p = 0.72 |
|---|---|---|---|---|
| Как есть: узкий `check.sh`, r = 0.15, CI 15–28, партия 4 | 1174 (1430) | 1178 (1422) | **1194 (1470)** | 1210 (1439) |
| то же, партия 8 | 1205 | 1226 | 1250 | 1265 |
| то же, r = 0.20 | 1455 | 1420 | 1464 | 1491 |
| то же, исправление вперёд вместо отката | — | 1521 | 1557 | 1584 |
| Группы при сдаче, r = 0.10, CI 15–28, партия 8 | — | 898 | 951 | 996 |
| **Группы при сдаче, r = 0.05, CI 15–28, партия 8** | 634 (793) | 690 (818) | **754 (884)** | 833 (919) |
| Узкий, r = 0.15, **CI 6–10**, партия 4 | 562 | 636 | 714 | 821 |
| **Группы при сдаче, r = 0.05, CI 6–10, партия 8** | 505 (541) | 593 (640) | **660 (707)** | 776 (826) |
| Нижняя граница: CI не на пути | 470 | 554 | 618 | 743 |
| Точечно, без доработок и CI | 333 | | | |

**K = 3 и K = 5, p = 0.55:**

| Режим | K = 3, R = 2 | K = 4, R = 3 | K = 5, R = 4 |
|---|---|---|---|
| Как есть (r = 0.15, CI 15–28, партия 4) | 1194 | 1194 | 1171 |
| Группы при сдаче, r = 0.05, CI 15–28 | 918 | 754 | 665 |
| Группы при сдаче, r = 0.05, CI 6–10 | 868 | 660 | **562** |
| CI не на пути | 801 | 618 | 518 |
| p = 0.72, группы при сдаче, CI 6–10 | 1060 | 776 | 657 |

Выводы:
- **Как есть пятый слот не нужен**, и четвёртый почти тоже: 1194 при K = 3, 4 и 5. Фича
  CI-связана, исполнители заняты в среднем 2.0 из 4.
- **Первый шаг — проверка групп при сдаче** (−37% при r = 0.05, −20% при r = 0.10). Это изменение
  базы (скрипт сдачи), а не проекта.
- **K = 5** окупается только после этого шага: −12% при нынешнем CI, −15% при быстром. P = 11.3 ≥
  10, так что пятый слот укладывается и в норму пробы.
- **K = 3** (слоты делятся с шагом 8): при группах при сдаче +22% к K = 4 (918 против 754). При
  нынешнем CI разницы нет: обе фичи упираются в один CI, и делить его выгоднее, чем слоты.
- Занятость исполнителей за фичу: 1.5–2.4 из 4 как есть, 2.6–3.2 с группами при сдаче, 3.3–3.4
  при быстром CI.

Деньги по медианам наблюдений (implementer ~$0.94, deep ~$4.9, reviewer ~$1.5; 21 deep и 55
обычных задач): при p = 0.55 ~2.0 запуска на задачу — 21 × 2.0 × $4.9 ≈ $205, 55 × 2.0 × $0.94
≈ $105, ~151 ревью × $1.5 ≈ $225, итого **~$530**. При p = 0.72 (2.5 запуска) — ~$660, при p =
0.43 — ~$455. Откаты добавляют ~14 запусков исправления (0.5 веса), это ≈ +$25, они уже в
счётчике модели.

## 11. Что меняется в базе (дополнительно к §8 design и к кругу 2)

| Файл | Изменение |
|---|---|
| `scripts/task_pairs.py plan` | путь тремя способами (старт, сложение, два времени); P и пороги — от худшего; `shared-empty` в `pair-rules.txt` (пустой файл, содержимое — красное); предупреждение «задача растит файл из бюджета строк проекта и не владеет файлом бюджета» (no-op, если у проекта нет такого файла); выдача по фазам `[K]` → `[T]` → ранг |
| `scripts/task_pairs.py train` | красная партия — деление пополам, **откат виновника и его влитых потомков**, повторное вливание потомков без доработки; партия до 4 по умолчанию, до 8, если включены группы при сдаче |
| скрипт сдачи (`skills/day`, `task_pairs.py submit`) | после освобождения слота — прогон групп `Тест-группа:` в рабочем дереве параллельно ревью; красная группа — `доработка` без ревью; исключения по длительности (`core`) — в конфиге проекта |
| `agents/architect.md` | README и AGENTS новых пакетов — в одну `[K]`/`[T]`-задачу вне пути и в `[H]`, срезам запрещены; опись перевода тестов — по AST получателя поля, а не grep; модули, которые создают сущность без перенесённых полей, — в `Готово-когда` точки переключения |
| `scripts/tests/` | случаи: ребро «влить после» удлиняет путь в режиме сложения; `shared-empty` с содержимым — красное; откат виновника снимает потомков; рост файла бюджета без владельца — предупреждение |

Все пробы — отчёт, не гейт, выпуск патчевый.

## 12. Что проверить по baseline

- **r у baseline**: доля вливаний, после которых CI краснел, и что делали с виновником (откат
  или исправление вперёд). От этого по модели зависит больше, чем от K и от p.
- Сколько проверок CI и сколько минут простоя на CI было у baseline.
- p на механических задачах (перевод) против задач поведения. Если у механических p < 0.2,
  оценка завышена на ~50–80 мин.
- Задевали ли baseline-задачи `loc-budget.json` и README пакетов одновременно и сколько это
  стоило.
- Сколько тест-модулей baseline правил при переводе на новую модель: 47 (моя опись), 59 (круг 2)
  или иначе.
