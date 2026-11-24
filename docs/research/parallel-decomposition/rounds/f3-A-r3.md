# Фича 3, команда A, круг 3: разложение и план `task_solutions` + раздел «Решение»

Дата 2026-11-24. Процесс — `design.md` (К → `[T]` в окне К → веер `[V]` → `[H]` → приёмка).
Позиция A прежняя: ширину даёт разложение по контрактам. Зависимость «по коду» заменяется
зависимостью «по контракту» там, где контракт держит поведение. На пути записи (замки,
единственный писатель) ребро остаётся настоящим. Круг 3 добавляет к этому второе условие:
**любое промежуточное состояние ветки фичи после вливания должно быть согласованным** (запись и
чтение одной сущности идут в одно хранилище). Это условие было нарушено в круге 2 (T011).

Источники: `feature-3-description.md`, `inputs/feature-3/*` (план Н-1 §2–§5, Н-1б, контракт v4…v6);
код наставника только на `4ba293f13`: `.pre-commit-config.yaml` (хуки `module-map`,
`api-doc-coverage`, `docs-index`, `stack-facts`, `process-map-doc`), `.github/workflows/cicd.yml`
(стр. 153–159: `setup-node` `'20'`, только при группе `frontend`), `courses/apps.py` (модели
подключаются импортом в `ready()`), `scripts/gen_module_map.py` (подпись стрелки — число мест
импорта), `scripts/check_docs_index.py` (сверяются `status`, `updated`, `title`), `git grep
edit_step` (вызывающие: `queue/views.py`, фасад `exam_solver/services.py`; тесты — только
`queue/tests/test_steps.py`).

Своя проверка: `simF3A/sim3.py` — HLFET плюс «К первыми», R = 3, ревью 8 мин, повтор ревью 5,
вливание 3, доработка **0.7 веса** новым запуском (кэш живёт 5 мин, запуск холодный), ≤ 2 кругов,
300 прогонов; партия и рёбра вливания; контрактный коммит C0 — отдельный узел 5 мин без ревью LLM.

## 0. Итог в цифрах

| Мера | Круг 2 | **Круг 3** |
|---|---|---|
| Задач | 24 | **27**: 4 `[K]`, 7 `[T]`, 4 `[S]`, 11 `[V]`, 1 `[H]` (+ приёмка `acceptance` вне слотов) |
| W, сумма весов | 407 (веса голов занижены) | **479** |
| S, путь по рёбрам старта | 94 (при честных весах ~119) | **108**: C0 → T002 → T013 → T022 → T023 (стек) → T027; той же длины C0 → T002 → T013 → T016 → T017 (стек) → T027 |
| P = W/S | 4.33 (честно ~3.6, красное) | **4.44**: K = 4 — предупреждение (4 ≤ P < 8); K = 5 — красное → **K = 4** |
| Путь с ревью и вливаниями (K = ∞) | — | **156 мин** |
| Фаза К | 69 мин, 17% | **78 мин, 16%**; глубина 1: T002, T003 стартуют от **влитого контрактного коммита C0** (§2, П-1′) |
| Пересечение `Файлы:` без пути | «0 без исключений» (неверно) | **1 названное исключение**: `module-map.md` + `module-graph.json` — `shared (генерируемый)`, решается перегенерацией (§6). `apps.py`, `TAGS.md`, `tech-stack.md`, `api-problems.json` — один хозяин или путь |
| Расписание K = 4, без отказов | 143 | **176** до вливания `[H]`; занятость 2.72 |
| То же при p = 0.43 / 0.30 / 0.15 | 208 / 189 / 166 | **273 / 243 / 206** (p80: 300 / 269 / 226) |
| Срок до передачи сессии пайплайна | 3.3 / 4.2 / 3.7 ч | **≈ 4.2 ч** без отказов; **≈ 5.6 ч** при p = 0.43; **≈ 4.5 ч** при p = 0.15 |

Круг 3 медленнее круга 2 на 33 мин без отказов и на 65 мин при p = 0.43. Из них:
- **+33** — честные веса голов пути (T001 deep, журнал из трёх задач вместо одной заниженной);
- **+22** при p = 0.43 — доработка 0.7 веса вместо 0.5 (`RW=0.5 sim3.py` даёт 251 против 273);
- **+20** в сроке — цена ставки «приёмка параллельно полному прогону» (§9), раньше она не
  считалась.

Круг 2 был быстрее не потому, что план лучше, а потому, что считал головы пути лёгкими.

## 1. Ответ на замечания круга 2

| # | Замечание | Что сделано |
|---|---|---|
| 1 | Голова пути занижена: T001 (~640 строк) «обычный M 15», T002 (~860 строк) «deep M 24» → честно S ≈ 119, P ≈ 3.6 < K | **T001 → deep M 24**; первым коммитом (≤ 5 мин) он кладёт контрактный коммит C0 (§2). **T002 разрезан как у B**: T002 [K] схема (модель, 0295, триггеры, deep M 24) → **T012 [S] чтение** ∥ **T013 [S] писатель** (оба deep M 24, от влитого T002). Пересчёт: S = 108, P = 4.44 ≥ K = 4 — предупреждение, не красное. Проверено обратное: без C0 (T002/T003 от влитого T001) — 304 мин при p = 0.43 (+31) |
| 2 | T011 меняет `exam_methodologist_queue/services.py` и вливается на 90-й, раньше партии Б (108): правки пишутся в старую таблицу, очередь читает журнал без правок | **Эталон очереди через журнал перенесён в партию Б** — в T017 (сервер очереди). T014 (бывший T011) трогает только `exam_solver/reference.py` и пакетное чтение; у этой функции в ветке нет вызывающих до партии Б (`git grep` на базе: очередь берёт эталон из `services.py` очереди). Все читатели журнала кандидата (T017, T021, T022, T023) и склейка KSA (T020) вливаются **после партии Б** (§8.3, инвариант ветки) |
| 3 | `node --test services/staff/utils/` в группе `frontend` пойдёт на Node 20 (`cicd.yml` стр. 157), `.ts` в тестах требует Node ≥ 22.6, флага в Node 20 нет | Проверено на `4ba293f13`: `setup-node` `'20'` стоит только при группе `frontend`. **T004 добавляет отдельный шаг в `cicd.yml`** (джоб `checks`, после групп): `setup-node` `'22'` + `npm --prefix services/staff test` (`"test": "node --test utils/"` в `package.json`). Правка `cicd.yml` будит хук `process-map-doc`, поэтому в T004 же: строка шага в `docs/engineering/process-map.json` и перегенерация `docs/meta/system/development-process.md` (`gen_process_map.py`). Шаг в `ci_quick_checks.py` убран |
| 4 | T003 заводит маршрут без описаний ручки, а `api-doc-coverage` такое не пропускает | **Описания GET и POST карточки — в T003**, в том же коммите, что `urls.py`: `docs/api/endpoints/staff-exam-tasks-solution{,-get}.md`, строки `docs/api/README.md`, строки `docs/TAGS.md`. Это текст шва C12 — для позиции A естественно: описание ручки и есть контракт. Срезы T021–T023 правят только тело своего описания, frontmatter не трогают (§8.2) |
| 5 | «0 пересечений без исключений» неверно: `apps.py` (T002 и T003), `module-graph.json`/`module-map.md` (почти каждый серверный срез), `TAGS.md` (T014 ∥ T016 ∥ T018 ∥ T019), `tech-stack.md` (T002 и T016) | Разобрано по файлу (§6): **`apps.py`** — один хозяин T001: в C0 он кладёт обе точки подключения (импорт `task_solutions.models` — пустой модуль, импорт `exam_solver.solution_registration` — пустой модуль). T002 заполняет `models.py`, T003 — `solution_registration.py`; `apps.py` больше никто не трогает. **`TAGS.md`** — T003 → T019 → T027, путь есть; остальные правят тело документов без frontmatter (`check_docs_index.py` сверяет только `status`, `updated`, `title`). **`tech-stack.md`** — T002 (0295) → T019 (0296), путь есть. **`module-map.md` + `module-graph.json`** — настоящее исключение: подпись стрелки — число мест импорта, его меняет каждый серверный срез с межмодульным импортом. Названо `shared (генерируемый)` с правилом перегенерации при rebase (П-9). Формулировку «без исключений» снимаю |
| 6 | Мелкое: вместо П-1 взять контрактный коммит B; приёмка ∥ полный прогон — ставка; доработка холодная, 0.7 | **П-1 отозвана**, принят контрактный коммит (П-1′, §2): `sim3.py` VAR=stackK (стек от сданного T001 целиком) — 285 мин при p = 0.43, C0 — 273. C0 лучше, потому что его ждут 5 мин, а не 24. **Ставка посчитана** (§9): параллельно дешевле последовательного при любой вероятности дефекта a < 1, ожидаемая цена +a·49 мин; при a = 0.4 — +20. **Доработка 0.7** во всех расчётах. П-7 («К первыми») отозвана: `nokfirst` даёт +1 мин, это шум |

## 2. Поправки процесса (поднимаются в `design.md`)

**П-1′ (вместо П-1). Контрактный коммит.** Предложение B (§9 п. 2 круга 2), принимаю: первый
коммит задачи К, который дословно переносит текст согласованного контракта и сверяется скриптом,
вливается отдельно, сразу после сверки и `check.sh`, без LLM-ревью. Другие К стартуют от него.
Это не стек: отказ ревью по смыслу шва невозможен, смысл меняет только поправка контракта.
- Здесь C0 = `task_solutions/types.py` и `registry.py` дословно по v4 §2.2–2.3 с правками
  v5/v6; пустые `task_solutions/models.py` и `exam_solver/solution_registration.py`; две строки
  импорта в `CoursesConfig.ready()`; строки модуля в `module-tiers.json` и
  `module-boundaries.json`.
- Сверка: `diff` блоков кода плана §2.2–2.3 против файлов пуст; `apps.py` отличается от базы
  ровно двумя строками из `contracts.md`.
- Расчёт: 273 мин (C0) против 285 (П-1, стек от сданного T001) и 304 (от влитого T001), p = 0.43.

**П-2. Партия обязательного вливания** — без изменений: `Вливается вместе: Б`, ≤ 3 задач, члены без
пересечения `Файлы:`. Б = {T017, T018, T019}.

**П-3′. Ребро вливания `Вливается после:` и инвариант ветки.** Старт по контракту, вливание — после
указанного соседа. Добавлено правило, которое и нарушил круг 2: **задача, которая читает или пишет
хранилище, переводимое партией, вливается после партии.** Проба: задача вне партии, чьи `Файлы:`
пересекаются с модулями членов партии по смыслу (вызов `edit_step*`, эталон очереди), без
`Вливается после: Б` → предупреждение. Механически ловится не всё: это строка линзы ревьюера К
и `architect`.

**П-4. К владеет раскладкой тестов** — без изменений (T001: правило `banks` в `GROUP_RULES`).

**П-5. `[H]` передаёт ветку после rebase на вершину приёмника и полного прогона** — без
изменений.

**П-6. Миграция данных — `[S]`, не К** — без изменений.

**П-8 (новая). Точки подключения — у одного хозяина.** Файл, через который модули
подключаются (`apps.py`, корневой `urls.py`, меню, DI), правит только К: в контрактном коммите
она кладёт строку импорта пустого модуля, который заполняет хозяин подключаемого. Это
частный случай `design.md` §3.1 («К заводит ключи и заглушки»), но в круге 2 его забыли для
`ready()`.

**П-9 (новая). Генерируемые файлы с подсчётом — `shared (генерируемый)`.** Файл, который
генератор строит из кода (здесь `module-map.md`, `module-graph.json`), не может иметь одного
хозяина: его меняет любой межмодульный импорт. В `pair-rules.txt` он помечается `shared` с
командой перегенерации, а `task_pairs.py merge` при конфликте в нём не зовёт исполнителя:
берёт сторону приёмника, запускает генератор и коммитит. Проба показывает такие пересечения
отдельной строкой, не красным. Если генератор пишет то, что зависит от порядка (номера,
даты) — это уже не `shared`, а владелец.

**П-10 (новая). Frontmatter и реестры документов.** Документ, который нужен срезу, заводит К или
сам срез с собственным файлом. Чужое описание срез правит только телом; `updated`, `status`,
`title` и `TAGS.md` правит хозяин документа или `[H]` (`check_docs_index.py --fill`). Довод:
хук `docs-index` сверяет только эти три поля; тело его не будит.

## 3. Истории и критерии приёмки (AC)

Новые номера: старый T011 (эталон) → T014 без части очереди; очередь-эталон → T017; журнал T002 →
T002 + T012 + T013; [T] журнала — новый T011.

| История | AC | Чем проверяется |
|---|---|---|
| US1 Журнал и координатор (ядро) | AC-1 сериализация `SolveRequest`, отказ `ml_context`, `enqueue_solve` → `ValueError` | контрактные тесты T001 |
| | AC-2 повтор `source_kind` / пересечение `journal_kinds` → `ImproperlyConfigured`; `current_solutions` как есть; `DEADLINE`; `SOLVER_FAILED`; `UnknownSolutionKind` | T001 |
| | AC-3а схема: только-дописывание (`UPDATE`/`DELETE`/`TRUNCATE` — ошибка базы), уникальности §3.1, 0295 вперёд и назад | T002 (`test_migration_0295`) |
| | AC-3б чтение: `head(s)`, `versions`, `latest_versions_for`, `derived_steps` (`step_id` по `STEP_NAMESPACE`), `step_history`, `heads_with_ksa`; запросов не больше при росте пакета | `[T]` T011 → T012 |
| | AC-3в запись: `VersionConflict` без записи; 422; семя; `step_source`, `ksa_source`; `subject_version` (§2.12); две записи → одна 409 (advisory lock); `IntegrityError` → `VersionConflict` | `[T]` T011 → T013 |
| US2 Решение задачи банка к версии | AC-4 16 случаев §5.2; пакет = поштучно, число запросов плоское | `[T]` T005 → T014 (случаи формы итога → T015) |
| | AC-5 адаптер `exam_task`: `NO_SOLUTION` / `UNKNOWN_SOURCE` / `SolutionView`; `solve` → `NOT_SUPPORTED`; зарегистрирован в веб- и Celery-процессе | T005 → T014 (регистрация — T003) |
| | AC-6 правило итога `steps_reach_answer` (§2.13) | T005 → T015 |
| | AC-7 очередь показывает того же кандидата, что `reference_solution` | T005 → **T017** (партия Б) |
| US3 Правка шага очереди на журнале | AC-8 GET `/queue/steps` без `edit_id`; POST с `based_on`; `unknown-reference`; 201 | `[T]` T006 → T017 (писатель — T016) |
| | AC-9 409 `entity_type=task_solution`, `current_state`; правка разных шагов при одной голове → 409; 17 прежних сценариев | T006 → T017 |
| | AC-10 клиент очереди: `based_on`, перечитывание на 409, тост Р-5, заметка `role="status"` | node-тесты T018 + e2e |
| US4 Перенос старых правок | AC-11 версии `human` = правкам; голова = старый `effective_steps`; идемпотентность; `INSERT` после 0296 — ошибка; повтор после отката; сверка; `raise` на удалённом шаге; литерал = `STEP_NAMESPACE` | `[T]` T007 → T019 |
| US5 Раздел «Решение» в карточке | AC-12 GET: голова журнала `exam_task` с `for_current_revision`, `reference` с `result_matches_answer`; у GET нет 409 | `[T]` T008 → T021 |
| | AC-13 POST, строки 2–4 Р-1: 409 «форма видела другой журнал», 403, те же шаги к новой ревизии → 201, `add_claim` под `lock_task` | T008 → T022 |
| | AC-13.1 POST, строка 1 Р-1 (поверх кандидата) через единственного писателя; чужая голова кандидата → 409 | T008 → T023 |
| | AC-14 показ раздела | node-тесты `examSolutionView` (T024) + e2e |
| | AC-15 форма списка, правила слияния 1–7 Р-6, `stale`, порядок чтений | `[T]` T009 → T025; UI — e2e (T026) |
| US6 Склейка KSA | AC-16 новая версия `origin=catalog_merge`; один повтор при конфликте; порядок замков | `[T]` T010 → T020 |
| Сквозные | AC-17 e2e Н-1 §5.3; AC-18 e2e Н-1б §3; AC-19 полный прогон django после rebase на ветку пайплайна; v6 подтверждён соседней сессией | `acceptance`, T027, координатор |

## 4. `contracts.md` (карта швов)

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| **C0** | контрактный коммит: `types.py`, `registry.py` дословно (v4 §2.2–2.3 + v5/v6), `STEP_NAMESPACE` литералом; пустые `task_solutions/models.py`, `exam_solver/solution_registration.py`; две строки в `CoursesConfig.ready()`; строки модуля в `module-tiers.json`, `module-boundaries.json` | T001, первый коммит, вливается после скриптовой сверки | T002, T003, все серверные |
| C1 | `types.py` (v2–v6) | T001 (C0) | T002, T003, T011–T023 |
| C2 | `registry.py` (`register`, `adapter_for`, `journal_owner`), `SolverAdapter` с необязательным `repoint_ksa`; координатор (`current_solution(s)`, `solve`, сигнатуры `enqueue_solve`, `register_outcome_listener`) | T001 | T003, T014, T020 |
| C3 | модель `SolutionVersion`, 0295, функция `task_solutions_append_only()` и триггеры | T002 | T012, T013, T019 |
| C4r | чтение журнала: `head(s)`, `versions`, `latest_versions_for`, `derived_steps`, `step_history`, `heads_with_ksa` — сигнатуры v4 §2.4 | T012 (реализация; сигнатуры — текст контракта) | T014, T016, T021, T022 |
| C4w | запись: `write_version`, `VersionConflict`, порядок замков «строка владельца → журнал» | T013 | T016, T020, T022 |
| C5 | `exam_solver.reference`: `ReferenceSolution`, `reference_solution(s)`; заглушка: пакет → `{}`, поштучно → `None` | T003 | T005, T008, T014 (реализация), T017, T021, T022 |
| C6 | `ExamTaskAdapter` (`current` через C5, `solve` → `NOT_SUPPORTED`, `repoint_ksa` → заглушка 0); регистрация — в `exam_solver/solution_registration.py` | T003 | T014, T020 |
| C7 | `exam_tasks.services.answer_form`, `revision_task_ids` — настоящие | T003 | T014, T015, T021 |
| C8 | `task_solving.answers.steps_reach_answer(steps, answer, form) -> bool \| None`; заглушка = прежнее `same_value` | T004 | T014, T021, T015 (реализация) |
| C9 | `exam_solver.step_edits`: `write_candidate_solution`, `conflict_state(ref)`, `edit_step_on_journal(..., based_on, step_id=None)` — заглушки `NotImplementedError`; **прежний `edit_step` не трогается** | T003 | T016 (реализация), T017, T023 |
| C10 | обработчик склейки: регистрация в `system_graph/merge_handlers.py`, `task_solutions/catalog_merge.py` — заглушка, возвращает 0 | T003 | T020 |
| C11 | API очереди §5.1 (GET/POST `/queue/steps`, члены 409) | T004 (типы TS), текст — план §5.1 | T006, T017, T018 |
| C12 | API карточки (GET/POST `/api/v1/staff/exam/tasks/<uuid>/solution`), **описания ручек `docs/api/endpoints/staff-exam-tasks-solution{,-get}.md`** | T003 (описания, маршрут), T004 (типы TS, клиент) | T008, T009, T021–T026 |
| C13 | полезная нагрузка эталона очереди: `steps[]` с `step_id`; форма `Reference.steps_candidate` прежняя | T003 | T017, T018 |
| C14 | TS `StepRules`, значение `stepRules` (заглушка — нынешняя логика `ReferenceBlock`) | T004 | T018 (реализация), T024, T025 |
| C15 | TS `examSolutionEdit.ts`: типы, сигнатуры, настоящая `targetOf` | T004 | T024, T025 (реализация), T026 |
| C16 | TS пропсы `SolutionEditor` | T004 | T024, T026 (реализация) |
| C17 | `examLabels.ts`: тексты Р-5, Р-6 | T004 | T018, T024, T026 |
| C18 | маршрут и `TaskSolutionView` (`get` → `solution_read.read`, `post` → `solution_writes.write`, заглушки 501). Объявленные ответы: GET 200/403/404, POST 201/403/409/422. **`api-problems.json` перегенерирует T003**; новые коды — `config/response-codes.json` (T003) | T003 | T021, T022, T023 |
| C20 | раскладка тестов: правило `banks` для `exam_solver\|exam_methodologist_queue` в `GROUP_RULES`; исключение `test_student_reports → platform` | T001 | все задачи с новыми тестами django |
| C21 | раннер staff: `"test"` в `services/staff/package.json`; **отдельный шаг `cicd.yml` с `setup-node` 22**; строка в `process-map.json` | T004 | T009, T018, T024, T025 |

Поправка шва — только добавлением (ADR-0019). Контракт v6 (§2.13) координатор отправляет соседней
сессии вместе с C0: «типы контракта в коде, коммит такой-то».

## 5. Задачи

Вес: 10 мин × 1.6 (deep) × 1.5 (M). Запуск — по наблюдениям 20–24.11: deep M 18–28 мин, deep S
13–20, обычный M 12–18, обычный S 8–12. Пути: `C/` = `services/django-api/courses/`,
`ST/` = `services/staff/`, `EX/` = `ST/app/(staff)/exam/`. Группы тестов — по `tr/cls.py` после
правки C20.

### Фаза К (78 веса, 16% W; глубина 1 от C0)

- [ ] T001 [K] Контракт `task_solutions`: типы, реестр, координатор, раскладка тестов, точки подключения
  Контракт: C0 (первый коммит), C1, C2, C20
  Файлы: C/task_solutions/{__init__,types,registry,services,models}.py (`models.py` — пустой, в C0), C/task_solutions/{README,AGENTS}.md, C/task_solutions/tests/{test_types,test_current_solutions}.py, C/exam_solver/solution_registration.py (пустой, в C0), C/apps.py (две строки, в C0), docs/engineering/{module-tiers,module-boundaries}.json, docs/engineering/module-map.md + module-graph.json (перегенерация — `shared`), scripts/test_registry.py (правило `banks`), scripts/tests/test_test_registry.py, docs/engineering/test-registry.json (исключение `test_student_reports: platform`)
  Зависит от: —
  Приёмка: AC-1, AC-2
  Готово-когда: **первый коммит (≤ 5 мин) — C0**: `diff` блоков v4 §2.2–2.3 против `types.py`/`registry.py` пуст, `apps.py` отличается от базы двумя строками из `contracts.md`, `check.sh` зелёный → координатор вливает C0 без ревью LLM. Дальше: AC-1, AC-2 тестами, краснеют на откате; `test_registry.py --check` зелёный, `--list` показывает `test_student_reports` в `platform`, пробный `exam_solver/tests/test_x.py` — в `banks`; никакой другой модуль не сменил группу (`--list` до и после); `check_module_boundaries.py`, `check_module_readme.py` зелёные
  Риск: deep · Размер: M (~250 строк кода координатора и реестра + тесты; перенос ~185 строк сверяет скрипт, ревьюер его не читает) · Тест-группа: django:banks, saga (scripts)
  Оценка: вес 24 (C0 5 + 19); запуск 18–28

- [ ] T002 [K] Журнал: схема `SolutionVersion` и 0295
  Почему не одна: модель импортирует C1; вместе с T001 больше M. Старт — от влитого C0
  Контракт: C3
  Файлы: C/task_solutions/models.py (заполнить), C/migrations/0295_task_solution_version.py, C/task_solutions/tests/_journal_fixtures.py, C/tests/test_migration_0295.py, docs/governance/tech-stack.md (блок головы миграций — `gen_stack_facts.py`)
  Зависит от: T001 (C0)
  Приёмка: AC-3а
  Готово-когда: 0295 вперёд и назад; `UPDATE`/`DELETE`/`TRUNCATE` — ошибка базы (тест); уникальности §3.1 тестами; `showmigrations` линейна 0294 → 0295; `gen_stack_facts.py --check` зелёный; `make_version` из фикстур пишет строку, которую читает модель
  Риск: deep · Размер: M (~230) · Тест-группа: django:platform (`test_migration_0295`, правило свежей базы)
  Оценка: вес 24; запуск 18–28

- [ ] T003 [K] Швы банка: адаптер, `ReferenceSolution`, заглушки писателя кандидата, маршрут и описания карточки, коды, регистрация
  Почему не одна: импортирует C1. Старт — от влитого C0
  Контракт: C5, C6, C7, C9, C10, C12 (описания), C13, C18
  Файлы: C/exam_solver/{adapter,reference,ksa_repoint,solution_read,solution_writes}.py (новые; все кроме `adapter` — заглушки), C/exam_solver/solution_registration.py (заполнить), C/exam_solver/step_edits.py (только новые заглушки C9 внизу файла), C/exam_solver/{services,views,urls}.py, C/exam_solver/README.md (список публичных функций), C/exam_tasks/services.py, C/exam_tasks/tests/test_answer_form.py, C/task_solutions/catalog_merge.py (заглушка), C/system_graph/merge_handlers.py (регистрация заглушки), C/tests/test_handler_registration.py, services/django-api/config/{response-codes,api-problems}.json (`api-problems` — генератором), **docs/api/endpoints/staff-exam-tasks-solution{,-get}.md**, docs/api/README.md (строки реестра), docs/TAGS.md (строки двух описаний, `check_docs_index.py --fill`), module-map.md + module-graph.json (перегенерация — `shared`)
  Зависит от: T001 (C0)
  Приёмка: AC-5 (часть «зарегистрирован»)
  Готово-когда: регистрация адаптера в веб- и Celery-процессе — тест; `answer_form`, `revision_task_ids` с тестом, краснеют на откате; маршрут отвечает 501 на оба метода; `check_api_doc_coverage.py`, `check_docs_index.py`, `check_codes.py` зелёные; у GET в `api-problems.json` нет 409; склейка каталога с заглушкой — прежний результат (тест на существующих данных); весь прежний набор `exam_*` зелёный
  Риск: обычный · Размер: M (~300 и два описания) · Тест-группа: django:banks, django:platform
  Оценка: вес 15; запуск 12–18 (верхняя граница M: если описания не влезают, это первый кандидат на отказ «незакрытый пункт»)

- [ ] T004 [K] Швы staff, раннер staff-тестов, заглушка правила итога
  Контракт: C8, C11, C12 (типы, клиент), C14, C15, C16, C17, C21
  Файлы: ST/utils/exam.ts (новые типы рядом со старыми; у шага очереди `step_id`, `version_id`, `based_on`), ST/utils/examLabels.ts, ST/utils/examStepEdit.ts (новый: тип и заглушка), ST/utils/examSolutionEdit.ts (типы, сигнатуры, `targetOf`), ST/utils/examSolutionTarget.test.cjs, EX/_components/SolutionEditor.tsx (заглушка с пропсами), ST/package.json (`"test": "node --test utils/"`), **.github/workflows/cicd.yml** (шаг «staff: node --test» в джобе `checks` после групп, `actions/setup-node@v4` с `node-version: '22'`, `cache-dependency-path: services/staff/package-lock.json`), docs/engineering/process-map.json (объявить шаг), docs/meta/system/development-process.md (перегенерация `gen_process_map.py`, frontmatter не трогать), C/task_solving/answers.py (заглушка C8)
  Зависит от: —
  Приёмка: —
  Готово-когда: `targetOf` по четырём строкам Р-1 — тест; `npm --prefix services/staff test` зелёный локально на Node 22, включая два существующих теста (`examQueueSelection`, `examTrustAlerts`), иначе шаг станет новым гейтом поверх старого красного; шаг CI прошёл на ветке (лог); `gen_process_map.py --check`, `check_process_map.py` зелёные; прежние тесты `task_solving` зелёные с заглушкой
  Риск: обычный · Размер: M · Тест-группа: staff-node (новый шаг), frontend, saga, django:banks
  Оценка: вес 15; запуск 12–18
  Оговорка: если в проекте путь `cicd.yml` защищён, шаг ставит человек; до его слова строгий xfail staff проверяется локально и пробным слиянием при сдаче.

### Приёмочные тесты `[T]` (окно К, строгий xfail, импорт внутри теста)

Зависят только от `contracts.md` и спеки. Вливаются после К своей стороны; срез вливается после своей `[T]`.

| Задача | AC | Файл | Группа | Вес | Запуск |
|---|---|---|---|---|---|
| T005 US2 | AC-4…AC-7 | C/exam_solver/tests/test_reference_solution_acceptance.py, C/task_solving/tests/test_steps_reach_answer_acceptance.py, C/exam_methodologist_queue/tests/test_reference_same_choice_acceptance.py | django:banks | M 15 | 12–18 |
| T006 US3 сервер | AC-8, AC-9 | C/exam_methodologist_queue/tests/test_steps_journal_acceptance.py | django:banks | S 10 | 8–12 |
| T007 US4 | AC-11 | C/tests/test_migration_0296_acceptance.py | django:platform (свежая база) | M 15 | 12–18 |
| T008 US5 сервер | AC-12, AC-13, AC-13.1 (тест на строку Р-1, чтобы T022 и T023 снимали свои xfail) | C/exam_solver/tests/test_task_solution_api_acceptance.py | django:banks | M 15 | 12–18 |
| T009 US5 клиент | AC-15 | ST/utils/examSolutionEdit.acceptance.test.cjs (обёртка `xfailStrict` в файле) | staff-node; вливается после T004 | M 15 | 12–18 |
| T010 US6 | AC-16 | C/task_solutions/tests/test_catalog_merge_acceptance.py | django:banks | S 10 | 8–12 |
| **T011 US1 журнал** | AC-3б, AC-3в | C/task_solutions/tests/test_journal_acceptance.py | django:banks | M 15 | 12–18 |

### Хребет журнала `[S]`

- [ ] T012 [S] Журнал: чтение
  Почему не срез: чтение одной таблицы пакетом, общее для T014, T016, T021, T022; сторон нет
  Контракт: C1, C3, C4r
  Файлы: C/task_solutions/reads.py, C/task_solutions/tests/test_reads.py
  Зависит от: T001, T002 · Приёмка: AC-3б (T011)
  Готово-когда: xfail AC-3б сняты; `assertNumQueries` не растёт с пакетом; `derived_steps` детерминирован; `hold`: откат `reads.py` красит свои тесты
  Риск: deep · Размер: M · Тест-группа: django:banks · вес 24; запуск 18–28

- [ ] T013 [S] Журнал: единственный писатель
  Почему не срез: одна точка записи с `pg_advisory_xact` и порядком замков; резать нельзя
  Контракт: C1, C3, C4w
  Файлы: C/task_solutions/journal.py, C/task_solutions/tests/{test_journal,test_journal_concurrency}.py
  Зависит от: T001, T002, T003 (коды) · Приёмка: AC-3в (T011)
  Готово-когда: xfail AC-3в сняты; два потока на одну голову → одна запись и один `VersionConflict` (`TransactionTestCase`, как `test_steps.py:412`); `IntegrityError` → `VersionConflict`; вложенная транзакция; `hold` краснеет
  Риск: deep · Размер: M · Тест-группа: django:banks · вес 24; запуск 18–28

- [ ] T016 [S] Писатель журнала кандидата
  Почему не срез: единственный писатель журнала кандидата для очереди (T017) и карточки (T023)
  Контракт: C4r, C4w, C9 (реализация)
  Файлы: C/exam_solver/step_edits.py (новые функции рядом со старым `edit_step`), C/exam_solver/tests/test_step_edits_journal.py
  Зависит от: T003; T012 (стек), T013 (стек) — стек внутри `[S]`-цепочки, вливается после обоих
  Приёмка: через T017 и T023
  Готово-когда: запись списком целиком; семя из шагов кандидата; `subject_version = revision_id`; замок строки кандидата раньше замка журнала (тест порядка); 409 по голове, `conflict_state` по `exc.ref`; прежний `edit_step` не тронут; `hold` красит новые тесты
  Риск: deep · Размер: S · Тест-группа: django:banks · вес 16; запуск 13–20

- [ ] T019 [S] US4: перенос правок в журнал (0296) и заморозка старой таблицы · **Вливается вместе: Б**
  Почему не срез: одна атомарная миграция данных со сверкой. Почему не в К: П-6
  Контракт: C1 (`STEP_NAMESPACE`), C3
  Файлы: C/migrations/0296_task_solution_version_from_step_edits.py, C/tests/test_migration_0296.py, docs/runbooks/task-solutions-0296.md (новый, со своей строкой в docs/TAGS.md), docs/governance/tech-stack.md (голова миграций)
  Зависит от: T002, T003 (путь по `TAGS.md`; T003 влит раньше T002, ожидания не добавляет) · Приёмка: AC-11 (T007)
  Готово-когда: xfail T007 сняты; литерал = `STEP_NAMESPACE`; сверка печатает итог; `gen_stack_facts.py --check`, `check_docs_index.py` зелёные
  Риск: deep · Размер: M · Тест-группа: django:platform · вес 24; запуск 18–28

### Веер `[V]`

- [ ] T014 [V] US2: `reference_solution` и пакетное чтение для курса и тренажёра
  Контракт: C4r, C5 (реализация), C6, C7, C8 (заглушка)
  Файлы: C/exam_solver/reference.py, C/exam_solver/tests/test_reference_batch.py
  Зависит от: T003, T004, T012 · Приёмка: AC-4 (без случаев формы итога), AC-5 (T005)
  Готово-когда: xfail сняты; `test_batch_equals_single`, `test_query_count_flat` краснеют на откате `reference.py`; **очередь не тронута** (эталон очереди — T017)
  Риск: deep · Размер: M · Тест-группа: django:banks · вес 24; запуск 18–28
  Инвариант ветки: до партии Б у `reference_solution` нет вызывающих в ветке; она видит журнал кандидата без перенесённых правок, и это никому не показывается

- [ ] T015 [V] US2: правило итога «одно число»
  Контракт: C8 · Файлы: C/task_solving/answers.py, C/task_solving/tests/test_answers.py
  Зависит от: T004 · Приёмка: AC-6 и случаи формы итога AC-4 (T005)
  Готово-когда: xfail AC-6 сняты; таблица §2.13 параметризована и краснеет на заглушке
  Риск: обычный · Размер: M · Тест-группа: django:banks · вес 15; запуск 12–18

- [ ] T017 [V] US3 сервер: ручки очереди и эталон очереди на журнале · **Вливается вместе: Б**
  Срез: US3, серверная половина (стек от T016 — половины разрезанного среза)
  Контракт: C5, C9, C11, C13
  Файлы: C/exam_methodologist_queue/views.py, **C/exam_methodologist_queue/services.py** (эталон через `reference_solution`, перенесено из круга 2 T011), C/exam_methodologist_queue/tests/{test_steps,test_reference_origin}.py, docs/api/endpoints/staff-exam-queue-steps{,-get}.md (только тело)
  Зависит от: T006; T016 (стек) · **Вливается после: T014** · Приёмка: AC-7, AC-8, AC-9 (T005, T006)
  Готово-когда: 17 сценариев на новой форме тела; `edit_id` нет в ответе; вызовов старого `edit_step` из очереди нет (`git grep`); xfail T006 и AC-7 сняты
  Риск: deep · Размер: M (верхняя граница: views + services + перепись 17 сценариев) · Тест-группа: django:banks · вес 24; запуск 18–28
  Если при сдаче дифф больше M — см. §10 п. 3 (решение заранее, а не по ходу)

- [ ] T018 [V] US3 клиент: форма шага очереди на `based_on` · **Вливается вместе: Б**
  Контракт: C11, C13, C14 (реализация), C17
  Файлы: EX/queue/_components/ReferenceBlock.tsx, ST/utils/examStepEdit.ts, ST/utils/examStepEdit.test.cjs, ST/utils/exam.ts (удалить `edit_id`, `base_edit_id`)
  Зависит от: T004, T006 · Приёмка: AC-10 (e2e)
  Готово-когда: node-тесты `mergeDraft` / `sameStep` / `stale` / пропавший шаг краснеют на откате; шаг staff в CI зелёный
  Риск: обычный · Размер: M · Тест-группа: staff-node · вес 15; запуск 12–18

- [ ] T020 [V] US6: склейка KSA через адаптеры
  Контракт: C2, C4w, C6, C10
  Файлы: C/task_solutions/catalog_merge.py, C/exam_solver/ksa_repoint.py, C/task_solutions/tests/test_catalog_merge.py, C/exam_solver/tests/test_ksa_repoint.py
  Зависит от: T001, T003, T013 · **Вливается после: Б** (склейка переписывает журнал кандидата, который до Б не содержит правок) · Приёмка: AC-16 (T010)
  Готово-когда: xfail сняты; ровно один повтор при конфликте; порядок замков — тест
  Риск: deep · Размер: S · Тест-группа: django:banks · вес 16; запуск 13–20

- [ ] T021 [V] US5 сервер: чтение решения (GET)
  Контракт: C4r, C5, C7, C8 (заглушка), C12, C18
  Файлы: C/exam_solver/solution_read.py, C/exam_solver/tests/test_solution_read.py, docs/api/endpoints/staff-exam-tasks-solution-get.md (только тело)
  Зависит от: T003, T004, T012 · **Вливается после: T014, Б** · Приёмка: AC-12 (T008)
  Готово-когда: свои тесты на настоящем журнале `exam_task` и на заглушке C5; после rebase на T014 и Б xfail AC-12 сняты
  Риск: обычный · Размер: M · Тест-группа: django:banks · вес 15; запуск 12–18

- [ ] T022 [V] US5 сервер: запись решения, строки 2–4 Р-1 (журнал `exam_task`)
  Контракт: C4r, C4w, C5, C12, C18
  Файлы: C/exam_solver/solution_writes.py, C/exam_solver/tests/test_solution_writes.py, docs/api/endpoints/staff-exam-tasks-solution.md (только тело)
  Зависит от: T003, T004, T012, T013 · **Вливается после: T014, Б** · Приёмка: AC-13 (T008)
  Готово-когда: на настоящих `write_version` и `lock_task`: `add_claim` под `lock_task` (тест порядка), две записи → одна 409, 409 `current_state` по `exc.ref`, 422 по §2.7, 403; строка 1 явно отвечает 501; xfail строк 2–4 сняты после rebase
  Риск: deep · Размер: M · Тест-группа: django:banks · вес 24; запуск 18–28

- [ ] T023 [V] US5 сервер: запись поверх кандидата, строка 1 Р-1
  Срез: вторая половина записи (стек от T022); писатель — обычное ребро от влитого T016
  Контракт: C9 (настоящий), C12
  Файлы: C/exam_solver/solution_writes.py (ветка строки 1), C/exam_solver/tests/test_solution_writes_candidate.py
  Зависит от: T016; T022 (стек) · **Вливается после: Б** · Приёмка: AC-13.1 (T008)
  Готово-когда: запись только через `write_candidate_solution` (тест и `hold`); чужая голова кандидата → 409 с `candidate_id`; xfail строки 1 сняты
  Риск: deep · Размер: S · Тест-группа: django:banks · вес 16; запуск 13–20

- [ ] T024 [V] US5 клиент: показ раздела · Файлы: EX/_components/SolutionSection.tsx, EX/_components/TaskDrawer.tsx, ST/utils/examSolutionView.ts, ST/utils/examSolutionView.test.cjs · Зависит от: T004 · AC-14 · обычный M, вес 15; 12–18 · staff-node
- [ ] T025 [V] US5 клиент: логика формы списка · Файлы: ST/utils/examSolutionEdit.ts, ST/utils/examSolutionEdit.test.cjs · Зависит от: T004 · AC-15 (T009) · deep M, вес 24; 18–28 · staff-node
- [ ] T026 [V] US5 клиент: `SolutionEditor` · Файлы: EX/_components/SolutionEditor.tsx · Зависит от: T004 · AC-15 (интерфейс, e2e) · обычный M, вес 15; 12–18 · frontend

### Хвост

- [ ] T027 [H] Выведение старого пути, документы, реестры, передача
  Файлы: C/exam_solver/step_edits.py (удаление старого `edit_step`, ADR-0019: вызывающих после Б нет, тестов нет — `git grep` на базе), C/exam_solver/services.py (убрать реэкспорт `edit_step`), C/exam_solver/{README,AGENTS}.md, C/exam_methodologist_queue/{README,AGENTS}.md, C/task_solving/README.md, C/task_solutions/README.md, frontmatter `updated` у тронутых описаний ручек + `check_docs_index.py --fill` (docs/TAGS.md), docs/INDEX.md, CHANGELOG, журнал дня, находки «хвост» дословно
  Зависит от: T012–T026
  Готово-когда: rebase на вершину `feature/course-pipeline-concept`; цепочка миграций линейна поверх неё; полный прогон всех django-групп и staff-node зелёный **до** передачи (П-5); затем сообщение сессии пайплайна
  Риск: обычный · Размер: M — вес 15 + ~30 мин прогона (слот на прогоне свободен) · Тест-группа: все

**Приёмка (`acceptance`, вне слотов).** Стенд `trn` один, ресурс `serial`. Подготовка (копия базы,
`recreate.sh`, `migrate`) и сценарии Н-1 §5.3 — после партии Б; сценарии Н-1б §3 — после T021–T026.
Оценка 75 мин. Почему параллельно полному прогону T027 и сколько это стоит — §9.

## 6. Карта владения файлами

Файлы, которые трогают больше одной задачи. У каждой пары есть путь, кроме одной строки `shared`.

| Файл | Задачи | Путь |
|---|---|---|
| `C/apps.py` | **только T001** (C0) | один хозяин (П-8) |
| `task_solutions/models.py` | T001 (пустой, C0) → T002 | C0 влит до старта T002 |
| `exam_solver/solution_registration.py` | T001 (пустой, C0) → T003 | то же |
| `module-tiers.json`, `module-boundaries.json` | T001 (C0) → T003 | C0 |
| **`module-map.md`, `module-graph.json`** | T001, T003, T012, T013, T014, T016, T017, T020–T023, T027 | **`shared (генерируемый)`**: пары T012 ∥ T013 ∥ T014 ∥ T021 ∥ T022 и др. без пути. Конфликт решает `task_pairs.py merge`: сторона приёмника + `gen_module_map.py` + коммит; исполнитель не участвует (П-9) |
| `docs/TAGS.md` | T003 → T019 → T027 | рёбра |
| `docs/governance/tech-stack.md` | T002 → T019 | ребро |
| описания ручек карточки | T003 → T021 (GET, тело), T003 → T022 → T023 (POST, тело) → T027 (frontmatter) | рёбра, стек |
| описания ручек очереди | T017 (тело) → T027 (frontmatter) | ребро |
| `exam_solver/step_edits.py` | T003 (заглушки) → T016 (новые функции) → T027 (удаление старого) | рёбра |
| `exam_solver/services.py` | T003 (фасад) → T027 (реэкспорт) | ребро |
| `exam_solver/solution_read.py` | T003 → T021 | ребро |
| `exam_solver/solution_writes.py` | T003 → T022 → T023 | ребро, стек |
| `exam_solver/reference.py`, `ksa_repoint.py`, `catalog_merge.py` | T003 → T014 / T020 | рёбра |
| `task_solving/answers.py` | T004 → T015 | ребро |
| `utils/exam.ts`, `examStepEdit.ts` | T004 → T018 | ребро |
| `utils/examSolutionEdit.ts` | T004 → T025 | ребро |
| `SolutionEditor.tsx` | T004 → T026 | ребро |
| README модулей | T001 / T003 → T027 | ребро |

Один хозяин: `scripts/test_registry.py`, `test-registry.json` — T001; `cicd.yml`, `process-map.json`,
`development-process.md`, `ST/package.json` — T004; `api-problems.json`, `response-codes.json`,
`merge_handlers.py`, `views.py`/`urls.py` `exam_solver` — T003; `views.py` и `services.py`
очереди — T017; `ReferenceBlock.tsx` — T018; `TaskDrawer.tsx` — T024; 0295 — T002; 0296 — T019.

Условие для `api-problems.json`: срезы не меняют объявленные ответы (C18 объявляет все). Срез,
которому нужен новый ответ, — это поправка C18 добавлением, а файл переходит к `[H]`.

## 7. Расписание, K = 4, R = 3 (без отказов; минуты от старта К)

Взятие и сдача по `sim3.py VAR=sched` (слоты перетасованы; номера слотов — для чтения):

| Слот | Задачи (старт–сдача) |
|---|---|
| 1 | C0 (0–5) → T001 (5–24) → T006 (24–34) → T009 (34–49) → T024 (49–64) → T013 (64–88) → T016 (88–104, стек) → T017 (104–128, стек) |
| 2 | T004 (0–15) → T002 (15–39) → T010 (39–49) → T015 (49–64) → T019 (64–88) → T021 (95–110) → T020 (110–126) |
| 3 | T011 (0–15) → T003 (15–30) → T018 (30–45) → T025 (45–69) → простой до 95 → T014 (95–119) |
| 4 | T005 (0–15) → T007 (15–30) → T008 (30–45) → T026 (45–60) → T012 (60–84) → T022 (99–123) → T023 (123–139, стек) |

T027 — 150–165 (ревью и вливание к 176).

Вливания: C0 — 9; T004, T005, T011 — 26; T001 — 35; T003, T007 — 41; T006 — 45; T002 — 50;
`[T]` — до 64; staff и T015 — 71–80; T012 — 95; T013 — 99; T016 — 115; T014 — 130;
**партия Б (T017, T018, T019) — 141**; T020, T021, T022 — 144; T023 — 150; T027 — 176.

Где простой. T002 ждёт слота с 9-й до 15-й (окно занято `[T]`), T012 — с 50-й до 60-й (слоты
взяли клиентские срезы на 45–49). Проверено правило «резерв слота под звено пути» (`LOOK`):
без отказов −7…−10 мин, при p = 0.43 −1 мин, при p = 0.15 −3. В шуме под отказами — не беру.

Монте-Карло, 300 прогонов, доработка 0.7 веса, ревью повтора 5 мин, ≤ 2 кругов; qi — сбой на rebase
у ребра вливания, qb — сбой сборки партии.

| K | без отказов | p = 0.43 (qi = qb = 0.3) | p = 0.30 (0.2) | p = 0.15 (0.1) |
|---|---|---|---|---|
| 3 | 194 | 302 | 263 | 228 |
| **4** | **176** | **273** (p80 300) | **243** (p80 269) | **206** (p80 226) |
| 5 | 162 | 273 | 237 | 198 |

Пятый слот без отказов даёт −14 мин, при p = 0.43 — 0, при p = 0.15 — −8: путь (156 мин при K = ∞)
держит фичу. Снижение p с 0.43 до 0.15 даёт −67 мин (−25%). K = 4.

Проверка решений круга 3, K = 4, p = 0.43:

| Вариант | Мин | Разница |
|---|---|---|
| **план** | **273** | — |
| без C0: T002, T003 от влитого T001 | 304 | +31 |
| П-1 круга 2: T002, T003 стеком от сданного T001 | 285 | +12 |
| без партии Б (невалидно по Н-1 §5.1, только цена) | 271 | −2 |
| T017 без ребра вливания на T014 | 271 | −2 |
| без «К первыми» | 274 | +1 |
| доработка 0.5 веса (допущение круга 2) | 251 | −22 |

Инвариант ветки (партия, рёбра вливания после Б) стоит ~2 мин: цена его ничтожна, а без него
ветка 50 минут живёт с расхождением записи и чтения.

## 8. Тесты, документы, ревью, вливания

### 8.1. Тесты

- Контрактные — в К. Приёмочные — в `[T]` под строгим xfail. Свои тесты среза — в файлах среза;
  `hold` откатывает не-тестовые `Файлы:`.
- Раскладка по группам CI решена один раз в T001 (C20); ни одна задача веера не трогает
  `test-registry.json`.
- staff-тесты (`*.test.cjs`, включая строгий xfail T009) с T004 идут в CI **отдельным шагом на
  Node 22**. Быстрая группа `frontend` (Node 20) их не трогает. Pre-commit их не гоняет (хук
  `test-registry` смотрит `.test.(ts|js)`): исполнитель гоняет `npm --prefix services/staff test`
  сам, это в `Готово-когда:`.
- Миграционные тесты (T002, T007, T019) — `django:platform`, свежая база. Партию Б собирают без
  `--keepdb`.
- Предел: `tsc` для staff в CI нет; типовую ошибку клиента ловит сборка образа staff или e2e.
  Новым гейтом посреди фичи его не ставим: под ним неизвестное число старых ошибок.

### 8.2. Документы

- Описания ручек карточки — T003 целиком (хук `api-doc-coverage` не пропускает маршрут без
  описания). T021–T023 правят только тело своего описания, если реализация уточнила текст;
  смысл шва меняется только поправкой C12 добавлением.
- Описания ручек очереди — тело в T017.
- Раннбук 0296 — T019, со своей строкой `TAGS.md`.
- README `task_solutions` с текстом контракта — T001; список публичных функций `exam_solver` —
  T003; проза README, `AGENTS.md`, frontmatter тронутых документов, `TAGS.md --fill`, `INDEX`,
  CHANGELOG, журнал — T027.

### 8.3. Ревью и вливания

- Пул ревьюеров — 3, линзы по видам. C0 ревьюер не читает: сверяет скрипт.
- Ревьюеру T012/T013 и T016 сообщают, что поверх уже идёт работа (T016; T017). Строгость отказа
  от этого не снижается.
- Линзы: T013, T016, T022 — путь записи (порядок замков, единственный писатель); T023 — нет
  второго входа в журнал кандидата; T017 — эталон очереди и ручки читают одно хранилище.
- **Инвариант ветки.** После любого вливания запись и чтение одной сущности идут в одно
  хранилище. До партии Б журнал кандидата пишет только старый путь, а читать его некому. После
  Б пишет только новый путь, и всё, что его читает (T020–T023), вливается после Б.
- **Партия Б.** Каждый член проходит своё ревью. Когда у всех трёх «можно сливать», координатор:
  1. rebase T017 → T018 → T019 на голову ветки фичи;
  2. собирает один кончик, гоняет `check.sh`, T005 (AC-7), T006, T007 без `--keepdb`, staff-node;
  3. вливает `--ff-only` одним пушем. CI — только на кончике (промежуточные коммиты партии не
     обязаны быть зелёными, предел для `git bisect`, отметка в журнале).

  Красная сборка — доработка члена, чей тест упал; партия ждёт целиком.
- **Рёбра вливания** (T017 ⇒ T014; T020–T023 ⇒ Б; T021, T022 ⇒ T014): rebase, прогон `[T]`
  истории; красное — доработка без ревью.
- **Генерируемые файлы**: конфликт в `module-map.md`/`module-graph.json` при rebase решает скрипт
  перегенерацией (П-9); если `gen_module_map.py --check` после этого красный — это уже не
  механика, а ошибка среза (нарушение границ), и задача идёт в доработку.
- **CI партиями** (отпечаток грубый: любая правка `services/` гоняет все django-группы, 15–28 мин):
  1. C0, К и `[T]` (~26–64);
  2. staff и T015 (~80);
  3. T012, T013, T016 (~115);
  4. T014 + Б (~141);
  5. T020–T023 (~150);
  6. T027 + полный прогон после rebase на ветку пайплайна.

  На путь ложится только последняя.

## 9. Срок

Приёмка против полного прогона T027 — **ставка, и она посчитана**. a — вероятность, что приёмка
найдёт дефект; цена дефекта при параллели = доработка (0.7 × ~15) + повтор ревью 5 + вливание 3 +
повторный прогон 30 ≈ 49 мин; при последовательном порядке ≈ 19 мин, но прогон всегда стоит после
приёмки (+30).
- Параллельно: max(прогон, приёмка) + a·49.
- Последовательно: приёмка + 30 + a·19.
- Параллель выгоднее при a·30 < 30, то есть при любом a < 1. Беру a = 0.4 (оценка, не замер):
  +20 мин.

| Отрезок | Без отказов | p = 0.43 | p = 0.15 |
|---|---|---|---|
| К + веер + хвост (вливание T027) | 176 | 273 | 206 |
| Полный прогон после rebase (в T027) | +30 → 206 | 303 | 236 |
| Приёмка `trn` (старт после Б: 141 / 196 / 154; 75 мин), параллельно | до ~216 | до ~271 | до ~229 |
| Ожидаемая цена дефекта приёмки (a = 0.4) | +20 | +20 | +20 |
| Передача сессии пайплайна и её вливание | +15 | +15 | +15 |
| **Итого** | **≈ 251 мин (4.2 ч)** | **≈ 338 мин (5.6 ч)** | **≈ 271 мин (4.5 ч)** |

Не входят шаги 0–4 (спека, `contracts.md`, перекладка, проба) и ожидание ответа соседней сессии
по v6.

Занятость: за фичу 2.72 без отказов и 2.63 при p = 0.43 (сегодня 2.1–2.4); в окне 0–69 мин —
4 из 4; 69–95 — 2–3 из 4 (веер ждёт чтение и писатель журнала, §10 п. 1); 95–126 — 4 из 4;
после 126 — 1–2.

Качество (оценка, не замер): доля «нельзя сливать» 0.43 → ~0.25–0.3.
- «Пересечение с соседней задачей» — пересечений `Файлы:` без пути нет, кроме генерируемой
  пары, которую решает скрипт.
- «Незакрытый пункт» и «тест ничего не держит» ловят `[T]` и `hold`; строгий xfail staff
  гоняется на Node 22.
- «Расхождение сторон» держат партия Б (очередь), инвариант ветки, C12 + `[T]` (карточка), e2e.
- Путь записи не проверяется на подменах.

## 10. Конфликты и простой

1. **Хребет журнала — узкое место.** C0 → T002 → T012 ∥ T013 → T016 → T017 и T013 → T022 → T023.
   Пять звеньев deep; отказ любого сдвигает партию Б и карточку на 15–20 мин. Путь при K = ∞ —
   156 мин из 176: пятый слот почти ничего не даёт. Это свойство фичи с новым ядром, а не плана
   (B пришёл к тому же: P ≈ K, не 2K).
2. **Хвост.** После ~125 мин работают 1–2 слота: ждут партию Б и T023.
3. **T017 на верхней границе M** (views + services очереди + перепись 17 сценариев). Если при
   сдаче больше M, вынести нечего без партии из четырёх — это красное по П-2, решает
   `architect` до старта: либо принять L для T017 (вес 34, +10 на пути), либо перенести
   эталон очереди в отдельную задачу и вливать его **после** Б с подменой старой функции,
   которая до того читает старую таблицу (выведение).
4. **Партия Б.** Один отказ задерживает троих; T018 готов на 45-й и ждёт до 141-й. Слот при этом
   свободен, но клиент очереди ~1.5 ч не виден на `trn`.
5. **Стык чтения T021/T022 ⇒ T014.** Сбой на rebase возможен (qi); дешевле обычного ребра.
6. **`GROUP_RULES` в T001** меняет группу одному чужому модулю (закрыт исключением). Ревьюер
   T001 сверяет `--list` до и после.
7. **Шаг staff в CI** — новый шаг в `cicd.yml` на Node 22. Если `cicd.yml` защищён, ставит
   человек; до этого строгий xfail staff — только локально и при пробном слиянии.
8. **Генерируемые файлы.** `module-map.md`/`module-graph.json` — общие по построению; план не
   делает вид, что их нет, а отдаёт их скрипту (П-9). `api-problems.json` — один хозяин при
   условии §6.
9. **Стенд один.** Приёмка последовательна, стартует после Б; цена дефекта приёмки посчитана (§9).
10. **v6 не согласован.** Возражение соседней сессии меняет только T015 и случаи T005; C0
    переносит v6 как есть, поправка — добавлением.
