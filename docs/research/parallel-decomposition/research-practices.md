# Как лидеры раскладывают фичу на задачи для 4–5 параллельных исполнителей и как обходят цикл «сделал → ревью → правки»

Собрано 2026-11-24. Каждое утверждение взято со страницы, открытой в этом проходе; URL стоит рядом.
Мои выводы, а не слова источника, помечены «[вывод]».

## 0. Главное в пяти строках

1. Параллельность закладывается на этапе разложения, исполнители её не создают. Работу режут **вертикальными срезами** (история или scope: свой UI, логика и тесты), а не слоями. Общая основа и **контракты/заглушки** делаются первой короткой фазой. Дальше срезы идут параллельно, каждый в своих файлах.
2. Время фичи снизу ограничено **критическим путём** графа зависимостей. Число исполнителей полезно наращивать до ширины графа, дальше они простаивают. Сокращают сам путь: ранние контракты, разрыв ложных зависимостей, fast-tracking.
3. Задача маленькая: от часов до пары дней у людей, ≤3 ч у агента, ~100 строк диффа. На исполнителя 5–6 задач, команда из 3–5.
4. Ревью у лидеров быстрое (минуты, максимум сутки) и **неблокирующее по мелочам** (LGTM с замечаниями, метки Nit/Optional/FYI, Ship/Show/Ask). Пока PR ждёт, автор продолжает работу стеком.
5. Для агентов добавляются три вещи. Независимый ревьюер сверяет с **спекой**, а не ищет «что-нибудь». Механические проверки (тесты, линт, Stop-hook) проходят **до** ревью. Разные аспекты ревью смотрят **параллельные** ревьюеры, каждый со своей линзой.

## 1. Разложение фичи: приёмы

### 1.1 Вертикальные срезы, а не слои
- Spec Kit велит организовывать задачи по user story: «Tasks MUST be organized by user story to enable independent implementation and testing». Каждая фаза — «a complete, independently testable increment». https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/tasks.md
- Стратегия параллельной команды в Spec Kit: Setup и Foundational делаются вместе, затем каждый разработчик берёт свою историю (A — US1, B — US2, C — US3), и истории интегрируются независимо. https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md
- Shape Up: scope — часть проекта, которую можно построить, интегрировать и закончить независимо, «ideally within a few days». Нарезка по ролям (все дизайн-задачи в одном списке, весь код в другом) прячет прогресс: до самого конца ничего не готово целиком. Пример параллельности: дизайнер ведёт scope Locate, программист в то же время ведёт Save/Edit. https://basecamp.com/shapeup/3.3-chapter-12
- Shape Up различает два вида работы. «Layer cake» (тонкий бэкенд) идёт одним scope. «Iceberg» (сложный бэкенд под простым UI) делят на отдельные scopes. Плохой scope узнаётся по общему имени («bugs», «front-end»), по размытому «done» и по размеру мини-проекта. Задачи без своего scope копятся в «Chowder»; больше 3–5 таких задач — сигнал выделить scope. Там же.
- Google (small CLs) предлагает два направления резки. Вертикально — независимые полные срезы («multiplication and division in a calculator»), которые можно строить параллельно. Горизонтально — слои, развязанные общим кодом или заглушками («proto signature or API stub»). Можно сочетать: «grid of layers by features», где каждая клетка — отдельный CL. https://google.github.io/eng-practices/review/developer/small-cls.html

### 1.2 Сначала основа и контракты, потом веер
- В Spec Kit фаза 2 (Foundational) «BLOCKS all user stories»: истории не начинаются, пока она не готова. https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md
- Consumer-driven contracts: потребитель фиксирует только то, на что опирается, и контракт поставщика выводится из этих ожиданий. Поставщик тогда добавляет поля без согласованных релизов, а ломающие изменения видны рано. Связь он не убирает, только делает её явной. https://martinfowler.com/articles/consumerDrivenContracts.html
- Pact: контрактные тесты снижают или убирают нужду в общих интеграционных стендах, и сервисы деплоятся независимо (`can-i-deploy`). Это маркетинговая страница без метрик. https://pact.io/
- [вывод] Контракт или заглушка, зафиксированные в Foundational, превращают зависимость «B ждёт реализацию A» в «B ждёт только интерфейс A». Это главный рычаг сокращения критического пути.

### 1.3 Владение файлами: две задачи не трогают один файл
- Метка [P] в Spec Kit ставится «ONLY if task is parallelizable (different files, no dependencies on incomplete tasks)». https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/tasks.md
- `/speckit-implement`: «Tasks affecting the same files must run sequentially». Фазы идут по порядку, тесты пишутся раньше реализации. Упавшая [P]-задача не останавливает остальные. https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/implement.md
- Claude Code agent teams: «Two teammates editing the same file leads to overwrites. Break the work so each teammate owns a different set of files». https://code.claude.com/docs/en/agent-teams
- CCPM: в метаданных каждой задачи есть `depends_on`, `parallel` и `conflicts_with`. Одну issue можно разрезать на потоки (БД, сервисы, API, UI, тесты) для разных агентов. Предупреждение оттуда же: агенты в одном worktree делят и одну БД. https://github.com/automazeio/ccpm

### 1.4 Граф зависимостей → волны, критический путь
- Kiro строит граф зависимостей из `tasks.md` и группирует задачи в волны: «Waves execute sequentially; tasks within a wave execute concurrently». Лимит параллельности и типичное число волн на странице не указаны. https://kiro.dev/docs/specs/
- Метод критического пути: длительность проекта не может быть меньше длины самой длинной цепочки зависимых работ («determines the shortest time possible»). Задачи вне пути имеют запас (float). Путь сокращают двумя способами: fast-tracking («performing more activities in parallel») и crashing, то есть дополнительные ресурсы на работы пути, «often at the cost of quality». https://en.wikipedia.org/wiki/Critical_path_method
- Agent teams: зависимая задача отображается как blocked и разблокируется автоматически, когда её предшественник завершён. Свободную задачу teammate берёт сам, захват защищён файловой блокировкой. https://code.claude.com/docs/en/agent-teams
- CAID (Geng, Neubig, CMU) устроен так: центральный менеджер строит план с учётом зависимостей, подзадачи идут асинхронно в изолированных git worktree, результаты сводятся через merge с проверкой тестами. Против одиночного агента: +14.7% на Commit0 и +25.6% абсолютной точности на PaperBench. https://arxiv.org/abs/2603.21489
- [вывод] Число одновременно занятых исполнителей ≈ ширина графа на каждом шаге. Если в 20–30 задачах ширина 4–5 только на отдельных шагах, проблема в форме графа (цепочки по слоям), а не в числе исполнителей.

### 1.5 Размер задачи и размер команды
- DORA: батчи на «hours to a couple days». Фича — «no more than a few days». Всё, что дольше недели до завершения и проверки, — «too big». В trunk — несколько малых изменений минимум раз в день. Отдельно отмечено: ИИ склонен генерировать большие фичи, которые трудно ревьюить. https://dora.dev/capabilities/working-in-small-batches/
- Google: «100 lines is usually a reasonable size for a CL, and 1000 lines is usually too large». Рефакторинг идёт отдельным CL. Тесты лежат в том же CL. https://google.github.io/eng-practices/review/developer/small-cls.html
- Devin берёт задачу, если человеку на неё нужно «three hours or less»; длиннее — дробить на сессии. Лучше всего идут задачи с явным критерием успеха (тесты, зелёный CI). https://docs.devin.ai/essential-guidelines/when-to-use-devin
- Agent teams: «Start with 3-5 teammates». Держать «5-6 tasks per teammate». На 15 независимых задач хватит трёх teammates. «Three focused teammates often outperform five scattered ones». Хорошая задача — самодостаточная единица с ясным результатом: функция, тестовый файл, ревью. https://code.claude.com/docs/en/agent-teams
- Anthropic, multi-agent research: лид запускает 3–5 субагентов параллельно, и на сложных запросах время падает «up to 90%». Каждому субагенту нужны цель, формат результата, инструменты и «clear task boundaries»; без этого субагенты дублировали друг друга. https://www.anthropic.com/engineering/multi-agent-research-system
- `/batch` в Claude Code делит крупное изменение на «5 to 30 independent units», каждый идёт в своём worktree и заканчивается своим PR. https://code.claude.com/docs/en/commands
- superpowers (writing-plans) режет на задачи по 2–5 минут, в каждой — пути файлов, код и шаг проверки. https://github.com/obra/superpowers

### 1.6 Где параллельность не работает (честные пределы)
- Anthropic: у большинства задач на код «fewer truly parallelizable tasks than research». Домены с общим контекстом и многими зависимостями пока «not a good fit». Мультиагент расходует ~15× токенов против чата. https://www.anthropic.com/engineering/multi-agent-research-system
- Cognition: «Actions carry implicit decisions, and conflicting decisions carry bad results». Пример: два параллельных субагента собирают несовместимые части Flappy Bird. Рекомендация — один линейный агент по умолчанию. https://cognition.com/blog/dont-build-multi-agents
- Компилятор на C от Anthropic: 16 агентов, задачи захватываются lock-файлом в `current_tasks/`, конфликты слияния «frequent», ~$20 000. Пока работа делилась на много независимых падающих тестов, агенты расходились сами. На ядре Linux («one giant task») все 16 упёрлись в один баг и затирали друг друга. Выход нашли через оракул: GCC собирал большую часть файлов, их компилятор — подмножество, и у каждого агента появились свои баги. https://www.anthropic.com/engineering/building-c-compiler
- Factory Missions прямо держат параллельность открытым вопросом («Is parallelization necessary?») и пишут: «Long-running plans accumulate errors». https://docs.factory.com/missions/overview
- CodeCRDT (600 прогонов): параллельная генерация дала от +21.1% ускорения до 39.4% замедления, в зависимости от структуры задачи; семантические конфликты 5–10%. https://arxiv.org/abs/2510.18893

### 1.7 Интеграция: как не утонуть в слияниях
- Trunk-based: в trunk коммитят минимум раз в 24 ч. Ветки короткие и рождаются на одной рабочей станции. Долгие изменения идут через branch by abstraction и feature flags. https://trunkbaseddevelopment.com/
- Branch by abstraction: абстракция → вторая реализация (выключена) → переключение → удаление старой. Каждый шаг — малый коммит, сборку не ломает. https://trunkbaseddevelopment.com/branch-by-abstraction/
- Google: после каждого CL из цепочки система работает («Don't break the build»). https://google.github.io/eng-practices/review/developer/small-cls.html
- Данные по агентским PR (33 596 PR, 2 807 репозиториев): текстовые конфликты у 19.8% одновременных пар от одного агента и у 41.7% пар от разных агентов. 84.4% конфликтных файлов — исходный код, ~42% конфликтов структурные (modify/delete, add/add). https://arxiv.org/abs/2607.04697
- Семантические конфликты (бенчмарк stale): на 417 реальных парах PR Django интерференция нашлась в 1 случае из 834 прогонов, на искусственных задачах со сменой интерфейса — в 97%. Если агенту передать сообщение о завершённом параллельном изменении, восстанавливается 82% прогонов. https://arxiv.org/abs/2609.25396
- [вывод] Опасны не параллельные задачи как таковые, а скрытая смена общего интерфейса посреди волны. Контракт, замороженный в Foundational, плюс уведомление соседей при его изменении закрывают большую часть риска.

## 2. Цикл ревью: как убрать последовательные круги

### 2.1 Скорость и неблокирующие замечания (люди)
- Google: «One business day is the maximum time it should take to respond to a code review request». Компания оптимизирует скорость команды, а не отдельного автора. Есть «LGTM with comments»: одобрить с открытыми замечаниями, если уверен, что автор их закроет, или если они мелкие или необязательные. https://google.github.io/eng-practices/review/reviewer/speed.html
- Google предлагает помечать вес замечания: Nit / Optional (Consider) / FYI. Без меток авторы считают обязательными «all comments». https://google.github.io/eng-practices/review/reviewer/comments.html
- Google: ожидание ревью — не простой. Автор стекует следующий CL поверх текущего; если изменение делится по файлам, части ревьюятся параллельно. https://google.github.io/eng-practices/review/developer/small-cls.html
- Trunk-based (continuous review): ревью — «A few minutes ... and tens of minutes acceptable». «More than a hour or two» уже бьёт по циклу. Для кода от ИИ первым проходит независимый ИИ-ревьюер вместе с линтом, тестами и статанализом, а человек смотрит намерение. «A co-author reviewing their own work is not a review». «AI-led review should take minutes or less». https://trunkbaseddevelopment.com/continuous-review/
- Ship/Show/Ask: одобрение не должно быть обязательным условием слияния. Show — PR открывается и вливается сразу, ревью идёт после. Ask — ждать перед слиянием, только когда изменение того требует. https://martinfowler.com/articles/ship-show-ask.html
- Meta: целевая метрика — P75 Time In Review, потому что с медленным хвостом коррелирует неудовлетворённость. Nudgebot сократил среднее время в ревью на 7%, а долю диффов, ждущих больше 3 дней, — на 12%. «Next Reviewable Diff» дал +17% ревью-действий в день. https://engineering.fb.com/2022/11/16/culture/meta-code-review-time-improving/

### 2.2 Агентная специфика
- Claude Code best practices предлагают ревьюировать дифф по SPEC.md с пометкой «report gaps that affect correctness and skip style». Обоснование: «A reviewer that's asked to find problems will always find *something*», а починка каждой находки плодит лишние абстракции и тесты. https://code.claude.com/docs/en/best-practices
- Там же. Проверку закрепляют до ревью: в промпте, через `/goal` (условие проверяет отдельная модель) или через Stop-hook (exit 2 не даёт закончить ход, пока typecheck красный). От агента требуют доказательство — команду и её вывод. Ревьюер, не видевший, как писался код, полезен именно свежестью взгляда, а не «умом». https://code.claude.com/docs/en/best-practices
- Agent teams: параллельное ревью одного PR тремя teammates с разными линзами (безопасность, производительность, покрытие тестами); лид сводит итог. Хуки TaskCompleted и TeammateIdle с exit 2 не дают закрыть задачу без прохождения гейта. https://code.claude.com/docs/en/agent-teams
- `/simplify` гоняет 4 ревью-агента параллельно (переиспользование, упрощение, эффективность, уровень абстракции). https://code.claude.com/docs/en/commands
- Building effective agents. Guardrails как вариант sectioning: один экземпляр делает работу, другой параллельно проверяет, и это «tends to perform better» одного вызова на обе роли. Evaluator-optimizer (цикл генерация ↔ оценка) оправдан при ясных критериях оценки и измеримой пользе от итераций. https://www.anthropic.com/engineering/building-effective-agents
- superpowers даёт два режима. subagent-driven-development: свежий субагент на задачу и двухстадийное ревью после каждой (сначала соответствие спеке, потом качество кода). executing-plans: одна сессия и одно ревью всей ветки в конце, режим «cheapest». https://github.com/obra/superpowers
- Devin: координатор раздаёт куски managed Devins, у каждого своя VM, следит за прогрессом и «resolves conflicts». В примерах — до 10 сессий одновременно. Чисел по эффекту нет. https://cognition.com/blog/devin-can-now-manage-devins
- [вывод] Круги ревью сокращают тремя приёмами. (а) Механическое уходит в гейты до ревью. (б) Ревью сверяет со спекой и критериями задачи и делит находки на блокирующие и неблокирующие; неблокирующие уходят в отдельную задачу хвоста, а не во второй круг. (в) Пока задача на ревью, исполнитель берёт следующую из волны (стек), а не ждёт.

## 3. Готовые инструменты и плагины

| Что | Что даёт для параллельности | Популярность | Источник |
|---|---|---|---|
| GitHub Spec Kit | tasks.md по историям, фаза Foundational, метка [P], правило «same file → sequential»; сам исполнитель параллельно не запускает | 151k ★ | https://github.com/github/spec-kit |
| AWS Kiro (IDE/CLI) | граф из tasks.md → волны, исполнение волнами параллельно | — (продукт) | https://kiro.dev/docs/specs/ |
| CCPM | PRD → epic → задачи с depends_on/parallel/conflicts_with, GitHub Issues, worktree, потоки внутри issue; ≤10 задач на epic по умолчанию; цифры эффекта от вендора, непроверенные | 8.5k ★ | https://github.com/automazeio/ccpm |
| Task Master | PRD → задачи с зависимостями, анализ сложности, expand, next; параллельного исполнения на странице нет | 28.5k ★ | https://github.com/eyaltoledano/claude-task-master |
| superpowers | writing-plans (задачи 2–5 мин), subagent-driven-development (ревью на задачу), dispatching-parallel-agents, worktrees | 325k ★ (по странице) | https://github.com/obra/superpowers |
| Claude Code agent teams | общий список задач с зависимостями, самозахват с блокировкой, хуки-гейты; experimental | встроено | https://code.claude.com/docs/en/agent-teams |
| Claude Code `/batch` | 5–30 независимых единиц, worktree и PR на каждую; для механических массовых правок | встроено | https://code.claude.com/docs/en/commands |
| Devin managed Devins / Factory Missions | координатор + изолированные исполнители; у Factory параллельность — открытый вопрос | коммерческие | см. ссылки выше |

[вывод] Ни один инструмент не меряет ширину графа и критический путь и не перестраивает разложение под N исполнителей. Spec Kit и Task Master задают форму задач. Kiro, agent teams и CCPM исполняют уже готовый граф. Качество графа (вертикальность, контракты, владение файлами) нигде не проверяется автоматически.

## 4. Что не удалось подтвердить

- Цифры исследования Google «Modern Code Review: A Case Study at Google» (медиана ~24 строки, ответ меньше часа) нашлись только во вторичных слайдах; первоисточник не открыт: https://research.google/pubs/modern-code-review-a-case-study-at-google/
- Страницы Cursor про multi-agent и worktrees отдали 404 (по ссылкам из https://cursor.com/llms.txt), утверждений о Cursor здесь нет.
- Страница Codex cloud (https://learn.chatgpt.com/docs/cloud) говорит только об отдельном workspace на задачу; про best-of-N и нарезку задач на ней ничего нет.
- Цифры эффекта CCPM (5–8 параллельных задач, «up to 3× faster») заявлены вендором и не проверены.
