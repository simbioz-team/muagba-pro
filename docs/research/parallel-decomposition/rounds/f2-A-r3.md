# Фича 2 (шаг 8, теория ступени): разложение команды A, круг 3

Дата: 2026-11-24. Процесс описан в `design.md`: K → веер `[V]` → `[H]`, `[T]` идёт параллельно с K.
Входные данные: `feature-2-description.md`, `step8-spec-sanitized.md`, код `nastavnik_stage_1` на коммите
`053602900` (только `git show 053602900:…`), замечания оценщика к `f2-A-r2.md`.
Проверки лежат в `simF2A_r3/`:
- `plan.py` — граф (`ALT3K=1` — вариант «3 K» для сравнения);
- `probe.py` — проба §5;
- `sim3.py` — событийная модель r2 плюс CI: раннеры, общие с шагом 6, красные партии, три режима
  CI (`trail`, `hybrid`, `gate`, §8 п. 2);
- `trace.py` — детерминированное расписание (K видна потомкам после CI);
- `edges.py` — П-8/П-9 новых рёбер на `module-graph.json` и `module-tiers.json` базового коммита;
- `cls.py` + `names.txt` — группы тестов по `test_registry.classify`.

## 0. Итог в цифрах

| Мера | r2 | **r3** |
|---|---|---|
| Задач | 32 (K 5, `[T]` 6, `[V]` 18, `[S]` 2, `[H]` 1) | **32** (то же; состав K и трёх срезов изменён) |
| Задач deep | 10 | **10** |
| W | 550 мин | **550 мин** |
| S (критический путь) | 69 | **69**: ребра T003 → T004 нет (§1 п. 2), а не 78 со стеком |
| P = W/S | 7.97 | **7.97**: при N = 4 предупреждение (< 2N = 8), при N ≤ 3 норма |
| Фаза K | 102 мин, 18.5 % | **102 мин, 18.5 %**; 5 задач K, обоснование числа в §2.1 |
| Нарушений П-8/П-9 у новых рёбер (`edges.py`) | **7 циклов** (не проверялось) | **0** |
| Тестов в `core` | 0 (по старым путям) | **0** при новых путях (`cls.py`) |
| `[T]` вне своего пакета (`check_test_location`) | 4 файла | **0**: место по импортам (§5) |

Прогноз (`sim3.py`, 400 прогонов; ревью 8 мин; вливание c = 6 мин по одному; CI в режиме
**`hybrid`** — K видна потомкам только после зелёного CI своей партии, срезы вливаются без ожидания CI,
CI идёт следом на 3 раннерах, половина прогонов ждёт раннер шага 6 до 15 мин; приёмка +30):

| N / R | p = 0.25 | p = 0.43 | p = 0.61 (бейзлайн) | занято из N | $ (0.25 / 0.43 / 0.61) |
|---|---|---|---|---|---|
| **N = 4, R = 3** | 328 | **352 (5.9 ч)**, p90 387 | **380 (6.3 ч)**, p90 414 | 2.32–2.57 | 151 / 179 / 211 |
| N = 4, красных партий 15 % | — | 400 (6.7 ч), p90 463 | 429 (7.2 ч), p90 498 | 2.28–2.42 | +$17–20 |
| N = 4, c = 3 (`task_pairs.py merge`) | 308 | 337 | 365 | 2.50–2.67 | то же |
| N = 3, R = 2 | 352 | 390 (6.5 ч) | 427 (7.1 ч) | 2.13–2.26 | то же |
| **N = 2, R = 2 (делёж с шагом 6)** | 451 | **502 (8.4 ч)**, p90 542 | **562 (9.4 ч)**, p90 605 | 1.65–1.69 | то же |
| N = 5, R = 4 | 293 (c = 3) | 342 | 363 | 2.53–2.67 | то же |

Занятость здесь считается до последнего **проверенного** CI коммита, а в r2 — до последнего вливания.
Поэтому при той же работе цифра ниже: 2.43 против 2.87. На отрезке до последнего вливания она та же,
2.8–2.9 из 4.

Против бейзлайна (~10–10.5 ч, 600–630 мин): при N = 4 **−37…−44 %**, при 15 % красных партий
−29…−37 %; при N = 2 −6…−20 %. Цена $179–211 против ~$133, то есть ×1.35–1.6.

**Совет.** Если шаг 6 не занимает слоты, N = 4, R = 3. Если шаг 6 идёт одновременно, N = 2–3.
Пятого не ставить: при c = 6 он даёт −3…−5 %. Сначала дешеветь вливание (c = 3 даёт −4 %).

## 1. Ответы на замечания оценщика (круг 2)

| # | Замечание | Что сделано | Проверка |
|---|---|---|---|
| 1 | Два цикла П-8: `rung_theory` ↔ `topic_content`; `topic_content` → `course_pipeline` у T025 | **Принято, с иным разрезом первого.** (а) `rung_theory` — **ярус 2**: чистая функция и загрузчик нужд, который читает только ядро (`TaskClass`, `TaskClassKSA`, `LearningTask*` в `courses/models.py`) и `ksa_graph`/`course_structure` (ярус 2). `topic_content` в нём не импортируется. Состояние ступени (отстала, нет теории) считается в `topic_content/rung_view.py`: это ребро 3 → 2, и оно законно. (б) Откат переехал в `course_pipeline/rung_rollback.py`. Из `topic_content/services.py` его зовёт окно `topic_content/rung_listeners.py` (образец — `phase_listeners.py`). Регистрация в `CoursesConfig.ready` и `test_handler_registration.py` лежат в T004 | `edges.py`: r2 — 7 рёбер на цикле, r3 — 0 нарушений П-8 и П-9 на 15 новых рёбрах. Список модулей, которым запрещено импортировать `rung_theory` (иначе цикл), записан в `contracts.md` (C6) |
| 1а | Почему не окно и для `course_theory` | Окно провайдера скрывает зависимость: семь срезов звали бы `notify`-подобную функцию, а регистрация понадобилась бы в веб- и в Celery-процессе. Ярус 2 делает зависимость прямой. Окно нужно только там, где направление не развернуть: `topic_content` → `course_pipeline` | — |
| 2 | Скрытое ребро T003 → T004 по кодам | **Принято, ребро убрано без стека.** (а) Все новые коды заводит T003: `response-codes.json` (`codes`, `gate_blockers`, `detail_variants`), сгенерированный `problem_types.py` (`gen_problem_types.py`), `locale/ru/problems.json`, `api-problems.json`, выведение R-24. (б) Употребление `/problems/course-path-not-applicable` настоящее: маршруты-заглушки T003 на курсе без флага отказывают 422 `rung-material` (часть AC-15). (в) `gate_blockers` проверка `check-codes` на «active без употребления» не читает, она проверяет только список `codes`; полноту каталога держит `check_problem_catalog.py`. (г) T004 новых кодов не употребляет: `theory_mode` на старом пути отдаёт **существующий** `not-applicable` (спека, R-13, AC-15). (д) Регистрация правил в `gates/registry.py` переехала из T004 в T023, которая зависит от влитой T003 | S = 69, а не 78. Готово-когда у T003: `check_codes.py`, `gen_problem_types.py --check`, `check_problem_catalog.py` |
| 3 | IE-9/IE-10 лежат в `topic_content/models.py` (`EmbeddedItem.clean`, :661–676) | **Принято, проверено.** Правка `topic_content.topic.course_id` → `topic_content.course_id` перенесена в T001. У T022 в `embedded_items/services.py` осталось только определение ступени-владельца (`get_owning_task_class`) | `git show 053602900:…/topic_content/models.py`, строки 653–676 |
| 4 | Пять K при пределе 1–3 | **Обосновано расчётом, не уступлено** (§2.1). Содержимое K — 102 мин веса: 72 deep и 30 обычных. При потолке M (24 deep, 15 обычная) это не меньше 3 + 2 = 5 задач. Вариант «3 K» со слитыми L посчитан: +19 мин при N = 4 (371 против 352), S 89, P 6.1 | `ALT3K=1 sim3.py` |
| 5 | Противоречие по CI | **Принято.** Выбран режим `hybrid` (§8 п. 2), и модель теперь его считает. Буквальное правило «ветка перематывается после зелёного» (`gate`) стоит +30 мин при N = 4 (382 против 352) и +24 при N = 2 | `sim3.py`: таблица §7 |
| 6 | `expectedFailure` прячет `ImportError`/`FieldError` | **Принято.** Метод AC в имени несёт владельца: `test_ac<N>_t0xx_<что>`. Срез снимает отметку со **всех** своих методов, и тест обязан пройти. Ошибка теста — доклад и правка `[T]`, отметку не оставляют. Проверка в `Готово-когда:` механическая (`git grep`, §4). T032 проверяет, что отметок не осталось | §4, T032 |
| 7 | `[T]` одного пакета в `courses/tests/acceptance` | **Принято.** Файл `[T]` лежит там, куда его относит `check_test_location` по импортам. Одна история даёт до трёх файлов в разных пакетах, интеграционные остаются наверху. Имена файлов наверху подобраны так, чтобы не попасть в `core` | `cls.py`: 0 в `core`; `check_test_location.py` в `Готово-когда:` каждой `[T]` |
| 8 | Прогноз оценщика 5.8–6.6 ч при N = 4, 8.8–9.8 при N = 2 | Моя модель с CI: 5.9–6.3 ч при N = 4 и 8.4–9.4 при N = 2. Нижние края расходятся на 2–5 %, верхние совпадают с допуском 15 % красных партий | §0 |

## 2. Как резал (позиция A, что изменилось в r3)

1. **Контракт вместо кода, и контракт целиком в K.** Всё, во что упираются два среза и больше,
   лежит в K. Срез заполняет только свои новые файлы и свою запись в заранее заведённом месте.
2. **Граница модулей — часть контракта.** В r2 я проверял общие файлы, но не рёбра импорта. В r3
   каждое новое ребро прогнано `edges.py` по графу базового коммита. Правило для исполнителей
   записано в C6: `rung_theory` импортирует только ядро и ярусы ≤ 2, а ни один модуль из списка
   `edges.py` (`ksa_graph`, `course_structure`, `graph_invariants`, `saga`, `access_registry`…)
   не импортирует `rung_theory`. Это касается T024 (`graph_invariants/structure_gate.py`), T028 и
   T029 (`course_structure/…`) и T018 (`access_registry/preflight.py`). Им нужны только поля ядра
   и обратные связи (`Course.objects.filter(course_contents__pk=…)`, как это уже сделано для темы в
   `preflight._course_id_from_request`).
3. **Скрытые рёбра между K проверены по именам.** K не импортирует имён, которые заводит соседняя K:
   - T004 описывает `theory` в заглушках без аннотации `CourseTheory` (тип вписывает срез T014), иначе
     появилось бы ребро T002 → T004;
   - T003 не ссылается на модули T004;
   - T001 не ссылается на `rung_theory`.
4. **Загрузчик — K глубины 2** (довод r2 в силе): состояние ступени = f(нужды T002, носители T001).
5. **Срез идёт по сценарию насквозь.** Срезов 20 ≥ 2N, поэтому деления по сторонам нет.
6. **Генерация разрезана по швам конвейера, перенос — двумя параллельными срезами** (как в r2).
7. **`topic_content/services.py` — одна цепочка:** T004 (4 вызова окна) → T020 → T021 (стек).

### 2.1. Почему K пять, а не 1–3 (`Почему не одна:` для фазы целиком)

| Содержимое K | Вес | Почему K |
|---|---|---|
| Схема, миграции, инварианты, IE-9/IE-10, журнал | 24 (deep M) | 8 потребителей |
| Чистая функция состава, типы, `testing.fake_course_theory` | 24 (deep M) | 6 потребителей |
| Коды, доступ, маршруты-заглушки, документы ручек, каркас команды, `WRITER_FILES` | 15 (M) | 9 потребителей; реестры общие с шагом 6 |
| Точки вызова в горячих файлах, окно отката | 24 (deep M) | 6 потребителей |
| Загрузчик нужд и `course_theory` | 15 (M) | 7 потребителей; зависит от схемы и функции |

- **Нижняя граница числа K.** Работы K 102 мин: 72 deep и 30 обычной. Потолок задачи — M
  (`design.md` §4: «больше M — резать»), то есть 24 для deep и 15 для обычной. Отсюда минимум
  ⌈72/24⌉ + ⌈30/15⌉ = 3 + 2 = **5 задач**. Правило «1–3» и потолок M в этой фиче несовместимы, и я
  оставляю потолок M: размер диффа связан с долей отказов (42–44 % при нынешних задачах), а число K
  само по себе — нет.
- **Вынести часть K в срезы** значит вернуть рёбра между `[V]`: 7 потребителей загрузчика и 4 среза
  генерации ждали бы соседний срез. В r1 именно это и было, 6 срезов стояли готовыми.
- **Вариант «3 K» посчитан** (`ALT3K=1`): T001; T002+T005 (deep L, от T001); T003+T004 (deep L).

  | | 5 K (r3) | 3 K |
  |---|---|---|
  | S | 69 | 89 |
  | P | 7.97 | 6.08 |
  | N = 4, p = 0.43 / 0.61 | **352 / 380** | 371 / 402 |
  | N = 2, p = 0.43 / 0.61 | 502 / 562 | 498 / 555 |
  | $ | 179 | 172 |

  При N = 2 разница не больше 1 %, при N = 4 «3 K» медленнее на 5–6 %, и это при той же доле
  отказов. У L она выше, так что разница скорее занижена.
- **Что остаётся от правила.** Фаза K занимает 18.5 % W (≤ 20 %), задачи K параллельны, глубина 2
  только у T005 с `Почему не одна:`. Предложение к `design.md` записано в §11 п. 1.

## 3. Карта швов (`contracts.md`)

| Шов | Что | Владелец | Потребители |
|---|---|---|---|
| C1 | `TopicContent.carrier_purpose` (`theory`/NULL), инварианты R-2 в `clean()`/`save()` | T001 | T015 T018 T019 T020 T022 T028 T030 T031 |
| C2 | `TopicContent.topic` и `TopicContentGenerationError.topic` → `null=True` | T001 | T015 T018 T019 T022 T030 |
| C3 | `TopicContent.course` FK PROTECT, `related_name="course_contents"`, заполнение в миграции, `save()` берёт курс от темы или ступени; **IE-9 в `EmbeddedItem.clean` по `topic_content.course_id`** | T001 | T005 T018 T019 T022 T029 T030 T031 |
| C4 | `section_type='approach_map'`, `TopicContentSection.understanding_step` (1…5/NULL), снимок состава версии R-8 `composition_snapshot` | T001 | T005 T014 T015 T020 T021 |
| C5 | `RungTheoryMigrationRecord` в `topic_content/models.py`; две миграции, номер на вливании | T001 | T030 T031 |
| C6 | Пакет `rung_theory` (**ярус 2**): `types.py` (`CourseTheoryInputs`, `RungNeeds`, `CourseNeeds`, `RungTheory`, `CourseTheory`), `needs.compute`, `versions.active_version`, `testing.fake_course_theory` (без БД). **Импортирует только ядро и ярусы ≤ 2. Не импортируют его:** `ksa_graph`, `course_structure`, `graph_invariants`, `saga`, `access_registry`, `matching`, `billing` и остальные из `edges.py` | T002 | T005 T014 T023 T025 T026 T027 |
| C7 | `rung_theory/loader.course_needs(course) -> CourseNeeds` (ядро + `ksa_graph`, пакетно); `topic_content/rung_view.course_theory(course) -> CourseTheory` (нужды + действующие версии носителей + снимок → состояние, `Lag`) | T005 | T012 T014 T017 T023 T025 T026 T027 |
| C8 | `GET /api/v1/courses/{c}/rung-theory`: маршрут-заглушка (на флаге 501, без флага 422 `rung-material`), строка доступа, заготовка документа | T003 | T012 |
| C9 | Ручки R-30 (5 шт.) и импорт в носитель: маршруты-заглушки с той же развилкой, строки доступа, заготовки документов | T003 | T019 T022 |
| C10 | Чтение теории ступени учеником: маршрут в `lesson/urls.py`, строка доступа, заготовка документа | T003 | T026 |
| C11 | Коды: `/problems/course-path-not-applicable` (варианты `rung-material`, `topic-material`, `content-reading`) — в `codes` и `detail_variants`; 4 кода `gate_blockers` (`rung-theory-knowledge-missing`, `rung-theory-section-unmarked`, `rung-theory-outdated`, `rung-approach-map-missing`); выведение `reading-material-outdated` (R-24); `problem_types.py` пересобран, каталог `locale/ru/problems.json` полон | T003 | T018 T019 T022 T023 T029 |
| C12 | Конвейер: `generation/rung_pipeline.run(unit)`, `rung_request.build(unit, theory) -> MlRequest`, `rung_draft_writer.write(unit, draft, mode)`, `rung_billing.plan(unit, mode)`; DTO `RungUnit` (снимок — кортеж id знаний) и `RungTheoryDraft`; одна ветка в `generation/services.py` | T004 | T014 T015 T016 |
| C13 | Образец запроса и ответа `ml-llm` `kind=rung_theory`: JSON-файл в обоих сервисах | T004 | T013 T014 |
| C14 | Окно `topic_content/rung_listeners.py`: `register_material_changed_listener`, `notify_material_changed(tc, replaced_version_id)`, громкий отказ `RungListenerMissing`; 4 вызова в `services.py` (на флаге); слушатель-заглушка `course_pipeline/rung_rollback.on_material_change` повторяет прежнее поведение; регистрация в `CoursesConfig.ready`; строка в `test_handler_registration.py` (веб и Celery, П-16) | T004 | T025 |
| C15 | (снят: регистрация правил гейта переехала в T023, коды в C11) | — | — |
| C16 | `WRITER_FILES` сторожа `check_topic_content_writes.py`: `rung_draft_writer.py`, `rung_material.py`, `rung_theory_transfer.py`, `rung_theory_cleanup.py` | T003 | T015 T019 T030 T031 |
| C17 | `theory_mode` в сериализаторе `regenerate-content`; ветка `rung_modes.respond(request, tc, mode)` (заглушка); на старом пути 422 `not-applicable` (существующий код) | T004 | T017 |
| C18 | Каркас `migrate_rung_theory` (`--dry-run` по умолчанию, `--apply`, `--course`, `--backfill-course`, `--export-journal`) и заглушки двух модулей | T003 | T030 T031 |

## 4. Задачи

Вес считается так: 10 мин × 1.6 (deep) × 1.5 (M). Ранг — HLFET с ребром «`[T]` → срезы истории».

**Форма приёмочных тестов.**
- **Django:** `@unittest.expectedFailure` на каждом методе AC. Данные создаются внутри метода.
  Имена, которых ещё нет, импортируются внутри метода, потому что на момент `[T]` K не влита.
- **Jest:** `test.failing(...)`. **Playwright:** `test.fail()`.
- **Имя метода несёт владельца:** `test_ac<N>_t0xx_<что>`, у jest и Playwright — `ac<N> t0xx …`.
  Владельца назначает план (таблица AC в §5), `[T]` его только переписывает.
- **Кто снимает отметку.** Срез снимает её со **всех** своих методов, а не только с тех, что
  позеленели. Каждый такой метод обязан пройти. Если тест неверен (импорт, поле, ожидание), срез
  докладывает и правит его вместе с автором `[T]`, но отметку не оставляет. Так `ImportError` под
  `expectedFailure` не проживёт дольше своего среза.
- **Проверка в `Готово-когда:` каждого среза** (механика, `check.sh` её не делает):
  `git grep -n -B2 -E "def test_ac[0-9]+_t0xx_|ac[0-9]+ t0xx" -- '*step8*' | grep -cE "expectedFailure|\.failing|test\.fail\("` → 0.
- **Первая проверка T006:** зонд с `expectedFailure`, который проходит, обязан дать ненулевой код
  у `manage.py test` на версии Django проекта (unexpected success — провал).

Общий шаблон для всех `[V]`/`[S]`: тесты среза зелёные и краснеют на откате кода среза (вывод `hold`
приложен); отметки всех своих методов сняты, и проверка выше даёт 0; `check.sh` зелёный (в нём
`check_module_boundaries.py`, `check_test_location.py`, `check_codes.py`).

### Фаза K (T001–T004 стартуют сразу, T005 — после вливания и CI T001 и T002)

- [ ] **T001 [K] Носитель теории: схема, миграции, инварианты, IE-9/IE-10, журнал** — deep, M, 24
  Контракт: C1–C5. Файлы: `topic_content/models.py` (поля, `clean()`/`save()`, **`EmbeddedItem.clean`
  :661–676: IE-9 по `topic_content.course_id`, IE-10 без изменений**), `migrations/<N>_rung_theory_carrier.py`,
  `migrations/<N+1>_rung_theory_migration_record.py`, `topic_content/tests/test_carrier_invariants.py`,
  `topic_content/tests/test_migration_<N>_rung_carrier.py`, `topic_content/embedded_items/tests/test_embedded_ie9_course.py`.
  Не трогает `courses/models.py` (потолок 7138 строк) и `rung_theory`.
  Приёмка: AC-14 (своими тестами). Готово-когда: `test_carrier_theory_requires_rung`,
  `test_carrier_topic_null_on_flag`, `test_course_filled_from_topic`, `test_migration_backward_restores_topic`,
  `test_ie9_course_from_carrier_without_topic` зелёные и краснеют на откате `clean()`; `makemigrations --check` пуст.
  Тест-группа: content, banks. Номер миграции берётся после голов шага 6 и переименовывается на вливании.
- [ ] **T002 [K] Пакет `rung_theory` (ярус 2): чистая функция состава** — deep, M, 24
  Контракт: C6. Файлы: `rung_theory/__init__.py`, `types.py`, `needs.py`, `versions.py`, `testing.py`,
  `AGENTS.md`, `README.md`, `tests/test_knowledge_needs.py`, `tests/test_knowledge_versions.py`,
  `docs/engineering/module-tiers.json` (`rung_theory` на **ярус 2**).
  Приёмка: AC-1, юнит-часть AC-2. Готово-когда: `test_progression_example_pr2`, `test_entry_point_knowledge_excluded`,
  `test_role_override_moves_need`, `test_exactly_one_rung_per_knowledge`, `test_active_version_rule` зелёные,
  без БД, краснеют на откате `needs.py`; `check_module_boundaries.py` зелёный.
  Тест-группа: graph.
- [ ] **T003 [K] Регистрация: коды, доступ, маршруты-заглушки, документы ручек, каркас команды, `WRITER_FILES`** — обычный, M, 15
  Контракт: C8–C11, C16, C18. Файлы: `config/response-codes.json` (`codes`, `gate_blockers`, `detail_variants`,
  выведение R-24), `config/problem_types.py` (только `gen_problem_types.py`), `config/locale/ru/problems.json`,
  `config/api-problems.json`, `access_registry/registry.py`, `topic_content/urls.py`,
  `topic_content/views_rung_theory.py`, `views_rung_material.py`, `views_rung_import.py`,
  `lesson/urls.py`, `lesson/views_rung_theory.py` (заглушки: без флага 422 `course-path-not-applicable`
  / `rung-material`, на флаге 501), `topic_content/rung_material.py`, `rung_theory_transfer.py`,
  `rung_theory_cleanup.py` (заглушки), `scripts/check_topic_content_writes.py` (`WRITER_FILES`),
  `management/commands/migrate_rung_theory.py` (каркас), 8 заготовок `docs/api/endpoints/*.md`,
  `docs/meta/process/rung-theory-migration-runbook.md` (заготовка), 9 строк `docs/TAGS.md`,
  `courses/tests/test_step8_content_routes_access.py`.
  Готово-когда: `test_every_rung_route_resolves`, `test_every_rung_route_has_access_row`,
  `test_rung_routes_off_flag_422_rung_material` зелёные; `check_codes.py`, `gen_problem_types.py --check`,
  `check_problem_catalog.py`, `check_api_doc_coverage.py`, `check_docs_index.py` зелёные;
  `migrate_rung_theory --dry-run` выходит с 0. Тест-группа: content.
  *Почему не одна с T004:* реестры механичны (Sonnet), хуки в горячих файлах требуют суждения (Opus);
  слитая была бы deep L (§2.1). Если дифф больше 300 строк, координатор режет её по шву «коды и доступ» |
  «маршруты, документы, команда». Обе половины — K без рёбер между собой.
- [ ] **T004 [K] Точки вызова в горячих файлах и окно отката** — deep, M, 24
  Контракт: C12–C14, C17. Файлы: `generation/services.py` (одна ветка), `generation/rung_pipeline.py`,
  `rung_request.py`, `rung_draft_writer.py`, `rung_billing.py` (заглушки и DTO), `topic_content/services.py`
  (только 4 вызова `notify_material_changed`), `topic_content/rung_listeners.py`, `course_pipeline/rung_rollback.py`
  (слушатель-заглушка), `courses/apps.py` (регистрация в `CoursesConfig.ready`), `courses/tests/test_handler_registration.py`
  (строка нового окна), `topic_content/serializers.py` (`theory_mode`), `topic_content/views.py`
  (ветка `rung_modes.respond`), `topic_content/rung_modes.py` (заглушка), образец C13 в
  `topic_content/generation/fixtures/rung_theory_ml.json` и `ml-llm/tests/fixtures/rung_theory_ml.json`,
  `topic_content/tests/test_rung_hooks_content.py`, `topic_content/generation/tests/test_rung_pipeline_stub.py`.
  Не импортирует `rung_theory` и новых кодов не употребляет.
  Готово-когда: `test_hooks_keep_old_behaviour`, `test_listener_missing_fails_loud`,
  `test_rung_listener_registered_web_and_celery`, `test_theory_mode_old_path_422_not_applicable`,
  `test_pipeline_stub_roundtrip_c13` зелёные; `check_module_boundaries.py` зелёный.
  Тест-группа: content, platform. Линза ревью: «в заглушках нет логики, сигнатуры хватит срезам».
- [ ] **T005 [K] Загрузчик нужд и состояние ступени** — обычный, M, 15 · Зависит от: T001, T002
  *Почему не одна:* состояние = f(нужды T002, носители T001); слитая K вышла бы deep L (§2.1).
  Контракт: C7. Файлы: `rung_theory/loader.py`, `rung_theory/tests/test_knowledge_loader.py`,
  `topic_content/rung_view.py`, `topic_content/tests/test_rung_view.py`, `rung_theory/README.md` (раздел загрузчика).
  Готово-когда: `test_loader_query_count_flat`, `test_state_lag_from_snapshot`, `test_course_theory_matches_fake`
  зелёные; `check_module_boundaries.py` зелёный (`rung_theory` не импортирует `topic_content`).
  Тест-группа: graph, content.

### Приёмочные тесты `[T]` (старт в окне K, зависят только от `contracts.md` и спеки)

Место файла назначает `check_test_location` по импортам. Файл, который тянет один пакет, лежит в
этом пакете; файл, который тянет несколько, — наверху. Ниже указано **ожидаемое** место. Окончательное —
по выводу проверки, и `check_test_location.py` стоит в `Готово-когда:` каждой `[T]`.

| Задача | История | AC | Вес | Файлы (ожидаемое место) | Группа |
|---|---|---|---|---|---|
| T006 | US1 состав, «Контент», генерация, деньги | AC-2, AC-3, AC-6, AC-8, AC-19, AC-22 | M 15 | `topic_content/tests/test_step8_us1_content.py`, `topic_content/generation/tests/test_step8_us1_generation.py`, `courses/tests/acceptance/step8/test_step8_us1_billing.py` (`topic_content` + `billing`), `frontend/tests/e2e/step8/rungContent.spec.ts` | content, billing |
| T007 | US2 материал ступени без темы | AC-4, AC-15, AC-16, AC-17, AC-18 | M 15 | `topic_content/tests/test_step8_us2_material.py`, `courses/tests/acceptance/step8/test_step8_us2_access.py` (`topic_content` + `access_registry`), `e2e/step8/rungEditor.spec.ts` | content, platform |
| T008 | US3 гейты и откат | AC-9, AC-20, AC-21 | S 10 | `course_pipeline/tests/test_step8_us3_gates.py`, `courses/tests/acceptance/step8/test_step8_us3_gate_rollback.py` (`topic_content` + `course_pipeline`) | saga |
| T009 | US4 уроки и трек | AC-12 | S 10 | `lesson/tests/test_step8_us4_mode_a.py`, `dialogue/tests/test_step8_us4_material_b.py`, `track_manage/tests/test_step8_us4_track.py` | lessons, graph |
| T010 | US5 структура и окно ступени | AC-10, AC-11 | S 10 | `task_classes/tests/test_step8_us5_structure.py`, `e2e/step8/rungModal.spec.ts` | banks, ui |
| T011 | US6 перенос | AC-5, AC-13 | S 10 | `courses/tests/acceptance/step8/test_step8_us6_migrate_content.py` (команда — потребитель верхнего уровня) | content |

Все `[T]` выполняет `implementer` (обычный). Ревью: «каждый AC покрыт, тест бьёт обе стороны, данные
в методе, владелец в имени совпадает с таблицей §5». AC-7 (качество вживую) не тест: это приёмка US1
на `cp-*`.

### Веер (стартует от влитых предков; K — от проверенных CI; стека нет, кроме T020 → T021)

**US1: состав, «Контент», генерация, деньги**
- [ ] **T012 [V] «Контент» по ступеням: ручка `rung-theory` и вкладка** — обычный, M, 15 · T003 T005
  Файлы: `topic_content/views_rung_theory.py` (тело), `docs/api/endpoints/course-rung-theory.md` (тело),
  `topic_content/tests/test_rung_theory_endpoint.py`, `frontend/.../tabs/RungContentTab.tsx`, `tabs/ContentTab.tsx`
  (ветка по флагу), `utils/rungTheory.ts`, `types/rungTheory.ts`, `__tests__/components/RungContentTab.test.tsx` ·
  Приёмка: AC-2, AC-22 (показ) · Готово-когда: `test_rung_theory_five_roles`, `test_rung_theory_states_match_composition`,
  jest `renders six rung states`, `old course keeps topic tab` · Группа: content.
- [ ] **T013 [V] Промпт теории ступени в `ml-llm`** — обычный, M, 15 · T004
  Файлы: `ml-llm/app/prompts/topic_content/plan_system_rung_theory.md`, `text_system_rung_theory.md`, схема ответа
  `kind=rung_theory`, `ml-llm/tests/test_topic_content_rung_theory_prompt.py` · AC-3 (форма, тестами `ml-llm`) ·
  Готово-когда: `test_rung_theory_response_matches_c13_sample`, `test_step4_has_question_and_rule` · Группа: ml-llm.
- [ ] **T014 [V] Запрос генерации: единица, план, режимы** — обычный, M, 15 · T004 T005
  Файлы: `generation/units.py`, `plan.py`, `dispatch.py` (+ читатели :354/:360), `rung_request.py` (тело и аннотация
  `CourseTheory`), `generation/tests/test_rung_theory_generate.py` · AC-3, AC-6 (`Lag`), AC-19 (блок карты) ·
  Готово-когда: `test_generate_sections_by_c_and_map`, `test_complete_only_lag_readonly_accepted`, `test_map_only_map`,
  `test_ref_in_context`, `test_step4_two_lexical_nodes` · Группа: content.
- [ ] **T015 [V] Запись черновика и слияние под замком** — deep, M, 24 · T001 T003 T004
  Файлы: `generation/rung_draft_writer.py` (тело), `generation/tests/test_rung_theory_merge.py` · AC-3, AC-6, AC-19 ·
  Готово-когда: `test_snapshot_r8_per_mode`, `test_complete_copies_active_version_under_lock`,
  `test_concurrent_edit_no_lost_sections`, `test_nothing_to_do_200_no_unit`, `test_topic_null_course_set` · Группа: content.
- [ ] **T016 [V] Деньги и автопуть** — deep, M, 24 · T004
  Файлы: `generation/rung_billing.py` (тело), `course_pipeline/auto_pipeline.py` (**общий с шагом 6**),
  `generation/tests/test_rung_theory_billing.py`, `course_pipeline/tests/test_auto_pipeline_rung.py` · AC-8 ·
  Готово-когда: `test_reserve_ge_fact_each_mode`, `test_zero_calls_without_click`, `test_autopath_never_complete` ·
  Группа: billing, saga.
- [ ] **T017 [V] Кнопки генерации и ответ ручки по режимам** — обычный, M, 15 · T003 T004 T005
  Файлы: `topic_content/rung_modes.py` (тело), `topic_content/tests/test_rung_modes_endpoint.py`,
  `frontend/.../content/RungTheoryActions.tsx`, `utils/rungTheoryGeneration.ts`, `__tests__/components/RungTheoryContentButtons.test.tsx` ·
  AC-22 (кнопки), AC-6 («нечего делать»), AC-15 (`theory_mode` на старом пути) · Готово-когда:
  `test_modes_generate_complete_map_dispatch`, `test_nothing_to_do_returns_200`, jest `pack button shows count`,
  `rereads after response` · Группа: content.

**US2: материал ступени без темы**
- [ ] **T018 [V] Доступ, отказы по пути, граф курса без темы** — deep, M, 24 · T001 T003 T004
  Файлы: `access_registry/preflight.py` (курс по `Course.objects.filter(course_contents__pk=…)`, **без импорта
  `topic_content` и `rung_theory`**, ярус 1), `topic_content/views.py` (проверки курса :1035/:1149/:1206, `topic_id` :270,
  отказы R-31 `topic-material`), `task_classes/views.py`, `course_graph_editor/read.py`,
  `access_registry/tests/test_preflight_rung_material.py`, `courses/tests/test_pipeline_path_refusals.py`,
  `course_graph_editor/tests/test_read_without_topic.py` · AC-4, AC-13 (предполётная), AC-15 (`topic-material`), AC-17 ·
  Готово-когда: `test_five_roles_each_route`, `test_topic_route_on_flag_422`, `test_old_material_same_course`,
  `test_graph_keys_rung_not_none` · Группа: platform, structure, content. Ребро T004 → T018 по `views.py`.
- [ ] **T019 [V] Материал ступени в редакторе: ручки R-30 и `ContentEditorDrawer`** — deep, M, 24 · T001 T003
  Файлы: `topic_content/rung_material.py` (тело), `views_rung_material.py` (тело, развилку T003 не снимать),
  4 тела `docs/api/endpoints/course-topic-content-*.md`, `topic_content/tests/test_rung_material_endpoints.py`,
  `frontend/.../content/ContentEditorDrawer.tsx`, `utils/rungMaterial.ts`, `__tests__/components/ContentEditorDrawerRung.test.tsx` ·
  AC-15 (`rung-material`), AC-17 (R-30), AC-18 · Готово-когда: `test_create_theory_under_rung_lock`,
  `test_versions_switch_by_group`, `test_name_and_place_from_carrier`, jest `drawer uses course routes on flag`,
  `occ conflict keeps unsaved` · Группа: content.
- [ ] **T020 [S] Разделы: карта подхода и знания раздела** — обычный, M, 15 · T001 T004
  *Почему не срез:* `topic_content/services.py` (2 703 строки) — один владелец за раз.
  Файлы: `topic_content/services.py` (раздел, читатели :606/:835/:1416), `topic_content/serializers.py` (поля раздела),
  `topic_content/tests/test_section_rules_rung.py`, `frontend/.../content/SectionsList.tsx`, `content/SectionKnowledgePicker.tsx`,
  `__tests__/components/SectionKnowledgePicker.test.tsx` · AC-16, AC-18 (знания) · Готово-когда:
  `test_second_approach_map_422_already_taken`, `test_map_on_backing_not_applicable`,
  `test_knowledge_ids_must_be_course_knowledge`, jest `picker lists course knowledge` · Группа: content.
- [ ] **T021 [S] Форк и пересборка без потери разметки** — обычный, M, 15 · T001; T020 (стек)
  Файлы: `topic_content/services.py` (`_carry_…` :1069–1146, форк :2332/:2350, пересборка :1637/:1942),
  `topic_content/tests/test_fork_rebuild_markup.py` · AC-16 · Готово-когда: `test_fork_keeps_knowledge_and_step_both_paths`,
  `test_rebuild_keeps_map` · Группа: content. `hold` откатывает только диапазоны строк T021.
- [ ] **T022 [V] Импорт в носитель и вставные вопросы без темы** — обычный, M, 15 · T001 T003
  Файлы: `topic_content/passthrough.py`, `views_rung_import.py` (тело), `docs/api/endpoints/course-topic-content-populate.md` (тело),
  `topic_content/embedded_items/services.py` (**только** `get_owning_task_class*` по ступени носителя; IE-9/IE-10 — T001),
  `topic_content/coverage/check.py`, `coverage/gate.py`, `topic_content/tests/test_import_without_topic.py`,
  `embedded_items/tests/test_embedded_without_topic.py`, `coverage/tests/test_coverage_knowledge_rung.py` · AC-4, AC-18 ·
  Готово-когда: `test_import_topic_null_group_from_carrier`, `test_question_foreign_knowledge_refused`, `test_coverage_by_course` ·
  Группа: documents, banks, content.

**US3: гейты и откат**
- [ ] **T023 [V] Гейт 2 на флаге: четыре правила и реестр** — обычный, M, 15 · T003 T005
  Файлы: `course_pipeline/gates/rules_rung_theory.py` (новый; правила читают `rung_view.course_theory` сами,
  кэш по курсу в файле, **`facts.py` не трогает**), `course_pipeline/gates/registry.py` (4 правила
  `bind_on_path(pipeline_v2=True)` и перепривязка правил R-23 на `pipeline_v2=False`; **общий с шагом 6**),
  `course_pipeline/tests/test_rules_rung_theory.py`, `course_pipeline/tests/test_gate2_flag_rules.py` · AC-9 ·
  Готово-когда: `test_knowledge_without_section_blocker`, `test_section_without_knowledge_warning`, `test_lag_warning`,
  `test_no_map_blocker`, `test_fork_without_section_blocker`, `test_old_rules_silent_on_flag`, `test_old_rules_fire_without_flag` ·
  Группа: saga.
- [ ] **T024 [V] Старые проверки вне реестра и `ksa-task-class-inadequate` на флаге** — обычный, M, 15 · —
  Файлы: `graph_invariants/structure_gate.py` (ярус 2, **без импорта `rung_theory`**), `task_classes/readiness.py`,
  `course_pipeline/gates/facts.py`, `course_pipeline/gates/rules_structure.py` (`_ksa_task_class_inadequate*` :662–772,
  `_a_lines_missing_content_reading`; **общий с шагом 6**), `task_classes/gate_rules.py`,
  `course_pipeline/tests/test_ksa_inadequate_flag.py`, `task_classes/tests/test_gate_rules_flag.py` · AC-9 (`_a_lines…`), AC-21 ·
  Готово-когда: `test_ksa_inadequate_on_flag_by_rung`, `test_a_lines_reading_off_on_flag`, `test_old_checks_fire_without_flag` ·
  Группа: saga. Предков нет: нужен только `Course.pipeline_v2`. По рангу T024 идёт рано, но вливается после своей `[T]` T008.
- [ ] **T025 [V] Откат гейта 2 по условию** — обычный, M, 15 · T004 T005
  Файлы: `course_pipeline/rung_rollback.py` (тело слушателя), `course_pipeline/gating.py`, `saga/gate_backing.py`
  (**общий с шагом 6**; ярус 2, решение передаётся аргументом), `course_pipeline/tests/test_rung_rollback.py`,
  `saga/tests/test_reopen_rung_theory.py` · AC-20 · Готово-когда: `test_rollback_only_when_coverage_lost`,
  `test_complete_approval_no_rollback` · Группа: saga. В `topic_content` не пишет: вызов идёт через окно C14.

**US4: уроки и трек**
- [ ] **T026 [V] Урок А по ступени и «Опирается на»** — обычный, M, 15 · T003 T005
  Файлы: `lesson/mode_a/services.py` (:101–176, :238; **общий с шагом 6**), `topic_content/lesson_modes.py`, `lesson/serializers.py`,
  `lesson/views_rung_theory.py` (тело), `docs/api/endpoints/lesson-rung-theory.md` (тело), `lesson/mode_a/tests/test_mode_a_rung.py`,
  `frontend/.../mode-a/LessonModeA.tsx`, `mode-a/RungRefs.tsx`, `utils/lessonRungTheory.ts`, `__tests__/components/LessonModeARefs.test.tsx` ·
  AC-12 (урок А) · Готово-когда: `test_mode_a_by_rung_on_flag`, `test_refs_point_to_first_rung`,
  `test_student_reads_theory_by_course_access`, jest `refs link to rung theory` · Группа: lessons.
- [ ] **T027 [V] Урок Б, контекст генерации задач, банк диагностики, трек** — обычный, M, 15 · T005
  Файлы: `topic_content/rung_sections.py` (`sections_for_knowledge`; в `topic_content`, потому что читает разделы),
  `dialogue/material_b.py`, `topic_content/generation/context.py`, `diagnostic_bank/payload.py`, `track_manage/services.py`,
  `track_manage/planner.py`, `topic_content/tests/test_rung_sections.py`, `dialogue/tests/test_material_b_rung.py`,
  `track_manage/tests/test_track_rung_theory.py`, `diagnostic_bank/tests/test_payload_rung.py` · AC-12 (урок Б, трек) ·
  Готово-когда: `test_material_b_takes_needed_rungs_theory_and_map`, `test_task_gen_context_from_rungs`,
  `test_diag_payload_rung_sections`, `test_track_on_flag_no_reading_class` · Группа: lessons, graph, banks, content.

**US5: структура и окно ступени**
- [ ] **T028 [V] Перегенерация структуры** — deep, M, 24 · T001
  Файлы: `task_classes/rung_layout.py`, `structure_gen/skeleton.py`, `task_classes/rung_layout_db.py` (:503, :706, :1137, :1677),
  `task_classes/rung_regen.py`, `task_classes/tests/test_rung_regen_theory.py` · AC-10 (перегенерация) ·
  Готово-когда: `test_regen_carries_theory_by_key`, `test_skeleton_no_content_reading_on_flag`; `check_course_structure_writes.py`
  зелёный · Группа: banks. Общие с шагом 6 каталоги `course_structure/` и `task_classes/`; `course_structure` не импортирует ни `topic_content`, ни `rung_theory`.
- [ ] **T029 [V] Окно ступени без «Тип» и «+ Теория», удаление с теорией → парковка** — обычный, M, 15 · T001 T003
  Файлы: `task_classes/services.py` (:173, :786, :1893; **общий с шагом 6**), `course_structure/deletion.py` (теория по обратной
  связи `TaskClass`, без импорта `topic_content`), `topic_content/parent_deletion.py`, `course_structure/tests/test_deletion_parking.py`,
  `task_classes/tests/test_content_reading_refusal.py`, `frontend/.../structure/TaskClassModal.tsx` (**общий с шагом 6**),
  `structure/TopicTreePanel.tsx`, `__tests__/components/TaskClassModalRung.test.tsx` · AC-10 (удаление), AC-11 ·
  Готово-когда: `test_content_reading_on_flag_422`, `test_delete_rung_with_approved_theory_parks`, jest `no type field on flag`,
  `no add theory button` · Группа: banks, structure.

**US6: перенос**
- [ ] **T030 [V] Перенос версий: `rung_theory_transfer`, журнал, отказы по курсу** — deep, M, 24 · T001 T003
  Файлы: `topic_content/rung_theory_transfer.py` (тело), `management/commands/migrate_rung_theory.py` (только отчёт `--dry-run`),
  `topic_content/tests/test_rung_theory_transfer.py` · AC-5 · Готово-когда: `test_apply_moves_versions_bytes_equal`,
  `test_second_apply_zero_changes`, `test_dry_run_writes_nothing`, `test_refuses_course_with_student`, `test_no_llm_ledger_rows` ·
  Группа: content.
- [ ] **T031 [V] Оболочки, `--backfill-course`, выгрузка журнала, раннбук** — deep, M, 24 · T001 T003
  Файлы: `topic_content/rung_theory_cleanup.py` (тело; удаление через дверь `course_structure`, `deletion.py` не правится),
  `docs/meta/process/rung-theory-migration-runbook.md` (тело), `topic_content/tests/test_rung_theory_cleanup.py`,
  `topic_content/tests/test_backfill_content_course.py` · AC-5, AC-13 · Готово-когда: `test_empty_shell_removed_with_snapshot`,
  `test_protected_shell_kept_with_reason`, `test_backfill_fills_null_course`, `test_export_rows_equal_count` · Группа: content.

**Хвост**
- [ ] **T032 [H] Хвост и документы замысла** — обычный, M, 15 · все `[V]`/`[S]`
  Файлы: `docs/INDEX.md`, `docs/TAGS.md` (поднять `updated`), `topic_content/README.md` (новые файлы среза), журнал проекта,
  `ADR-099` (D9, О-6), журнал концепции, строка шага 8 в плане, находки «хвост» дословно, сверка читателей по теме.
  Готово-когда: `check_docs_index.py`, `check_doc_links.py` зелёные; **отметок не осталось**:
  `git grep -nE "expectedFailure|test\.failing|test\.fail\(" -- '*step8*'` пуст; все методы `test_ac*`
  из таблицы §5 существуют (`git grep -c` по каждому имени ≥ 1).

## 5. Тесты и документы: где что пишется

**Владельцы методов AC** (назначает план, `[T]` переписывает в имена):

| AC | Владельцы | AC | Владельцы |
|---|---|---|---|
| AC-1, AC-14 | K (T002, T001), свои тесты | AC-12 | T026 (урок А), T027 (урок Б, трек) |
| AC-2 | T012 | AC-13 | T018 (предполётная), T031 (`course IS NULL` = 0) |
| AC-3 | T014 (запрос), T015 (разделы), T017 (кнопка); форма — T013 в `ml-llm` | AC-15 | T018 (`topic-material`), T019 (`rung-material`), T017 (`theory_mode`) |
| AC-4 | T018, T022 | AC-16 | T020, T021 |
| AC-5 | T030, T031 | AC-17 | T018, T019 |
| AC-6 | T014, T015, T017 | AC-18 | T019, T020, T022 |
| AC-8 | T016 | AC-19 | T014, T015 |
| AC-9 | T023 (новые и R-23), T024 (`_a_lines…`) | AC-20 | T025 |
| AC-10 | T028, T029 | AC-21 | T024 |
| AC-11 | T029 | AC-22 | T012, T017 |

- **Тесты среза** лежат в каталоге модуля среза, `[T]` — по импортам (§4). Общих `conftest`/фикстур нет,
  проект на `unittest`, данные строятся в методе через `courses/tests/_course_fixtures.py`.
- **Имена тестов** прогнаны через `classify` (`simF2A_r3/cls.py`, 56 модулей). В `core` ноль, поэтому
  `test-registry.json` никто не трогает. Имена наверху несут слово группы: `…content_routes_access`,
  `…us3_gate_rollback`, `…us6_migrate_content`.
- **Документы ручек:** заготовки с frontmatter и строки `TAGS.md` делает T003, тело — срез ручки без
  правки frontmatter, `updated` поднимает T032.
- **Документы модуля:** `rung_theory/AGENTS.md`, `README.md` пишет T002, раздел загрузчика — T005.
  Строки новых файлов в `topic_content/README.md` пишет T032.

## 6. Карта владения: горячие и скрытые общие файлы

| Файл | Владелец (порядок) | Почему без конфликта / что делать |
|---|---|---|
| `topic_content/services.py` | T004 (4 вызова окна) → T020 → T021 (стек) | цепочка по рёбрам |
| `topic_content/views.py` | T004 → T018 | ребро |
| `topic_content/serializers.py` | T004 → T020 | ребро |
| `topic_content/models.py` (вкл. `EmbeddedItem.clean`) | только T001 | IE-9/IE-10 здесь |
| `topic_content/embedded_items/services.py` | только T022 | только определение владельца |
| `generation/services.py` | только T004 | |
| `courses/apps.py`, `courses/tests/test_handler_registration.py` | только T004 | **общий с шагом 6** (регистрации): объединение строк на rebase |
| `config/response-codes.json`, `problem_types.py` (генерируемый), `locale/ru/problems.json`, `api-problems.json`, `access_registry/registry.py` | только T003 | **общие с шагом 6**: на rebase объединение строк и `gen_problem_types.py`; новый код срезу нужен — доклад |
| `course_pipeline/gates/registry.py` | только T023 | **общий с шагом 6** |
| `course_pipeline/gates/rules_structure.py`, `gates/facts.py` | только T024 | **общие с шагом 6** |
| `scripts/check_topic_content_writes.py` | T003 | 4 писателя внесены заранее |
| `docs/engineering/module-tiers.json` | T002 | **общий с шагом 6** |
| `docs/engineering/module-graph.json`, `module-map.md` | генерируемые, `shared` | координатор на rebase выполняет `gen_module_map.py` |
| `docs/engineering/test-registry.json`, `test-location.json` | никто | имена и места подобраны (§5) |
| `docs/TAGS.md` | T003 → T032 | срезы frontmatter не трогают |
| `rung_theory/AGENTS.md`, `README.md` | T002 → T005 | ребро |
| `courses/models.py` | никто | потолок 7138 строк |
| миграции `courses` | T001 | **общая цепочка с шагом 6**: номер на вливании |
| `TaskClassModal.tsx`, `task_classes/services.py`, `course_structure/deletion.py` | T029 | **общие с шагом 6** |
| `course_pipeline/auto_pipeline.py` | T016 | **общий с шагом 6** |
| `saga/gate_backing.py`, `course_pipeline/gating.py` | T025 | **общие с шагом 6** |
| `lesson/mode_a/services.py` | T026 | **общий с шагом 6** |
| `topic_content/generation/context.py` | T027 | **общий с шагом 6** |

Пересечений `Файлы:` у задач без пути между ними нет (`probe.py`).

## 7. Расписание

### N = 4, R = 3, c = 6, детерминированно (p = 0, `trace.py 4 3 6 serial 21`): K видна потомкам после CI 21 мин

| Задача | Слот | Старт | Сдана | Влита | | Задача | Слот | Старт | Сдана | Влита |
|---|---|---|---|---|---|---|---|---|---|---|
| T001 K | 1 | 0 | 24 | 38 (CI 59) | | T018 | 1 | 83 | 107 | 128 |
| T002 K | 2 | 0 | 24 | 44 (CI 65) | | T019 | 3 | 86 | 110 | 134 |
| T004 K | 3 | 0 | 24 | 50 (CI 71) | | T030 | 4 | 95 | 119 | 140 |
| T007 T | 4 | 0 | 15 | 29 | | T031 | 2 | 104 | 128 | 146 |
| T003 K | 4 | 15 | 30 | 56 (CI 77) | | T013 | 1 | 107 | 122 | 152 |
| T006 T | 1 | 24 | 39 | 62 | | T021 S | 3 | 110 | 125 | 158 |
| T010 T | 2 | 24 | 34 | 68 | | T022 | 4 | 119 | 134 | 164 |
| T011 T | 3 | 24 | 34 | 74 | | T012 | 1 | 122 | 137 | 170 |
| T008 T | 4 | 30 | 40 | 80 | | T014 | 3 | 125 | 140 | 176 |
| T009 T | 2 | 34 | 44 | 86 | | T017 | 2 | 128 | 143 | 182 |
| T024 | 3 | 34 | 49 | 92 | | T023 | 4 | 134 | 149 | 188 |
| T028 | 1 | 59 | 83 | 110 | | T025 | 1 | 137 | 152 | 194 |
| T005 K | 2 | 65 | 80 | 98 (CI 119) | | T026 | 3 | 140 | 155 | 200 |
| T016 | 4 | 71 | 95 | 116 | | T027 | 2 | 143 | 158 | 206 |
| T020 S | 3 | 71 | 86 | 104 | | T029 | 4 | 149 | 164 | 212 |
| T015 | 2 | 80 | 104 | 122 | | T032 H | 1 | 212 | 227 | **241** |

Что видно из таблицы.
- **Окно K используют `[T]` и T024** (предков у неё нет). Слоты простаивают с 49-й по 59-ю минуту:
  ждут CI первой K.
- **Узкое место — по-прежнему очередь вливаний:** 32 × 6 = 192 мин работы координатора подряд. Срезы
  сданы к 164-й минуте, последний влит на 212-й.
- **Варианты:**
  - вливания партией (4 + 2n) — 211;
  - без CI-ворот K — 241 (очередь их поглощает);
  - N = 3 — 247;
  - N = 2 — 317.
- **Совпадения с шагом 6** (T023–T029, T016, T028) стоят в середине и в конце веера.

### Сценарии (`sim3.py`, медиана / p90, мин; приёмка +30 включена)

| | p = 0.43 | p = 0.61 |
|---|---|---|
| N = 4, `trail` (CI не держит никого) | 329 / 356 | 354 / 388 |
| **N = 4, `hybrid` (CI держит только K)** | **352 / 387** | **380 / 414** |
| N = 4, `gate` (буквально: ветка движется после зелёного) | 382 / 414 | 412 / 443 |
| N = 4, `hybrid`, 15 % красных партий | 400 / 463 | 429 / 498 |
| N = 4, `gate`, 15 % красных | 445 / 514 | 466 / 553 |
| N = 4, `hybrid`, партиями | 348 / 384 | 378 / 412 |
| N = 4, `hybrid`, c = 3 | 337 / 376 | 365 / 400 |
| N = 3, R = 2, `hybrid` | 390 / 422 | 427 / 462 |
| **N = 2, R = 2, `hybrid`** | **502 / 542** | **562 / 605** |
| N = 2, `gate` | 526 / 564 | 587 / 635 |
| N = 5, R = 4, `hybrid` | 342 / 372 | 363 / 400 |
| N = 4, `hybrid`: T004 ×3 и отказ / T003 ×3 и отказ / обе | 388 / 376 / 408 | — |
| N = 4, `hybrid`: отказ T005 / T001 | 359 / 365 | — |
| N = 2, `hybrid`: T004 ×3 и отказ / обе | 551 / 592 | — |
| N = 4 / N = 2, вариант «3 K» (§2.1) | 371 / 498 | 402 / 555 |

В режиме `trail` откат красной партии не задевает начатых потомков, поэтому для K он занижает цену.
Красная K ломает до 20 срезов. По этой причине CI держит только K.

## 8. Ревью, вливание, CI, приёмка

1. **Очередь вливаний.** Механику делает `task_pairs.py merge` (rebase, `--ff-only`, `gen_module_map.py`,
   `gen_problem_types.py`, объединение строк реестров), координатор подтверждает. Тогда c = 3, это −15 мин.
   Годное вливается партией по рангу.
2. **CI: режим `hybrid`, правило записано буквально.**
   - Ветка плана движется после локального `check.sh` и пробного слияния, **не дожидаясь CI**.
   - Партия пушится в свою ссылку `ci/s8-b<NN>`: у неё своя группа concurrency, а `cicd-${{ github.ref }}`
     с `cancel-in-progress: true` гасил бы прогоны соседей.
   - **Исключение — K.** Потомки K стартуют от коммита, который прошёл CI, потому что K меняет схему,
     коды и горячие файлы, и её красный CI ломает до 20 срезов. Ворота стоят 21–30 мин на пути
     (352 против 329).
   - **Красная партия срезов:** делится пополам, виновник откатывается `git revert` и идёт на
     доработку с рангом + 50. Потомки, начатые от него, получают сообщение и делают rebase.
   - Режим `gate` (ждать CI на каждом ребре) стоит +30 мин при N = 4 и +24 при N = 2 против
     `hybrid`. Он оправдан, если красных партий срезов больше ~25 %: тогда `trail`-откаты дороже ворот.
     Долю координатор пишет в журнал.
   - `only_groups` по `Тест-группа:` мало что даёт: отпечаток грубый, любая правка `services/` сбрасывает
     все группы django. CI — полный django, 15–28 мин, раннеры общие с шагом 6, **координатор CI один на
     обе фичи**.
3. **Ревью.** Пул R = N − 1. Линзы:
   - K: «хватит ли срезам», для T004 ещё «нет логики в заглушках», для всех K «нет имён соседней K»;
   - `[T]`: «AC покрыт, обе стороны, данные в методе, владелец в имени»;
   - срез: логика, `Контракт:`, `Готово-когда:`.

   Механику (`check.sh`, `hold`, проверку отметок) ревьюер не повторяет. Второй круг — по диффу
   доработки, кругов не больше двух.
4. **Ворота вливания.** Срез вливается после своих предков (K — проверенных CI) и своей `[T]`.
5. **Приёмка по истории,** как только влиты её срезы: US6 и US5 первыми, US1 — с AC-7 вживую на `cp-*`,
   Playwright — на `cc-*`.

## 9. Конфликты и простой

1. **Шаг 6 работает одновременно.** Общие файлы перечислены в §6 с пометкой. Правило базы «общие файлы
   одновременно не берутся» действует между фичами через `Файлы:` обоих `tasks.md`. Для K это может
   значить ожидание; номер миграции и строки реестров берутся на rebase. Модель этого простоя не считает.
2. **Очередь вливаний** — §8 п. 1.
3. **T004 стала шире на окно** (`rung_listeners.py`, `apps.py`, `test_handler_registration.py`), но потеряла
   гейты и `WRITER_FILES`. ×3 и отказ: +36 мин при N = 4, +49 при N = 2. Запасной разрез — по шву
   «генерация (C12, C13)» | «`topic_content` и окно (C14, C17)».
4. **T003 стала шире на коды** (`problem_types.py`, каталог, выведение). ×3 и отказ: +24 мин при N = 4.
   Запасной разрез указан в задаче.
5. **Новые рёбра импорта.** Срез, который импортирует `rung_theory` из запрещённого модуля, ловит
   pre-commit (`check_module_boundaries.py`). Список запрещённых модулей лежит в C6, и ревьюеру среза
   T018, T024, T028, T029 его называют.
6. **`expectedFailure` на чужом методе.** Если срез «чинит» метод соседа, это пересечение: метод с чужим
   `t0xx` в имени он не трогает, а докладывает.
7. **Полный прогон `courses` идёт 30 мин.** Исполнитель гоняет свои тесты и группу, полный прогон делает CI.

## 10. Прогноз против бейзлайна

| | Бейзлайн (оценщик) | r2 (без CI в модели) | **r3, N = 4** | **r3, N = 2** |
|---|---|---|---|---|
| Длительность, p = 0.43 | ~10–10.5 ч | 5.4 ч (326) | **5.9 ч (352)** | **8.4 ч (502)** |
| Длительность, p = 0.61 | — | 5.9 ч (356) | **6.3 ч (380)** | **9.4 ч (562)** |
| То же, 15 % красных партий | — | — | 6.7–7.2 ч | 9.3–10.2 ч |
| Одновременно занято | 2.1–2.4 из 4 (1.48 по оценщику) | 2.87–2.96 | 2.43–2.57 до CI хвоста; 2.8–2.9 до последнего вливания | 1.67–1.69 из 2 |
| Цена | ~$133 | $180 / $213 | **$179 / $211** | то же |

**Качество.**
- «Пересечение с соседней задачей» внутри фичи сводится к рёбрам `views.py`, `serializers.py`,
  `services.py`.
- Новый класс отказов — «ребро импорта» — закрыт `edges.py` на плане и pre-commit на коде.
- «Расхождение сторон» держат срез насквозь и `[T]`.
- «Незакрытый пункт» держат имена тестов и владельцы методов AC.
- «Тест, который ничего не держит», ловят `hold` и снятие всех отметок.
- Остаётся пересечение с шагом 6.

Цена ×1.35–1.6 к бейзлайну. Её снижает доля доработок: при p = 0.25 выходит $151.

## 11. Замечания к процессу (`design.md`)

1. **§3.2 п. 3 «K 1–3» заменить на «K ≤ 20 % W, каждая ≤ M, глубина 1 (2 — с `Почему не одна:`)».**
   Число K следует из размера (§2.1), и текущая формулировка противоречит потолку M в §4.
2. **В пробу плана (§5) добавить проверку рёбер импорта**: новые рёбра из `Файлы:`/`Контракт:` против
   графа модулей проекта (П-8/П-9), если проект его ведёт. Без неё цикл находит pre-commit второго среза.
3. **Проба «скрытое ребро K → K»**: имена, которые K употребляет (коды, типы, модули), обязаны
   существовать на базе или в самой K.
4. **Режим CI назвать в §3 шаг 12:** `hybrid` по умолчанию, порог перехода на `gate` — доля красных партий.
5. **Отметки xfail:** владелец в имени метода, срез снимает все свои отметки, `[H]` проверяет, что их не
   осталось. Место `[T]` — по правилу проекта о расположении тестов, а не «наверху».
6. Из r2 в силе: очередь вливаний в §7, своя ссылка CI партии, скрытые общие файлы из `pair-rules.txt`.
