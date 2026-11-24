# Параллельная реализация фичи: как это делают лидеры и есть ли готовый плагин

Сводка от 2026-11-24. Собрана из двух проходов: `research-practices.md` (практики и источники) и `research-plugins.md` (готовые инструменты; звёзды и даты взяты через GitHub API). Мои выводы, которых нет в источниках, помечены «[вывод]».

## 1. Коротко

- **Ширина задаётся при разложении.** Пять исполнителей не сделают параллельной фичу, которую нарезали цепочкой. Сколько исполнителей полезно, определяет ширина графа зависимостей, а сколько длится фича, определяет его самая длинная цепочка (критический путь).
- **Лидеры режут фичу «поперёк», а не «послойно».** Каждый кусок содержит свой UI, свою логику и свои тесты и лежит в своих файлах. Общее (типы, интерфейсы, заглушки) делается одной короткой первой фазой, потом куски расходятся веером.
- **Ревью у них не тормозит работу.** Оно короткое и сверяет код со спекой. Мелкие замечания не возвращают задачу на второй круг. Механические проверки проходят до ревью. Пока задача ждёт ревью, исполнитель берёт следующую.
- **Готового плагина, который решает задачу как есть, нет.** Одни инструменты исполняют уже готовый граф, другие задают формат задач. Ни один не проверяет, что разложение даёт ширину 4–5, и не перестраивает его. Полезные идеи разбросаны по нескольким проектам, и их придётся собрать самим.

## 2. Концепция простым языком

### 2.1 Почему из 20–30 задач параллельно идут только 4–5

Представьте фичу как граф: задачи соединены стрелками «B нельзя начать, пока не готова A». Тогда:

- быстрее самой длинной цепочки стрелок фича не закончится, сколько исполнителей ни добавляй ([метод критического пути](https://en.wikipedia.org/wiki/Critical_path_method));
- в каждый момент занято столько исполнителей, сколько задач свободно от незакрытых стрелок. Это и есть «ширина» графа.

Если задачи нарезаны слоями («модели → сервисы → эндпоинты → UI»), граф выходит узкой длинной лестницей, и исполнители простаивают. Именно такой порядок внутри истории предписывает шаблон Spec Kit: «Models before services, Services before endpoints» ([tasks-template.md](https://github.com/github/spec-kit/blob/main/templates/tasks-template.md)). [вывод] Это наиболее вероятная причина жалобы: дело в форме графа, а не в количестве исполнителей.

### 2.2 Принципы разложения для ширины 4–5

1. **Вертикальные срезы вместо слоёв.** Каждый кусок проходит фичу насквозь и проверяется сам по себе.
   - Spec Kit: «Tasks MUST be organized by user story to enable independent implementation and testing» ([tasks.md](https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/tasks.md)).
   - Shape Up: scope строится, интегрируется и закрывается независимо, «ideally within a few days». Нарезка по ролям прячет прогресс ([Shape Up, гл. 12](https://basecamp.com/shapeup/3.3-chapter-12)).
   - Google: вертикальные срезы можно строить параллельно, слои развязываются заглушками («proto signature or API stub»), допустима сетка «слои × фичи» ([small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html)).
2. **Сначала контракт, потом веер.** Интерфейсы, типы и заглушки фиксируются первой короткой фазой. Тогда «B ждёт, пока A будет реализована» превращается в «B ждёт только интерфейс A», и цепочка рвётся.
   - Foundational-фаза в Spec Kit «BLOCKS all user stories» ([tasks-template.md](https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md)). Поэтому её надо держать маленькой.
   - Consumer-driven contracts ([Fowler](https://martinfowler.com/articles/consumerDrivenContracts.html)), [Pact](https://pact.io/).
   - В wshobson agent-teams файлом типов владеет лид, исполнители его только импортируют ([SKILL.md](https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/parallel-feature-development/SKILL.md)).
3. **У каждого файла один владелец.** Две одновременные задачи не трогают один файл.
   - Метка `[P]` в Spec Kit ставится только при «different files, no dependencies»; «Tasks affecting the same files must run sequentially» ([implement.md](https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/implement.md)).
   - Agent Teams: «Two teammates editing the same file leads to overwrites» ([документация](https://code.claude.com/docs/en/agent-teams)).
   - В CCPM у задачи есть поля `depends_on`, `parallel` и `conflicts_with` ([CCPM](https://github.com/automazeio/ccpm)).
4. **Явный граф, а затем волны.** Каждая задача объявляет свои зависимости. Исполнитель берёт любую задачу, у которой все предшественники закрыты.
   - Kiro: «tasks within a wave execute concurrently» ([Kiro](https://kiro.dev/docs/specs/)).
   - Agent Teams: заблокированная задача открывается сама, когда закрыт её предшественник ([документация](https://code.claude.com/docs/en/agent-teams)).
   - Beads: `bd ready` выдаёт работу без открытых блокеров ([beads](https://github.com/gastownhall/beads)).
   - CAID (CMU): менеджер строит план с учётом зависимостей, исполнители работают в отдельных worktree, итог сводится merge с тестами. Против одного агента это дало +14.7% и +25.6% ([arXiv 2603.21489](https://arxiv.org/abs/2603.21489)).
5. **Маленькие задачи.**
   - DORA: от нескольких часов до пары дней, больше недели — «too big». ИИ склонен порождать слишком большие фичи ([DORA](https://dora.dev/capabilities/working-in-small-batches/)).
   - Google: около 100 строк — нормальный CL, 1000 — слишком много ([small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html)).
   - Devin: задача на «three hours or less» человеческого времени ([Devin](https://docs.devin.ai/essential-guidelines/when-to-use-devin)).
   - Agent Teams: 3–5 исполнителей, по 5–6 задач на каждого, и «Three focused teammates often outperform five scattered ones» ([документация](https://code.claude.com/docs/en/agent-teams)).
6. **Чаще вливать и не ломать сборку.**
   - Trunk-based: в trunk минимум раз в сутки, длинные изменения идут через feature flags и branch by abstraction ([trunkbaseddevelopment.com](https://trunkbaseddevelopment.com/), [branch by abstraction](https://trunkbaseddevelopment.com/branch-by-abstraction/)).
   - Очередь вливаний с проверками в стиле Bors в Gas Town Refinery ([gastown](https://github.com/gastownhall/gastown)).

### 2.3 Честные пределы параллельности

- Anthropic: в задачах на код «fewer truly parallelizable tasks than research». Мультиагентная работа стоит примерно 15× токенов ([multi-agent research](https://www.anthropic.com/engineering/multi-agent-research-system)).
- Cognition: «conflicting decisions carry bad results». По умолчанию они советуют одного линейного агента ([Don't build multi-agents](https://cognition.com/blog/dont-build-multi-agents)).
- Компилятор C от Anthropic: 16 агентов, частые конфликты слияния. На «одной гигантской задаче» все агенты упёрлись в один баг, пока работу не разделили через оракул ([building-c-compiler](https://www.anthropic.com/engineering/building-c-compiler)).
- CodeCRDT: от +21% ускорения до −39% замедления в зависимости от структуры задачи ([arXiv 2510.18893](https://arxiv.org/abs/2510.18893)).
- Агентские PR: текстовые конфликты у 19.8% одновременных пар от одного агента и у 41.7% пар от разных агентов ([arXiv 2607.04697](https://arxiv.org/abs/2607.04697)). Семантические конфликты на реальных PR редки, зато на задачах со сменой интерфейса доходят до 97%. Если агенту сообщить о соседнем изменении, восстанавливается 82% прогонов ([arXiv 2609.25396](https://arxiv.org/abs/2609.25396)).
- Factory прямо оставляет вопрос открытым: «Is parallelization necessary?» ([Factory Missions](https://docs.factory.com/missions/overview)).
- [вывод] Главный риск — не сама параллельность, а смена общего интерфейса посреди волны. Его закрывают два приёма: контракт замораживают в первой фазе, а при изменении контракта уведомляют соседей.

### 2.4 Параллельность внутри задачи: цикл «сделал → ревью → правки»

1. **Механику проверяет не ревьюер.** Тесты, линт и typecheck должны пройти до ревью: через Stop-hook с exit 2, через `/goal`, или исполнитель предъявляет доказательство (команду и её вывод) ([best practices](https://code.claude.com/docs/en/best-practices)). Хуки `TaskCompleted` и `TeammateIdle` не дают закрыть задачу без гейта ([Agent Teams](https://code.claude.com/docs/en/agent-teams)).
2. **Ревьюер сверяет со спекой, а не ищет «хоть что-нибудь».** Формула: «report gaps that affect correctness and skip style». Причина: «A reviewer that's asked to find problems will always find *something*» ([best practices](https://code.claude.com/docs/en/best-practices)).
3. **Замечания делятся на блокирующие и нет.**
   - У Google есть «LGTM with comments» и метки Nit / Optional / FYI ([speed](https://google.github.io/eng-practices/review/reviewer/speed.html), [comments](https://google.github.io/eng-practices/review/reviewer/comments.html)).
   - Ship/Show/Ask: одобрение не обязательно для слияния ([Fowler](https://martinfowler.com/articles/ship-show-ask.html)).
   - bmad-loop ограничивает ревью тремя кругами (`max_review_cycles`), недоделки уходят в `deferred-work.md` ([bmad-loop](https://github.com/bmad-code-org/bmad-loop)).
4. **Пока ревью идёт, исполнитель не ждёт.** У Google автор продолжает работу стеком поверх CL на ревью ([small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html)). Ревью должно занимать минуты, а «More than a hour or two» уже вредит; ИИ-ревью — «minutes or less» ([continuous review](https://trunkbaseddevelopment.com/continuous-review/)). Meta меряет P75 времени в ревью ([Meta](https://engineering.fb.com/2022/11/16/culture/meta-code-review-time-improving/)).
5. **Параллельные ревьюеры с разными линзами** (безопасность, производительность, тесты) смотрят задачу одновременно, а не по очереди: [Agent Teams](https://code.claude.com/docs/en/agent-teams), `/simplify` с четырьмя ревьюерами ([commands](https://code.claude.com/docs/en/commands)), `/team-review` у [wshobson](https://github.com/wshobson/agents/blob/main/plugins/agent-teams/README.md). Отдельный проверяющий экземпляр «tends to perform better» одного вызова на обе роли ([building effective agents](https://www.anthropic.com/engineering/building-effective-agents)).
6. [вывод] В сумме это даёт три приёма: механика уходит в гейты до ревью; ревью сверяет со спекой и шлёт на второй круг только блокирующее, а мелочи уходят в хвостовую задачу; исполнитель тем временем берёт следующую задачу волны.

## 3. Готовые плагины и инструменты

| Инструмент | ★ / статус | Что даёт | Чего не хватает | Оценка |
|---|---|---|---|---|
| [GitHub Spec Kit](https://github.com/github/spec-kit) | 151k, v1.4.4 (2026-11-23), MIT | Задачи по историям, Foundational, `[P]`, правило «один файл → последовательно» | Послойный порядок внутри истории порождает цепочки; нет планировщика и ревью кода | Уже стоит у проектов; источник узкого графа. Нужна надстройка |
| [Task Master](https://github.com/eyaltoledano/claude-task-master) | 28.5k, 0.43.1 (2026-03), MIT + Commons Clause | Явные `dependencies`, `next`, `expand`, анализ сложности | Расписание держится «в уме» у LLM ([task-orchestrator](https://github.com/eyaltoledano/claude-task-master/blob/main/packages/claude-code-plugin/agents/task-orchestrator.md)); нет ревью; Node; уходит в коммерцию | Не годится |
| [CCPM](https://github.com/automazeio/ccpm) | 8.5k, без релизов, MIT | `depends_on`, `parallel`, `conflicts_with`; потоки внутри задачи ([execute.md](https://github.com/automazeio/ccpm/blob/main/skill/ccpm/references/execute.md)) | Нет ревью («Do NOT use for … reviewing PRs»), один worktree на эпик, ≤10 задач; «до 3×» заявляет сам вендор | Брать идеи |
| [obra/superpowers](https://github.com/obra/superpowers) | 325k, v7.0.2, MIT | Задачи по 2–5 мин, сильное ревью после каждой (спека + качество) | Прямо запрещает параллель: «Never dispatch multiple implementation subagents in parallel» ([SKILL.md](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md)) | Эталон ревью, но тот самый последовательный цикл |
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) + [bmad-loop](https://github.com/bmad-code-org/bmad-loop) | 55.7k / 192, MIT | Цикл на Python без LLM в управлении, ≤3 кругов ревью, журнал отложенного | Строго последовательно | Брать идеи предела кругов |
| [Ruflo (claude-flow)](https://github.com/ruvnet/ruflo) | 82k, v3.80.5, MIT | Рой агентов, worktree на агента, GOAP-цели | Огромная непрозрачная обвязка; разложение фичи — не её функция | Не годится |
| [wshobson agent-teams](https://github.com/wshobson/agents/tree/main/plugins/agent-teams) | 42.9k (каталог), MIT | `/team-feature`: потоки с владением файлами, контракты, срезы; `/team-review` по измерениям | Только промпты поверх экспериментальных Agent Teams; ширина разложения не проверяется | Ближе всех по идеям; нужна серьёзная доработка |
| [am-will/swarms](https://github.com/am-will/swarms) | 250, лицензии нет | Обязательные зависимости, проверка плана сабагентом, волны | Волна ждёт самую медленную задачу; мало пользователей | Не годится |
| [Gas Town](https://github.com/gastownhall/gastown) + [Beads](https://github.com/gastownhall/beads) | 18.9k / 29k, MIT | `bd ready`, захват задач, Refinery — очередь вливаний с бисекцией | Go, Dolt, tmux, демон: противоречит правилу «bash, git, python3» | Брать идеи очереди вливаний |
| [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) | встроено, experimental | Общий список с зависимостями, самозахват с блокировкой, хуки-гейты | Разложения нет; статус может отставать; одна команда на сессию | Механизм исполнения, а не разложения |
| [Claude Code `/batch`](https://code.claude.com/docs/en/commands) | встроено | 5–30 независимых единиц, worktree и PR на каждую | Только для механических массовых правок | Не для фич |
| [feature-dev](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/feature-dev) | официальный, Apache-2.0 | Параллельные разведчики и ревьюеры | Один поток реализации | Не годится |
| [Kiro](https://kiro.dev/docs/specs/) | продукт AWS | Граф из tasks.md, волны параллельно | Отдельная IDE/CLI, не плагин | Идея волн |
| [Devin managed Devins](https://cognition.com/blog/devin-can-now-manage-devins), [Factory Missions](https://docs.factory.com/missions/overview) | коммерческие | Координатор + изолированные исполнители | Закрытые, цифр эффекта нет | Не годится |

Ещё просмотрены и отброшены: [claude-squad](https://github.com/smtg-ai/claude-squad), [Crystal](https://github.com/stravu/crystal), [HumanLayer](https://github.com/humanlayer/humanlayer). Это менеджеры сессий или однопоточные конвейеры.

## 4. Вывод

**Готового популярного плагина, который закрывает задачу без серьёзной доработки, нет.**

- Инструменты делятся на два лагеря. Одни **исполняют** готовый граф (Agent Teams, Beads, Task Master, swarms, Kiro), другие **описывают формат** задач (Spec Kit, CCPM). Ни один не **меряет ширину графа и критический путь** и не перестраивает разложение под N исполнителей. Если tasks.md — цепочка, никакой оркестратор её не распараллелит.
- По второй жалобе: самые популярные решения с сильным ревью (superpowers, bmad-loop) устроены строго последовательно. Параллельное ревью по линзам есть только в виде промптов (wshobson, `/simplify`).
- Ближайший кандидат — wshobson agent-teams. Он остаётся текстом для LLM поверх экспериментальной функции и ничем не проверяет результат разложения.
- Рамки базы: конвейер фич чужой (ADR-0010), Spec Kit у проектов уже стоит, зависимости допускаются только bash, git и python3. [вывод] Значит, решение — не замена Spec Kit, а надстройка над его tasks.md: правила формы разложения (срезы, контракт первым, владение файлами, явные `depends_on`/`conflicts_with`) плюс проба, которая считает ширину и критический путь, и изменения в существующей паре исполнитель/ревьюер (гейты до ревью, сверка со спекой, неблокирующие замечания в хвост, исполнитель не ждёт ревью). Идеи для переноса: контракты и владение файлами из wshobson, `conflicts_with` из CCPM, предел кругов и журнал отложенного из bmad-loop, очередь вливаний из Gas Town Refinery.

## 5. Что не подтверждено

- Цифры «Modern Code Review: A Case Study at Google» нашлись только во вторичных источниках ([страница](https://research.google/pubs/modern-code-review-a-case-study-at-google/)).
- Страницы Cursor про multi-agent отдали 404 ([llms.txt](https://cursor.com/llms.txt)). Страница Codex cloud ничего не говорит про нарезку задач ([страница](https://learn.chatgpt.com/docs/cloud)).
- Эффект CCPM («5–8 параллельных задач», «до 3×») заявлен вендором и не проверен.
- Число звёзд superpowers (325k) взято из одного прохода и выглядит необычно высоким; перед цитированием стоит перепроверить.
