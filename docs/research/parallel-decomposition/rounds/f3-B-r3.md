# Фича 3 (`task_solutions` + раздел «Решение»): разложение и план. Команда B, круг 3

Дата 2026-11-24. Процесс — `design.md` (шаги 0–14, форма задачи §4, проба §5).
Вход тот же: `feature-3-description.md`, санированные `n1-plan-design`, `n1b-design`, `contract-v4.md`,
код и документы наставника только на `4ba293f13`. Прошлая версия — `f3-B-r2.md`. Что в этом файле не
изменилось против r2, я переношу без изменений, а правки отмечаю **(r3)**.

Расчёты в `simF3B/`:
- `f3b_r3.py` — граф круга 3 и та же событийная модель (400 прогонов). Режимы: строгий K и «звено
  пути сверх K». Во втором режиме сверх K можно не больше одного звена, и только из множества
  `tl + bl − w = S` (критические по чистому графу зависимостей);
- `block_r3.py` — тот же граф в сегодняшнем режиме;
- `slots_r3.py` — расписание без разброса, строгий K = 4;
- `tr/cls.py` — раскладка тест-модулей по группам `scripts/test_registry.py` на `4ba293f13`.

Генераторы и хуки, которые пишут файлы за задачу, проверены на `4ba293f13` по `.pre-commit-config.yaml`
и `scripts/ci_quick_checks.py`: `docs-index`, `module-map`, `gen_stack_facts`, `gen_process_map`,
`gen_problem_codes_doc` (§3.1).

## 0. Итог в цифрах

| Мера | Значение |
|---|---|
| Задач исполнителей | **31**: 4 `[K]`, 4 `[S]`, 11 `[V]`, 11 `[T]` (9 приёмочных и 2 подготовки e2e), 1 `[H]`; плюс 2 приёмки `acceptance` |
| W (сумма весов §5) | **536** (K 78, S 88, V 220, T 140, H 10). В r2 было 473: недовес снят (r3) |
| S (критический путь) | **98**: `T002 [K] → T006 [S] → T007 [S](стек) → T010 [V] → T028 [H]`. Путь той же длины идёт через T012. На пути только deep: S или M, ни одной задачи больше M |
| P = W/S | **5.47**. При K = 4 и K = 5 это «предупреждение» (K ≤ P < 2K), красного нет |
| Границы T (Грэм) | K = 3: 179…277; K = 4: 134…232; K = 5: 107…205 |
| Фаза К | 15% W, 4 задачи, глубина 1. C0 — контрактный коммит T001 |
| Модель, **строгий K = 4** (R = 3), до вливания `[H]` | p = 0: **169**; 0.15: 199; 0.3: **229** (P90 266); 0.43: **260** (P90 302) |
| До «принята» (A1, A2 на trn, последний CI и полный прогон `courses`) | p = 0.3: **~309** мин (P90 342); p = 0.43: **~339** (P90 375) |
| Тот же граф в сегодняшнем режиме | 219 / 289 / 330 до `[H]` при p = 0 / 0.3 / 0.43. Новый процесс быстрее на **21–23%** |
| Занятость до `[H]` | 3.1–3.3 из 4. Сегодня 2.1–2.4 |
| K = 5 (R = 4) | до `[H]` 158 / 216 / 249: −11…−13 мин, занятость 3.3–3.6 из 5. Запусков столько же |
| «Звено пути сверх K» в узкой форме | −3…−5 мин при p ≤ 0.15, при p ≥ 0.3 ноль (229 → 229, 260 → 261). **Правило снято** (§8.1) |

Против r2 стало медленнее на 12–16 мин до `[H]` (r2: 157 / 215 / 244, и это со слотом сверх K).
Скорость не терялась: в r2 был недовес. У T010 и T014 был размер L, а стоял M; T013 был deep, а стоял
обычным. Ниже цифры честного веса.

## 1. Ответ на замечания оценщика (r3)

| Замечание | Что сделано | Проверка |
|---|---|---|
| Скрытые общие файлы, которые пишут хуки: `docs/TAGS.md` (T003, T008, T010, T012; T008 и T010 в одной партии), `tech-stack.md` (T002, T008, перенумерация в T028), `development-process.md` (от `cicd.yml` в T004) | Всё внесено в `shared-generated` (§3.1) вместе с генератором и задачами, которые его запускают. Сверка нашла ещё два таких файла, которых оценщик не назвал: `docs/engineering/module-map.md` и `module-graph.json`. Хук `module-map` срабатывает на любой `courses/*.py` и перестраивает их от нового межмодульного импорта: это 8 задач. У каждой задачи появилось поле `Генерирует:`. Правило: такие файлы при rebase и пробном слиянии **не сливаются, а перегенерируются**. В пробе появилась новая строка (§9 п. 9): `Файлы:` сверяются с `files:` хуков-генераторов, и генерируемый файл вне `shared-generated` — красное | `.pre-commit-config.yaml` на `4ba293f13`: `docs-index` (`^docs/.*\.md$` → `check_docs_index.py --fill`), `module-map` (`courses/.*\.py` → `gen_module_map.py`), `gen_stack_facts --check` (голова миграций в `tech-stack.md`), `gen_process_map --check` (`cicd.yml` → блок `GENERATED:process-map`) |
| T010 ~560 строк, больше M, на критическом пути, а это не названо | Разрезан. **T010** [V] deep M (~300 вместе с тестами): запись и чтение очереди в `step_edits.py`, тесты в новом файле. **T029** [V] обычный M (~260): ручки очереди (`views.py`, `services.py`, `test_steps.py`, документы). T029 стартует от К, потому что вызывает новые точки через фасад (C7), а в тестах до вливания T010 подменяет их фикстурой C19. Вливаются вместе. На пути остался T010 размера M, S не изменился | `f3b_r3.py`: S = 98. Путь: `T002 → T006 → T007 → T010 → T028` |
| T013 (слияние при 409 и правила Р-6, ~540 строк кода и ~950 тестов) стоит «обычным», а этот класс работы в бейзлайне дал 4 круга ревью | T013 стал **deep**. 540 строк кода больше M и для deep, поэтому задача разрезана так же, как T010. **T013** [V] deep M: состояние формы, редьюсер, отправка. **T031** [V] deep M: `mergeSolution(base, mine, theirs)` по правилам 1–7 Р-6 в своём файле `examSolutionMerge.ts`; заглушку и сигнатуру кладёт T004 (C14). Линза ревью T031 — «каждое правило Р-6 и обратный случай» | W +33. Задачи не на пути: `T004 → T013/T031 → H` = 15 + 24 + 10 |
| T014 вместе с редактором списка — ~780 строк, надо резать на показ и редактор | **T014** [V] M: показ, `SolutionSection.tsx`, `TaskDrawer.tsx`, `exam.css`. **T030** [V] M: редактор списка шагов `SolutionStepsEditor.tsx` (заглушку с пропсами кладёт T004, C18) и свой `solution-steps.css`; так в staff уже устроены `audit.css` и `explorer.css`. Общих файлов у T014 и T030 нет | карта владения §5 |
| «Звено пути не ждёт слота» — это фактически K = 5 при P = 4.83 < 5. Нужны цифры и при строгом K = 4. Правило ограничить: не больше одного сверх K и только для звена с рангом = S | Все основные цифры теперь даны **при строгом K = 4**. Ограниченная форма правила посчитана: даёт −3…−5 мин при p ≤ 0.15 и ничего при p ≥ 0.3, то есть меньше разброса. **Правило снято**, поправка §9 п. 3 из r2 отозвана. K = 5 посчитан отдельно, честно как K = 5: при P = 5.47 проба его больше не красит, выигрыш −11…−13 мин | `f3b_r3.py`, `ov=0/1`, `K=5` |
| Шов C11 «все новые коды» пуст: контракт прямо говорит «новых кодов нет» | **C11 снят.** v4 §2.7: «Новых кодов нет. Сверено с `response-codes.json`… Все девять кодов есть». `UnknownSolutionKind` — исключение Python, сетевого кода у него нет. `config/response-codes.json` из `Файлы:` T003 убран | `contract-v4.md` §2.7 |
| Ребро T006 → T003 «(коды)» ложное | Снято. T006 зависит только от T001 и T002 | S от этого не изменился: T002 (24) тяжелее T003 (15) |
| Если коды всё же появятся, нужны также `locale/ru/problems.json` и перегенерация `problem-codes.md` | Записано как процедура поправки контракта (§3, после таблицы). Это не работа среза: строка в `config/response-codes.json`, текст в `config/locale/ru/problems.json`, перегенерация `docs/api/problem-codes.md` (`gen_problem_codes_doc.py`, проверка свежести в pre-commit и CI). Всё делает владелец поправки одним коммитом в К-уровень. `problem-codes.md` стоит в `shared-generated` с пометкой «только при поправке» | `ci_quick_checks.py:394` |

Ответы на замечания r1 (разрез T001, правило «одно число» в `[V]`, `test-registry`, раннер staff,
`data-testid` в контракте) остаются как в `f3-B-r2.md` §1.

## 2. Истории и критерии приёмки (`AC-n`)

| История | Что | AC |
|---|---|---|
| US1 | журнал решений и координатор: контракт для курса | AC-1…AC-8 |
| US2 | перенос правок `ExamSolverStepEdit` в журнал (0296) | AC-9…AC-11 |
| US3 | выдача эталонного решения банка (`reference_solution`, адаптер) | AC-12…AC-14 |
| US4 | очередь методолога на журнале: API (§5.1) | AC-15…AC-17 |
| US5 | запись решения задачи банка: сервер `/tasks/<id>/solution` | AC-18…AC-21 |
| US6 | раздел «Решение»: логика формы, слияние при 409, показ, редактор | AC-23…AC-26 |
| US7 | форма шага в очереди: слияние по полям и хвосты Р-5 | AC-27, AC-28 |
| US8 | склейка KSA каталога через адаптеры | AC-29 |
| US9 | сверка итога шагов с ответом: правило «одно число» | AC-22 |
| e2e | стенд trn: Н-1 §5.3, Н-1б §3; полный прогон | AC-30…AC-32 |

Тексты AC-1…AC-32 — как в `f3-B-r1.md` §2. **(r3)** Кто какие AC снимает: AC-15 и AC-16 (семантика
записи и чтения из журнала) — T010; AC-14 и AC-17 (форма ответа ручки, один выбор с
`reference_solution`) — T029. AC-23 и AC-25 (форма, отправка, `NeedsRight`) — T013; AC-24 (409 и
слияние) — T031. AC-26 (показ и редактор) держит e2e T027.

## 3. `contracts.md` (шаг 1, `architect`)

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| C0 | **Контрактный коммит**: `task_solutions/types.py` и `registry.py` дословно по v4 §2.2–2.3 с правками v5/v6; строки `task_solutions` в `module-tiers.json` и `module-boundaries.json`, включая ребро `exam_solver → task_solutions` | T001, первый коммит | T002, T003 (подтягивают), все серверные |
| C1 | `task_solutions/services.py` — публичные точки v4 §2.4. Координатор `current_solution(s)`, `solve`, `enqueue_solve` (`NotImplementedError` по контракту), `register_outcome_listener`. Точки журнала — делегаты с ленивым импортом: `head(s)`, `versions`, `latest_versions_for`, `derived_steps`, `heads_with_ksa` → `reads.py` (T005); `write_version`, `step_history` → `journal.py` (T006) | T001 | все серверные |
| C2 | `task_solutions/tests/_fixtures.py`: `FakeAdapter`, контекст `registered(adapter)` | T001 | серверные `[T]`, T009, T015 |
| C3 | Таблица `task_solution_version`, `0295` (ограничения §3.1, функция и триггеры), `models.py`, строка импорта моделей в `apps.ready()` | T002 | T005, T006, T008 |
| C4 | `task_solutions/tests/_journal_fixtures.py`: `make_version` (строка мимо `write_version`) | T002 | T005–T007, T009, T010, T012, T015, T029, серверные `[T]` |
| C5 | `exam_tasks.services.answer_form(task, revision=None)`, `revision_task_ids(ids)` | T003 | T009, T012 |
| C6 | `task_solving.answers.steps_reach_answer(steps, answer) -> bool \| None` — **заглушка, всегда `None`**; `RULE_TEXT = ""` | T003 | T009, T012, T014 (тело — T016) |
| C7 | `exam_solver/services.py` — фасад, ленивые делегаты: `reference_solution(s)` → `reference.py`; `write_candidate_solution`, `candidate_conflict_state` → `step_edits.py` (T007); **(r3)** `queue_steps(candidate_id)` и `queue_step_write(candidate_id, order, fields, base_seq, user)` → `step_edits.py` (T010), сигнатуры по §5.1; `task_solution_read/write` → `solution_writes.py`; `repoint_ksa` → `solution_repoint.py`. Очередь уже ходит в решатель только через фасад (`from courses.exam_solver import services as solver` в `views.py:24` и `services.py:38`) | T003 | T007, T009, T010, T012, T015, T029 |
| C8 | `exam_solver/adapter.py` — каркас адаптера (`source_kind = "exam_task"`, `journal_kinds = ("exam_solver_candidate", "exam_task")`): `current` → `reference.current_for`, `repoint_ksa` → `solution_repoint`, `solve` → `NOT_SUPPORTED`; регистрация в `apps.ready()` (блок в конце `ready`) | T003 | T009, T015, курс |
| C9 | Заглушки модулей: `exam_solver/reference.py` (`NotImplementedError("T009")`), `solution_repoint.py` (`→ 0`), `solution_views.py` (501) | T003 | T009, T015, T012 заполняют |
| C10 | HTTP `GET/POST /api/v1/staff/exam/tasks/<uuid>/solution`: маршрут, схемы, декораторы, `docs/api/endpoints/staff-exam-tasks-solution{,-get}.md`; отказы — только коды v4 §2.7 | T003 | T012, T013, T014, T027 |
| ~~C11~~ | **(r3) Снят.** Новых кодов нет (v4 §2.7), все девять есть в `response-codes.json` | — | — |
| C12 | HTTP `/queue/steps` v2 (§5.1): текст схемы — здесь, типы — C13 | T004 (типы) | T010, T011, T029 |
| C13 | `staff/utils/exam.ts` — новые типы рядом со старыми (только дописывание) | T004 | T011, T013, T014, T030, T031 |
| C14 | `staff/utils/examStepEdit.ts`: `StepRules`, `stepRules` (вынос из `ReferenceBlock` без смены поведения). `examSolutionEdit.ts` — каркас: состояние, действия, `solutionFormReducer(rules)`, `submitSolution(state, deps)`. **(r3)** `examSolutionMerge.ts` — сигнатура `mergeSolution(base, mine, theirs): MergeResult` и тип `MergeResult` (пометки `changed / deleted-by-other / added-by-other / new`, флаг `sameAsTheirs`); тело — `throw new Error("T031")` | T004 | T011, T013, T014, T030, T031 |
| C15 | `data-testid` (список — как в r2 §3) и ключи `examLabels.ts` | список — `architect`, ключи — T004 | T011, T014, T026, T027, T030 |
| C16 | Раннер staff: `npm test` → `node --test utils/*.test.cjs`; шаг CI | T004 | T011, T013, T021, T023, T031 |
| C17 | `exam_solver/tests/_solution_fixtures.py`: `fake_reference(mapping)` подменяет делегат `reference_solution(s)` фасада | T003 | T010, T012, T029 (до вливания T009) |
| **C18 (r3)** | `exam/_components/SolutionStepsEditor.tsx` — пропсы `{ steps, marks, rules, dispatch, readOnly }`; заглушка показывает список только для чтения. В C15 за редактором закреплены `solution-step-<n>-up / -down / -delete`, `solution-step-add-after-<n>`, `-mark` | T004 | T014 (вставляет), T030 (тело) |
| **C19 (r3)** | `exam_solver/tests/_solution_fixtures.py`: `fake_queue_journal(steps_by_candidate)` подменяет делегаты `queue_steps` и `queue_step_write` фасада | T003 | T029 (до вливания T010) |

Ленивые делегаты и заглушки — как в r2: T003 не зависит от кода срезов, а срезы стартуют от влитого К.
`apps.py` правят T002 и T003, разные блоки `ready()`: это строка `shared` в `pair-rules.txt`.

**Если коды всё же появятся (r3).** Это поправка контракта, а не работа среза. Владелец поправки
(`architect` или задача К, если она не влита) одним коммитом делает три вещи: строку в
`services/django-api/config/response-codes.json`, текст в `services/django-api/config/locale/ru/problems.json`
и перегенерацию `docs/api/problem-codes.md` через `python3 scripts/gen_problem_codes_doc.py`. Свежесть
`problem-codes.md` проверяют pre-commit и CI (`ci_quick_checks.py:394`). Потребители подтягивают
коммит; если поправка ломающая, координатор останавливает их одним сообщением.

### 3.1. `shared-generated` (r3): файлы, которые за задачу пишут хуки и генераторы

Правило. Генерируемый файл не входит в `Файлы:` ни одной задачи как собственный. Задача, правка
которой его меняет, называет его в поле `Генерирует:` и коммитит результат генератора. При rebase и
пробном слиянии конфликт в таком файле **не сливается руками**: скрипт берёт версию цели, запускает
генератор и коммитит. Генератор детерминирован от дерева, поэтому после слияния он даёт правду.
Пересечение по `Генерирует:` проба показывает, но не красит. Красное — генерируемый файл, которого
нет в списке ниже.

```
# pair-rules.txt — shared-generated: файл | генератор | кто запускает
docs/TAGS.md                              | python3 scripts/check_docs_index.py --fill | T003, T008, T012, T029, T028
docs/governance/tech-stack.md             | python3 scripts/gen_stack_facts.py          | T002, T008, T028
docs/meta/system/development-process.md   | python3 scripts/gen_process_map.py          | T004
docs/engineering/module-map.md            | python3 scripts/gen_module_map.py           | T001, T003, T007, T009, T010, T012, T015, T028
docs/engineering/module-graph.json        | python3 scripts/gen_module_map.py           | (те же)
services/django-api/config/api-problems.json | python3 scripts/gen_api_problems.py      | T003; T012 и T029 — если меняется декоратор
docs/api/problem-codes.md                 | python3 scripts/gen_problem_codes_doc.py    | только при поправке контракта по кодам
```

Откуда список:

| Файл | Что его пишет | Почему задача его трогает |
|---|---|---|
| `docs/TAGS.md` | хук `docs-index` на `^docs/.*\.md$`: строка индекса на каждый документ, сверка с frontmatter (`updated` тоже) | T003 — два документа ручки и строки `docs/api/README.md`; T008 — раннбук 0296; T012 — примеры в документах ручки; T029 — документы `/queue/steps`; T028 — `module-map.md` |
| `tech-stack.md` | `gen_stack_facts.py`: блок `GENERATED:stack-facts`, строка «Голова миграций Django: `0294_…`» | T002 (0295), T008 (0296), T028 (перенумерация после rebase) |
| `development-process.md` | `gen_process_map.py`: блок `GENERATED:process-map` из `cicd.yml` и `process-map.json` | T004 добавляет шаг CI для staff |
| `module-map.md`, `module-graph.json` | хук `module-map` на `courses/.*\.py`: схема строится из импортов | новые межмодульные рёбра: T001 (новый модуль), T003 (`exam_solver → task_solutions`, `exam_tasks`), T007, T009, T010 (`task_solutions`, `task_solving`), T012, T015 (`system_graph → task_solutions`), T028 |
| `api-problems.json` | `gen_api_problems.py` из декораторов | T003 — новые ручки; T012, T029 — если меняется набор отказов |

Где в партиях это встречается: в обязательной партии {T008, T010, T029, T011} `TAGS.md` пишут T008 и
T029, `module-map` — T010, `tech-stack.md` — T008. Без правила это три ручных слияния в самой
дорогой партии, с правилом — три запуска генератора в скрипте пробного слияния.

## 4. Задачи (`tasks.md` после перекладки)

Вес по §5: 10 × 1.6 (deep) × 1.5 (M). Запуск — оценка по наблюдениям 20–24.11: deep M 18–28 мин,
deep S 13–20, обычный M 12–18, обычный S 8–12. Группы тестов проверены `tr/cls.py` на `4ba293f13`.
Размер: S — до ~150 строк кода, M — до ~300 (тесты среза в отдельном файле, ревьюер читает их по
линзе «держит ли»).

### Фаза К (78 веса, 15%)

- [ ] **T001 [K] `task_solutions`: типы, реестр, координатор**
  Контракт: владелец C0, C1, C2
  Файлы: courses/task_solutions/{__init__.py, types.py, registry.py, services.py, README.md, AGENTS.md, tests/__init__.py, tests/_fixtures.py, tests/test_types.py, tests/test_adapters.py, tests/test_dispatch.py}, docs/engineering/module-tiers.json, docs/engineering/module-boundaries.json
  Генерирует: module-map.md, module-graph.json
  Зависит от: —
  Приёмка: AC-6 (собственные контрактные тесты)
  Готово-когда: первый коммит (≤ 5 мин) — C0, `diff` блоков кода v4 §2.2–2.3 против `types.py`/`registry.py` пуст; `from_payload(to_payload(r)) == r`, с `ml_context` — `ValueError`; конфликт `source_kind`/`journal_kinds` — `ImproperlyConfigured`; `current_solution(s)` отдаёт `SolutionView` адаптера; неизвестный вид — `UnknownSolutionKind`; `solve`: предел — `DEADLINE`, исключение — `SOLVER_FAILED`; делегаты без модулей поднимают `ImportError` только при вызове; `check_module_boundaries.py`, `check_module_readme.py`, `gen_module_map.py --check` зелёные
  Риск: deep · Размер: M (~250 без переноса типов) · Тест-группа: banks · Оценка: вес 24 (5 + 19); запуск 18–25

- [ ] **T002 [K] Журнал: модель и 0295**
  Контракт: владелец C3, C4
  Файлы: courses/task_solutions/models.py, courses/migrations/0295_task_solution_version.py, courses/apps.py (блок импорта моделей — `shared`), courses/task_solutions/tests/_journal_fixtures.py, courses/tests/test_migration_0295.py
  Генерирует: tech-stack.md (голова миграций)
  Зависит от: — (подтягивает C0)
  Приёмка: AC-8
  Готово-когда: 0295 применяется и откатывается; `UPDATE`/`DELETE`/`TRUNCATE` — ошибка базы; уникальности §3.1; `make_version` пишет строку, которую читает модель; тесты краснеют при откате миграции; `gen_stack_facts.py --check` зелёный
  Риск: deep · Размер: M (~230) · Тест-группа: platform (правило T-1406) · Оценка: вес 24; запуск 18–28

- [ ] **T003 [K] Банк: порты, адаптер-каркас, заглушки, фасад**
  Контракт: владелец C5–C10, C17, C19
  Файлы: courses/exam_tasks/services.py (вставка двух функций), courses/exam_tasks/tests/test_answer_form.py, courses/task_solving/answers.py (заглушка + `RULE_TEXT`), courses/exam_solver/{services.py (блок фасада, включая `queue_steps`/`queue_step_write`), adapter.py, reference.py, solution_repoint.py, solution_views.py, urls.py, README.md (публичные имена)}, courses/exam_solver/tests/_solution_fixtures.py, courses/apps.py (блок регистрации — `shared`), docs/api/endpoints/staff-exam-tasks-solution.md, …-solution-get.md, docs/api/README.md (строки реестра), scripts/test_registry.py (`GROUP_RULES`, строка `banks`), docs/engineering/test-registry.json (исключение для `test_student_reports`)
  Генерирует: api-problems.json, TAGS.md, module-map.md, module-graph.json
  Зависит от: — (подтягивает C0)
  Приёмка: — (порты: свои тесты `answer_form` и `revision_task_ids`)
  Готово-когда: тесты `answer_form` и `revision_task_ids` зелёные и краснеют на откате; `adapter_for("exam_task")`, `solve` → `NOT_SUPPORTED`; маршрут отвечает 501; `gen_api_problems.py`: GET без 409, POST с 403/409/422 и только кодами v4 §2.7; `check_codes` зелёный без правок `response-codes.json`; `test_registry.py --check` зелёный; `check_docs_index.py` зелёный
  Риск: обычный · Размер: M (~300 и документы) · Тест-группа: banks · Оценка: вес 15; запуск 12–18

- [ ] **T004 [K] staff: клиентские швы, заглушки, раннер тестов**
  Контракт: владелец C12–C14, C16, C18; ключи C15
  Файлы: services/staff/utils/exam.ts (новые типы), services/staff/utils/examLabels.ts, services/staff/utils/examStepEdit.ts (новый), services/staff/utils/examStepEdit.test.cjs, services/staff/utils/examSolutionEdit.ts (каркас), services/staff/utils/examSolutionMerge.ts (сигнатура и заглушка), services/staff/app/(staff)/exam/_components/SolutionStepsEditor.tsx (заглушка), services/staff/app/(staff)/exam/queue/_components/ReferenceBlock.tsx (только импорт вынесенных правил), services/staff/package.json (`"test"`), .github/workflows/cicd.yml (шаг «staff: node --test», `setup-node 22`), docs/engineering/process-map.json (если потребует `check_process_map.py`)
  Генерирует: development-process.md (блок `process-map`)
  Зависит от: —
  Приёмка: — (вынос без смены поведения: `examStepEdit.test.cjs` на сегодняшнее поведение)
  Готово-когда: `tsc` и `build` staff зелёные; `npm test` в staff зелёный, включая `examQueueSelection.test.cjs` и `examTrustAlerts.test.cjs`; шаг CI прошёл на ветке; `gen_process_map.py --check` и `check_process_map.py` зелёные; в `examSolutionEdit.ts` импорт из `examStepEdit` только `import type`
  Риск: обычный · Размер: M · Тест-группа: staff-node, frontend (быстрые проверки) · Оценка: вес 15; запуск 12–18
  Оговорка: если `cicd.yml` в защищённых путях наставника, шаг CI ставит человек; до его слова строгий xfail staff проверяется `npm test` и пробным слиянием

### Приёмочные тесты `[T]` (с нуля, против `contracts.md`, строгий xfail)

Все `[T]` — `implementer`, без кода К. Ранг `[T]` равен рангу среза, который ждёт её при вливании.

| Задача | AC | Файл | Группа | Размер, вес | Запуск | Ждёт срез |
|---|---|---|---|---|---|---|
| T017 [T] US1 | AC-1…AC-5, AC-7 | courses/task_solutions/tests/test_acceptance_journal.py | banks | M, 15 | 12–18 | T005, T006 |
| T018 [T] US2 | AC-9…AC-11 | courses/tests/test_migration_0296_acceptance.py | platform | S, 10 | 8–12 | T008 |
| T019 [T] US3 | AC-12…AC-14 (случаи `rule` помечены) | courses/exam_solver/tests/test_task_reference_acceptance.py | banks | M, 15 | 12–18 | T009, **T029** (AC-14), T016 |
| T020 [T] US4 | AC-15…AC-17 | courses/exam_methodologist_queue/tests/test_task_steps_journal_acceptance.py | banks | S, 10 | 8–12 | **T010, T029** |
| T021 [T] US7 | AC-27, AC-28 | services/staff/utils/examStepEdit.acceptance.test.cjs | staff-node | S, 10 | 8–12 | T011 |
| T022 [T] US5 | AC-18…AC-21 | courses/exam_solver/tests/test_task_solution_acceptance.py | banks | M, 15 | 12–18 | T012 |
| T023 [T] US6 | AC-23…AC-25 | services/staff/utils/examSolutionEdit.acceptance.test.cjs | staff-node | M, 15 | 12–18 | **T013, T031** |
| T024 [T] US8 | AC-29 | courses/exam_solver/tests/test_task_repoint_acceptance.py | banks | S, 10 | 8–12 | T015 |
| T025 [T] US9 | AC-22 | courses/task_solving/tests/test_answer_rule_acceptance.py | banks | S, 10 | 8–12 | T016 |
| T026 [T] e2e | AC-30: подготовка и сценарии Н-1 §5.3, снимок «до» на старом коде | dev_images/n1/, e2e/n1/*.spec.ts, копия `recreate.sh` | e2e (trn, `serial`) | M, 15 | 15–25 | A1 |
| T027 [T] e2e | AC-31: сценарии Н-1б §3, 1–10, включая редактор (вверх, вниз, удалить, добавить); SQL подбора з1–з3; сухой прогон 1, 4, 6 на `page.route` | e2e/n1b/*.spec.ts | e2e | M, 15 | 15–25 | A2 |

### Хребет `[S]`

- [ ] **T005 [S] Журнал: чтение**
  Почему не срез: чтение одной таблицы пакетом, общее для T007, T009, T010, T012, T015
  Контракт: C1 (делегаты), C3, C4 · Файлы: courses/task_solutions/reads.py, courses/task_solutions/tests/test_reads.py
  Зависит от: T001, T002 · Приёмка: AC-4 (`step_id`), AC-7 — из T017
  Готово-когда: xfail AC-7 и части AC-4 сняты; число запросов не зависит от числа владельцев (`assertNumQueries`); `derived_steps` детерминирован
  Риск: deep · Размер: M · Тест-группа: banks · Оценка: вес 24; запуск 18–28

- [ ] **T006 [S] Журнал: единственный писатель**
  Почему не срез: единственный писатель с замком `pg_advisory_xact`, правилами 1–8 и выводом отметок
  Контракт: C1, C3, C4 · Файлы: courses/task_solutions/journal.py, courses/task_solutions/tests/test_journal.py
  Зависит от: T001, T002 **(r3: ребро на T003 снято — кодов нет)** · Приёмка: AC-1, AC-2, AC-3, AC-4 (семя), AC-5 — из T017
  Готово-когда: xfail сняты; два одновременных писателя (`TransactionTestCase`, как `test_steps.py:412`); `IntegrityError` → `VersionConflict`; вложенная транзакция; `hold` краснеет
  Риск: deep · Размер: M · Тест-группа: banks · Оценка: вес 24; запуск 18–28

- [ ] **T007 [S] Один писатель журнала кандидата**
  Почему не срез: точка «один писатель» для T010 и T012
  Контракт: C7 · Файлы: courses/exam_solver/step_edits.py (новые `write_candidate_solution`, `candidate_conflict_state`, внутренний путь записи; старый `edit_step` не трогается), courses/exam_solver/tests/test_task_candidate_journal.py
  Генерирует: module-map.md, module-graph.json
  Зависит от: T003, T005 (стек), T006 (стек) · Приёмка: — (держат T020, T022 через T010, T012)
  Готово-когда: запись списком целиком; семя из шагов кандидата; `subject_version = revision_id`; KSA из `allowed_step_ksa`; замок строки кандидата раньше замка журнала; 409 по голове; у кандидата без версий — `derived_steps`
  Риск: deep · Размер: S · Тест-группа: banks · Оценка: вес 16; запуск 13–20

- [ ] **T008 [S] Перенос 0296**
  Почему не срез: одна атомарная миграция данных со сверкой
  Контракт: C0 (`STEP_NAMESPACE` литералом), C3 · Файлы: courses/migrations/0296_task_solution_version_from_step_edits.py, courses/tests/test_migration_0296.py, docs/runbooks/0296-task-solutions.md
  Генерирует: tech-stack.md (голова миграций), TAGS.md (раннбук)
  Зависит от: T001, T002 · Вливание: **вместе с T010, T029, T011** (заморозка старой таблицы ломает старый `edit_step`)
  Приёмка: AC-9…AC-11 — из T018 · Готово-когда: xfail сняты; печатается итог сверки; раннбук по §3.2
  Риск: deep · Размер: M · Тест-группа: platform · Оценка: вес 24; запуск 18–28

### Срезы `[V]` (стартуют от влитого; рёбер `[V] → [V]` на старт нет)

- [ ] **T009 [V] US3: выдача решения банка**
  Контракт: C0, C1, C2, C5–C9 · Файлы: courses/exam_solver/reference.py (заглушка → тело), courses/exam_solver/tests/test_task_reference.py
  Генерирует: module-map.md, module-graph.json
  Зависит от: T001, T003, T005 · Приёмка: AC-12 (кроме `rule`), AC-13 — из T019
  Готово-когда: xfail сняты; ветки `steps_reach_answer` = `true/false/None` подменой; пакет равен поштучному чтению, число запросов — константа; шаги кандидата — голова журнала или `derived_steps`
  Риск: deep · Размер: M · Тест-группа: banks · Оценка: вес 24; запуск 18–28

- [ ] **T010 [V] US4 (сервер, запись и чтение очереди) — звено критического пути (r3)**
  Срез: «методолог правит шаг кандидата, правка ложится версией журнала» — от `queue_step_write` до головы журнала и обратно через `queue_steps`
  Контракт: C7 (`queue_steps`, `queue_step_write`), C12 · Файлы: courses/exam_solver/step_edits.py (`queue_steps` — чтение из журнала; `queue_step_write` — `edit_step` становится обёрткой над путём T007 с `base_seq`; снятие записи в старую таблицу), courses/exam_solver/tests/test_task_steps_journal.py (новый; группа `banks` по `GROUP_RULES`)
  Генерирует: module-map.md, module-graph.json
  Зависит от: T003, T007 · Вливание: вместе с T008, T029, T011
  Приёмка: AC-15, AC-16 — из T020
  Готово-когда: xfail AC-15, AC-16 сняты; правка по устаревшему `base_seq` → `VersionConflict`; после 0296 старая таблица не пишется (тест на отсутствие `INSERT`); `test_steps.py` (T029) зелёный на настоящих делегатах после пробного слияния партии
  Риск: deep · Размер: M (~170 кода + ~130 тестов; r2 держал здесь ~560) · Тест-группа: banks · Оценка: вес 24; запуск 18–28. **Стоит на пути: ранг максимальный, ревьюер берёт первым**

- [ ] **T029 [V] US4 (сервер, ручки очереди) (r3)**
  Срез: «ручка `/queue/steps` v2 отдаёт и принимает шаги журнала» — от HTTP до делегатов фасада
  Контракт: C7, C12, C17, C19 · Файлы: courses/exam_methodologist_queue/{views.py, services.py (`references()` через `solver.reference_solution`)}, courses/exam_methodologist_queue/tests/test_steps.py, docs/api/endpoints/staff-exam-queue-steps.md, …-steps-get.md
  Генерирует: TAGS.md; api-problems.json — если меняется набор отказов
  Зависит от: T002 (C4), T003 (C7, C17, C19) · Вливание: после T009 (AC-14); вместе с T008, T010, T011
  Приёмка: AC-14, AC-17 — из T019, T020
  Готово-когда: 17 старых сценариев `test_steps.py` проходят с новыми полями на `fake_queue_journal` и `fake_reference`; xfail AC-17 снят; после rebase на влитый T009 снят AC-14; на пробном слиянии партии сценарии зелёные без подмен
  Риск: обычный · Размер: M (~260) · Тест-группа: banks · Оценка: вес 15; запуск 12–18

- [ ] **T011 [V] US7 (клиент): форма шага очереди**
  Контракт: C12–C16 · Файлы: services/staff/app/(staff)/exam/queue/_components/ReferenceBlock.tsx, services/staff/utils/examStepEdit.ts (`mergeDraft` по полям), services/staff/utils/examStepEdit.test.cjs, services/staff/utils/exam.ts (переключение на новые типы, удаление `edit_id`/`base_edit_id`)
  Зависит от: T004 · Вливание: вместе с T008, T010, T029 · Приёмка: AC-27, AC-28 — из T021
  Готово-когда: xfail сняты; `tsc`, `build`, `npm test` зелёные; `data-testid` по C15
  Риск: обычный · Размер: M · Тест-группа: staff-node · Оценка: вес 15; запуск 12–18

- [ ] **T012 [V] US5 (сервер): запись решения задачи банка — звено критического пути**
  Контракт: C5–C10, C17 · Файлы: courses/exam_solver/solution_writes.py, courses/exam_solver/solution_views.py (заглушка → тело), courses/exam_solver/tests/test_task_solution_writes.py, docs/api/endpoints/staff-exam-tasks-solution{,-get}.md (примеры)
  Генерирует: TAGS.md, module-map.md, module-graph.json; api-problems.json — если меняется декоратор
  Зависит от: T003, T005, T007 · Вливание: после T009
  Приёмка: AC-18…AC-21 — из T022
  Готово-когда: xfail сняты; гонка «утверждение ответа под `lock_task` против записи карточки» → 409; `result_matches_answer` из `steps_reach_answer` (до T016 — `null`)
  Риск: deep · Размер: M · Тест-группа: banks · Оценка: вес 24; запуск 18–28

- [ ] **T013 [V] US6 (логика формы карточки) — deep (r3)**
  Контракт: C13, C14 · Файлы: services/staff/utils/examSolutionEdit.ts, services/staff/utils/examSolutionEdit.test.cjs
  Зависит от: T004 · Вливание: после T031 (редьюсер вызывает `mergeSolution` на 409) · Приёмка: AC-23, AC-25 — из T023
  Готово-когда: xfail AC-23, AC-25 сняты; правила приходят аргументом `rules`, импорт только `import type`; «несохранённые правки» при закрытии и смене задачи; `NeedsRight`; отправка: 409 → действие `conflict(theirs)`, 422 → поле ошибки
  Риск: **deep** · Размер: M (~270 кода) · Тест-группа: staff-node · Оценка: вес 24; запуск 18–28

- [ ] **T031 [V] US6 (слияние при 409, правила 1–7 Р-6) — deep (r3)**
  Срез: «методолог получил 409 и видит своё поверх чужого с пометками» — от `MergeResult` до флага `sameAsTheirs`
  Контракт: C14 (`mergeSolution`, `MergeResult`) · Файлы: services/staff/utils/examSolutionMerge.ts (заглушка → тело), services/staff/utils/examSolutionMerge.test.cjs
  Зависит от: T004 · Приёмка: AC-24 — из T023
  Готово-когда: xfail AC-24 сняты; на каждое правило 1–7 Р-6 по тесту и по обратному случаю; пометки `changed / deleted-by-other / added-by-other / new` по C15; «ваши правки уже есть в их версии» → `sameAsTheirs`; функция чистая (без React и `fetch`)
  Риск: **deep** · Размер: M (~270 кода) · Тест-группа: staff-node · Оценка: вес 24; запуск 18–28. Линза ревью: «каждое правило и обратный случай». Это тот класс работы, что в бейзлайне дал 4 круга

- [ ] **T014 [V] US6 (показ): раздел «Решение» в `TaskDrawer` (r3: без редактора)**
  Контракт: C10, C13–C15, C18, C6 · Файлы: services/staff/app/(staff)/exam/_components/SolutionSection.tsx (новый), services/staff/app/(staff)/exam/_components/TaskDrawer.tsx (счётчик перезагрузок, подтверждение закрытия и смены задачи), services/staff/app/(staff)/exam/exam.css
  Зависит от: T004 · Вливание: после T013 · Приёмка: AC-26 (показ; держит T027)
  Готово-когда: `tsc` и `build` зелёные; `data-testid` раздела по C15; редактор вставлен через C18 (на заглушке — список только для чтения); сценарии T027 1, 4, 6 проходят на `page.route`
  Риск: обычный · Размер: M (~380) · Тест-группа: staff-node · Оценка: вес 15; запуск 12–18

- [ ] **T030 [V] US6 (редактор списка шагов) (r3)**
  Контракт: C13–C15, C18 · Файлы: services/staff/app/(staff)/exam/_components/SolutionStepsEditor.tsx (заглушка → тело), services/staff/app/(staff)/exam/_components/solution-steps.css (новый, импорт из компонента — как `audit.css`)
  Зависит от: T004 · Вливание: после T013 (действия редьюсера) · Приёмка: AC-26 (редактор; держит T027, сценарии с перестановкой и удалением)
  Готово-когда: `tsc` и `build` зелёные; вверх, вниз, удалить, добавить после `n` (0 — в начало) отправляют действия C14; пометки по `data-mark`; `readOnly` прячет кнопки; `data-testid` по C15
  Риск: обычный · Размер: M (~400) · Тест-группа: staff-node · Оценка: вес 15; запуск 12–18

- [ ] **T015 [V] US8: склейка KSA**
  Контракт: C0, C1, C2, C7–C9 · Файлы: courses/exam_solver/solution_repoint.py (заглушка → тело), courses/task_solutions/catalog_merge.py (новый), courses/system_graph/merge_handlers.py (строка обработчика), courses/exam_solver/tests/test_task_solution_repoint.py, courses/task_solutions/tests/test_catalog_merge.py
  Генерирует: module-map.md, module-graph.json (ребро `system_graph → task_solutions`)
  Зависит от: T001, T003, T006 · Приёмка: AC-29 — из T024
  Готово-когда: xfail сняты; оба вида владельцев; порядок замков `(kind, id)`; конфликт — один повтор, затем громкий отказ; `edited_by` — служебный
  Риск: deep · Размер: M (~230) · Тест-группа: banks · Оценка: вес 24; запуск 18–28

- [ ] **T016 [V] US9: правило «одно число»**
  Контракт: C6 · Файлы: courses/task_solving/answers.py (тело и `RULE_TEXT`), courses/task_solving/tests/test_steps_reach_answer.py
  Зависит от: T003 · Вливание: после T025; после ответа соседней сессии по v6 §2.13 (вопрос уходит на шаге 1). Если к `[H]` ответа нет, решает человек
  Приёмка: AC-22 — из T025; случаи `rule` AC-12 — из T019
  Готово-когда: как в r2 (знаки сравнения, LaTeX, отрезок после последнего `=`/`≈`, каждый случай v6 §2.13 — тест, `hold` краснеет)
  Риск: deep · Размер: S · Тест-группа: banks · Оценка: вес 16; запуск 13–20

### Хвост и приёмки

- [ ] **T028 [H] Хвост и передача**
  Файлы: exam_solver/README.md, AGENTS.md, exam_methodologist_queue/README.md, task_solutions/README.md, журнал сессии, находки «хвост» дословно
  Генерирует: module-map.md, module-graph.json, tech-stack.md (если перенумерация), TAGS.md
  Зависит от: T008–T016, T029–T031
  Готово-когда: rebase на вершину `feature/course-pipeline-concept`; если голова цепочки миграций ушла, 0295 и 0296 перенумерованы, **все генераторы `shared-generated` перезапущены, их `--check` зелёные**; полный прогон `courses` (~30 мин) зелёный до передачи; сообщение соседней сессии (AC-32)
  Риск: обычный · Размер: S · Оценка: вес 10; работа 8–12 + прогон 30 (слот не держит)
- **A1 `acceptance`** — Н-1 на trn по T026 (AC-30). Старт: влиты T005–T011, T029 и T026. ~25 мин.
- **A2 `acceptance`** — Н-1б по T027 (AC-31). Старт: A1, влиты T012–T016, T030, T031. ~30 мин.

## 5. Граф и проба плана (§5)

```
C0 ─(подтянуть)─┬────────────────────────────────┐
T001 K ─────────┼─┬─> T005 S ─(стек)─┐            │
T002 K ─────────┴─┼─> T006 S ─(стек)─┴─> T007 S ──┬─> T010 V ══╗ партия {T008, T010, T029, T011}
                  │         └─────────────────────┼─> T015 V    ║
                  ├─> T008 S ═════════════════════╪═════════════╣
                  ├─> T029 V (от К; после T009) ══╪═════════════╣
T003 K ───────────┴─> T009 V ┄┄(вливание)┄┄┄┄┄┄┄┄┄┴─> T012 V ───╫─> T028 H ─> A1 ─> A2 ─> CI + полный прогон
                  └─> T016 V                                     ║
T004 K ──┬─> T011 V ═════════════════════════════════════════════╝
         ├─> T013 V deep ┄(после T031)
         ├─> T031 V deep
         ├─> T014 V ┄(после T013)
         └─> T030 V ┄(после T013)
T017–T027 [T] — с нуля, ранг = ранг ждущего среза
```

| Мера (§5) | Значение | Оценка |
|---|---|---|
| P = W/S | 5.47 | предупреждение при K = 4 и K = 5; красного нет |
| Занятость HLFET в веере | 3.1–3.3 из 4 | норма (≥ 0.8K = 3.2) на границе |
| Фаза К | 15%, глубина 1 | норма; 4 задачи К — отступление от «1–3» (r2 §8.1) |
| Пересечение `Файлы:` без пути | `apps.py`: T002 ∥ T003 — `shared` с названными блоками. С путём: `step_edits.py` T007 → T010; `exam_solver/services.py` только T003; заглушки T003/T004 → тело среза (`reference.py`, `solution_repoint.py`, `solution_views.py`, `answers.py`, `examSolutionMerge.ts`, `SolutionStepsEditor.tsx`); `exam.ts`, `examStepEdit.ts`, `examSolutionEdit.ts` T004 → T011/T013. **T014 ∥ T030: общих файлов нет** (у T030 свой `.css`). **T010 ∥ T029: общих файлов нет** (связь только через фасад C7) | норма |
| **Генерируемые файлы вне `shared-generated` (r3)** | 0. Пересечения по `Генерирует:` — §3.1 | норма |
| Шов без владельца или потребителя | 0 (C11 снят) | норма |
| `[V]` с `Сущность:` / `Миграция:` | 0 | норма |
| Покрытие `AC-n` → `[T]` → срез | 32 из 32 | норма |
| `[T]` зависит от кода К | 0 | норма |
| Ребро `[V] → [V]` на старт | 0. Порядок вливания: T009 ⇢ T012, T029; T031 ⇢ T013 ⇢ T014, T030 | норма |
| `(стек)` от `[K]` | 0 (C0 — контрактный коммит) | норма с поправкой r2 §9 п. 2 |
| deep или M на пути | T002, T006, T010, T012 — deep M; T007 — deep S. Больше M — **ни одной** | предупреждение: ставятся первыми по рангу |
| Тест-модули в `core` | 0 из 25 (новые `test_task_steps_journal`, `examSolutionMerge.test.cjs` проверены) | норма |
| `[T]` на стороне без раннера CI | 0 после T004 | норма |
| Партии CI по `Тест-группа:` | серверные — `banks` и `platform`, отпечаток грубый: каждая партия — полная проверка 15–28 мин | показывается |

## 6. Расписание по слотам (строгий K = 4, R = 3; номинальные веса, без отказов; `slots_r3.py`)

Формат: задача старт–сдача (влита).

| Слот | Задачи |
|---|---|
| 1 | T001 0–5 (C0) → T001 5–24 (34) → T019 24–39 (49) → T005 39–63 (73) → T024 63–73 (83) → T008 73–97 (138) → T012 97–121 (131) → T027 121–136 (146) → T028 138–148 (158) |
| 2 | T002 0–24 (34) → T022 24–39 (49) → T006 39–63 (73) → T007 63–79 (89) → T016 79–95 (105) → T010 95–119 (138) → T026 119–134 (144) |
| 3 | T017 0–15 (25) → T023 15–30 (42) → T031 30–54 (64) → T018 54–64 (73) → T025 64–74 (91) → T009 74–98 (107) → T011 98–113 (138) → T030 113–128 (138) |
| 4 | T004 0–15 (25) → T003 15–30 (40) → T013 30–54 (64) → T020 54–64 (81) → T021 64–74 (83) → T015 74–98 (113) → T014 98–113 (123) → T029 113–128 (138) |

- `[H]` влит на 158-й минуте, A1 — до 169, A2 — до 199. С последним CI и полным прогоном выходит
  ~249 мин без отказов.
- С разбросом и отказами (400 прогонов, строгий K = 4): до `[H]` 169 / 199 / 229 / 260 мин при
  p = 0 / 0.15 / 0.3 / 0.43; до «принята» 261 / 282 / 309 / 339.
- **Простой.** Слотов, стоящих без дела до 119-й минуты, нет. Звено пути T010 ждёт слот 6 мин
  (95 против 89): слоты заняты T016, T009, T015, T014. После ~136 слоты 2–4 пусты: хвост ждёт
  обязательную партию {T008, T010, T029, T011} (влита на 138) и `[H]`. Брать нечего, это ожидание
  хребта.
- Сегодняшний режим на том же графе (`block_r3.py`: слот держится до вливания, тесты пишет
  исполнитель, +40% к весу среза): 219 / 289 / 330 до `[H]`.

## 7. Тесты, документы, ревью, вливания

- **Тесты.** Приёмочные — в `[T]`, каждый в своём файле. Тест среза — в файле среза; у T010 и T031
  файлы новые. Общие фикстуры — в К: C2 (T001), C4 (T002), C17 и C19 (T003). `test_steps.py` правит
  только T029.
- **Документы.** Каждая ручка — свой файл в `docs/api/endpoints/`: заводит К, примеры дописывает
  срез. **(r3)** Генерируемые файлы (`TAGS.md`, `tech-stack.md`, `development-process.md`,
  `module-map.md`, `module-graph.json`, `api-problems.json`) пишет генератор, а не слияние (§3.1).
- **Ревью.** Пул R = 3, ревьюер берёт сданное по рангу пути: первыми T002, T006, T007, T010, T012.
  Линзы — как в r2. **(r3)** Новая линза: T031 и T013 — «каждое правило Р-6 и обратный случай»;
  T030 — «каждая кнопка отправляет действие контракта». Ревью по ходу на звеньях пути остаётся опытом
  с замером p (r2 §7) и в базовые цифры не входит.
- **Вливания.** Партии:
  - К — {T001, T002, T003, T004}: пробное слияние проверяет `apps.py`, генераторы перезапускаются один раз на партию;
  - обязательная — **{T008, T010, T029, T011}**;
  - далее {T005, T006, T007}, {T009, T016, T031, T013}, {T014, T030, T012, T015}, {T028}.

  Скрипт пробного слияния после слияния партии запускает генераторы из `shared-generated` и их
  `--check`. CI идёт по партиям; на пути — последняя партия и полный прогон.
- **Внешнее.** Ветка — от вершины `feature/course-pipeline-concept`. Вопрос по v6 §2.13 уходит на
  шаге 1. Вливание в ветку пайплайна делает чужая сессия.

## 8. Разбор: конфликты, простой, что не получилось

### 8.1. Отступления от `design.md` и снятые правила

1. **Четыре задачи К вместо 1–3** — как в r2.
2. **Контрактный коммит C0** — как в r2 (поправка §9 п. 2). Без неё +29…+35 мин.
3. **(r3) «Звено пути не ждёт слота» снято.** Замечание оценщика верно: при P < K правило — это
   скрытый K + 1. В узкой форме (≤ 1 сверх K, только `tl + bl − w = S`) оно даёт −3…−5 мин при
   p ≤ 0.15 и ничего при p ≥ 0.3: 229 против 229 и 261 против 260. Отказ звена пути вырастает в
   доработку, а доработка встаёт в очередь первой и без этого правила. Выигрыша меньше разброса,
   поэтому правила нет. Поправку r2 §9 п. 3 отзываю. Если нужно быстрее, это решение **K = 5**, и
   его надо считать как K = 5.

### 8.2. Сколько слотов

| K (R) | до `[H]`, p = 0 / 0.3 / 0.43 | до «принята», p = 0.3 | занятость | P против K |
|---|---|---|---|---|
| 3 (2) | 212 / 277 / 310 | ~361 | 2.6 | предупреждение (3 ≤ 5.47 < 6) |
| **4 (3)** | **169 / 229 / 260** | **~309** | 3.1–3.3 | предупреждение |
| 5 (4) | 158 / 216 / 249 | ~291 | 3.3–3.6 | предупреждение |

Совет: **K = 4 базово.** K = 5 проба больше не красит (P = 5.47), он даёт −11…−13 мин до `[H]` при
том же числе запусков. Цена — пятый одновременный rebase и пул ревью 4. Брать K = 5, если пул ревью 4
есть. K = 3 медленнее K = 4 на 17–21%.

### 8.3. Почему P ≈ 5, а не ≥ 8

Хребет `T002 → T006 → T007 → T010/T012` — четыре звена deep, 88 веса. Новые задачи круга 3 (T029,
T030, T031, deep T013) легли в веер, а не на путь: W вырос на 63, S остался 98, P поднялся с 4.83 до
5.47. Дальше P поднимается только укорочением хребта. Варианты из r2 §8.2 его не укорачивают. Вывод
прежний: **фича с новым ядром даёт P ≈ K, не 2K.**

### 8.4. Ожидаемые конфликты текста

- `apps.py`: T002 ∥ T003, разные блоки `ready()`.
- `step_edits.py`: T007 дописывает, T010 переделывает `edit_step` и чтение; путь есть.
- `ReferenceBlock.tsx`: T004 (импорт) → T011 (тело). `TaskDrawer.tsx` — только T014.
- **(r3) Генерируемые:** `TAGS.md` в обязательной партии (T008, T029) и в партии T012; `module-map`
  у 8 задач; `tech-stack.md` у T002 → T008 → T028 (между ними есть путь, но перенумерация в T028
  меняет строку головы). Все снимаются перезапуском генератора, ручного слияния нет.
- `cicd.yml`: только T004. Если путь защищён — человек.

### 8.5. Простой и ожидания вне исполнителей

Как в r2: один стенд trn (T026, A1, A2 подряд), CI последней партии и полный прогон на пути, риск
поправки контракта соседней сессией.

## 9. Поправки к `design.md` (предложение)

Пункты 1, 2, 4–8 — как в `f3-B-r2.md` §9. Изменения:

3. ~~Звено пути не ждёт слота~~ — **отозван** (§8.1 п. 3).
9. **(r3) §5, новая строка пробы: «генерируемый файл вне `shared-generated`».** `task_pairs.py plan`
   сверяет `Файлы:` каждой задачи с `files:` хуков проекта, которые запускают генератор
   (`.pre-commit-config.yaml`: хуки с `--check`/`--fill`). Каждый файл, который такой генератор
   пишет, должен стоять в `shared-generated` с командой генератора — иначе красное. Пересечения по
   `Генерирует:` проба только показывает. Довод: в r2 их было 4 файла у 9 задач, и ни один не попал в
   карту владения, потому что в `Файлы:` их никто не пишет — их пишет хук.
10. **(r3) §4, поле `Генерирует:`.** Список генерируемых файлов, которые задача меняет. Скрипт
    пробного слияния не сливает их, а перезапускает генератор.
11. **(r3) §4, предел размера применяется к коду, а не к числу задач.** Срез, у которого кода больше
    ~300 строк, режется по шву с контрактом (сигнатура и заглушка в К), даже если это добавляет
    задачу. Отказ ревью на L стоит дороже двух M: в бейзлайне 4 круга ревью дал именно такой класс
    работы.
