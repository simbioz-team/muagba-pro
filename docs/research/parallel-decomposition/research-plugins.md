# Готовые плагины и инструменты: разложение фичи и параллельные исполнители

Дата сверки: 2026-11-24. Звёзды, лицензии, даты взяты через GitHub API (`gh api repos/...`),
факты о механике — из README и файлов скилов/шаблонов в самих репозиториях (ссылки на файлы ниже).

## Сводная таблица

| Инструмент | Звёзды | Последний релиз / push | Лицензия | Граф зависимостей | Метки параллельности | Назначение исполнителей | Ревью | Годится для 4–5 исполнителей с ревью |
|---|---|---|---|---|---|---|---|---|
| [GitHub Spec Kit](https://github.com/github/spec-kit) | 151k | v1.4.4, 2026-11-23 | MIT | Неявный: фазы + «depends on Txxx» текстом | `[P]` = «разные файлы, нет зависимостей» | Нет планировщика; `/implement` идёт по фазам, `[P]` «можно вместе» | Нет ревью кода; `/converge` дописывает недоделанное в tasks.md | Нет: даёт метки, но шаблон сам порождает цепочки |
| [Task Master (task-master-ai)](https://github.com/eyaltoledano/claude-task-master) | 28.5k | 0.43.1, 2026-03-31; push 2026-04 | MIT + Commons Clause | Да, явный `dependencies` у задачи, `next`, `expand`, анализ сложности | Нет отдельной метки; параллельность = «нет незакрытых зависимостей» | Агент-промпт `task-orchestrator` (LLM держит граф «в уме») | Нет встроенного | Нет: развитие ушло в коммерческий Hamster, оркестратор — только промпт |
| [CCPM](https://github.com/automazeio/ccpm) | 8.5k | релизов нет; push 2026-11-04 | MIT | Да: `depends_on`, `parallel`, `conflicts_with` в файле задачи | `parallel: true` + разбор задачи на «потоки» с файлами | Потоки внутри одной задачи, агенты в **одном** worktree эпика | Нет этапа ревью | Частично: идея потоков и `conflicts_with` полезна, ревью и изоляции нет; ≤10 задач на эпик |
| [obra/superpowers](https://github.com/obra/superpowers) | 325k | v7.0.2, 2026-11-03 | MIT | Нет графа: план — упорядоченный список задач 2–5 мин | Нет | subagent-driven-development: свежий сабагент на задачу, **строго по одной** | Сильное: ревью после каждой задачи (спека + качество) и финальное по ветке | Нет: прямой запрет «Never dispatch multiple implementation subagents in parallel (conflicts)» |
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) + [bmad-loop](https://github.com/bmad-code-org/bmad-loop) | 55.7k / 192 | v6.12.4, 2026-10-14 / v0.13.2, 2026-10-10 | MIT (README) | Эпики → истории; порядок по списку | Нет | bmad-loop: детерминированный Python-цикл, история за историей | Ревью отдельной свежей сессией, ≤3 круга (`max_review_cycles`) | Нет: последовательный конвейер; ценен цикл ревью без LLM в управлении |
| [Ruflo (бывш. claude-flow)](https://github.com/ruvnet/ruflo) | 82k | v3.80.5, 2026-11-24 | MIT | GOAP-планировщик целей (`ruflo-goals`), трекер задач роя | Топологии роя (mesh/hierarchical) | Рой агентов, worktree на агента | Нет выделенного ревью-гейта | Нет: огромная обвязка (100+ агентов, память, федерация), декомпозиция не про граф фичи |
| [wshobson/agents → agent-teams](https://github.com/wshobson/agents/tree/main/plugins/agent-teams) | 42.9k (каталог) | релизов нет; push 2026-11-24 | MIT | Скил `task-coordination-strategies` (граф, баланс нагрузки) | Владение файлами, контракты интерфейсов, вертикальные срезы | `team-lead` раскладывает, `team-implementer` в границах файлов | Параллельное мульти-ревью по измерениям (`/team-review`) | Ближе всех по идеям, но это только промпты поверх экспериментальных Agent Teams; нет проверки разложения |
| [am-will/swarms](https://github.com/am-will/swarms) | 250 | push 2026-04-18 | не указана | Да: каждая задача обязана объявить зависимости | Волны (wave) | Тот же оркестратор, что планировал, пускает волну сабагентов | Ревью плана сабагентом; проверка между волнами | Нет: малоизвестен, без лицензии, волна ждёт самую медленную задачу |
| [Gas Town](https://github.com/gastownhall/gastown) + [Beads](https://github.com/gastownhall/beads) | 18.9k / 29k | v1.2.1, 2026-06-06 / v1.3.4, 2026-11-04 | MIT | Beads: граф задач, `bd ready` — готовая к взятию работа | Готовность по графу; «конвои» задач | Mayor/Witness/Polecats; планировщик с лимитом `max_polecats` | Refinery: очередь вливаний в стиле Bors, гейты проверки, бисекция | Нет как есть: тяжёлая инфраструктура (Go, Dolt, tmux, демон); идеи очереди вливаний и `bd ready` — ценны |
| [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) (встроено) | — | экспериментально | — | Да: задача может зависеть от других, блокирована до их закрытия, разблокировка автоматическая | Нет; «самозахват» свободной незаблокированной задачи с файловой блокировкой | Лид назначает или тиммейт берёт сам | Хуки `TaskCompleted`/`TeammateIdle` (exit 2 = вернуть) | Механизм исполнения есть, разложения нет; рекомендуют 3–5 тиммейтов, 5–6 задач на каждого |
| [feature-dev (официальный)](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/feature-dev) | 48k (каталог) | push 2026-11-24 | Apache-2.0 | Нет | Параллельны только разведчики кода (2–3) и ревьюеры | Один исполнитель | Ревью качества в конце | Нет: про один поток реализации |

Прочее, просмотренное и отброшенное: [claude-squad](https://github.com/smtg-ai/claude-squad) (8.9k, AGPL-3.0) и
[Crystal](https://github.com/stravu/crystal) (3.1k, MIT, push 2026-02) — менеджеры параллельных сессий в worktree,
разложения на задачи не делают; [HumanLayer/CodeLayer](https://github.com/humanlayer/humanlayer) (12.9k, Apache-2.0) —
research → plan → implement, один поток.

## Подробно, с проверенными фактами

### GitHub Spec Kit
- Формат задачи: `[ID] [P?] [Story] Description`; `[P]` — «Can run in parallel (different files, no dependencies)»
  ([tasks-template.md](https://github.com/github/spec-kit/blob/main/templates/tasks-template.md)).
- Шаблон фаз: Setup → Foundational («BLOCKS all user stories») → истории P1/P2/P3 → Polish.
  Внутри истории предписан послойный порядок: «Models before services, Services before endpoints,
  Core implementation before integration, Story complete before moving to next priority».
- `/implement`: «Phase-by-phase execution», «Tasks affecting the same files must run sequentially»
  ([implement.md](https://github.com/github/spec-kit/blob/main/templates/commands/implement.md)). Своего
  планировщика исполнителей нет, ревью кода нет; `/converge` сверяет код со спекой и дописывает
  недоделанное в tasks.md.
- Вывод: это и есть источник жалобы. Параллельность по шаблону возникает только (а) между `[P]`-задачами
  одной фазы и (б) между историями после Foundational. Послойный порядок внутри истории и общая
  Foundational-фаза превращают 20–30 задач в длинные цепочки, где одновременно готовы 4–5.

### Task Master
- Задачи с явными `dependencies`, команды `next`, `expand`, `analyze_project_complexity`, теги-потоки
  ([README](https://github.com/eyaltoledano/claude-task-master)).
- Параллельность — агент `task-orchestrator` в плагине: «build and maintain a mental model of task dependencies»,
  «Never assign dependent tasks to different executors simultaneously»
  ([task-orchestrator.md](https://github.com/eyaltoledano/claude-task-master/blob/main/packages/claude-code-plugin/agents/task-orchestrator.md)).
  То есть граф хранится в инструменте, а расписание — в голове LLM.
- Лицензия MIT с Commons Clause (нельзя продавать как услугу). Последний коммит 2026-04-23, релиз 2026-03-31;
  документация переехала на tryhamster.com — продукт уходит в коммерческое русло.

### CCPM
- PRD → эпик → задачи (≤10 на эпик), у задачи `depends_on`, `parallel`, `conflicts_with`; синхронизация в
  GitHub Issues; worktree на эпик ([README](https://github.com/automazeio/ccpm)).
- Главная идея: «Issues Aren't Atomic» — одна задача режется на потоки (БД, сервис, API, UI, тесты), каждый
  агент работает «ONLY in your assigned files», все в одном worktree
  ([execute.md](https://github.com/automazeio/ccpm/blob/main/skill/ccpm/references/execute.md)).
- Этапа ревью нет вовсе; в SKILL.md прямо «Do NOT use for: ... reviewing PRs». Таблица «5 агентов — 1x времени»
  в README — маркетинговая оценка, не замер.

### obra/superpowers
- writing-plans: задачи по 2–5 минут с точными путями и кодом; subagent-driven-development: свежий
  исполнитель на задачу, ревью «spec compliance + code quality» после каждой, финальное ревью ветки.
- Прямой запрет параллели: «Never dispatch multiple implementation subagents in parallel (conflicts)»
  ([SKILL.md, строка ~235](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md)).
  Параллельность есть только в `dispatching-parallel-agents` — для независимых расследований/починок, не для фичи.
- Вывод: эталон качества ревью, анти-эталон по времени — ровно тот цикл «исполнитель → ревьюер → второй круг»,
  на который жалуется пользователь, причём строго последовательно.

### BMAD-METHOD и bmad-loop
- BMAD: агенты-роли (analyst, pm, architect, po, dev), эпики → истории; v7 в альфе.
- bmad-loop: «pick story → implement → adversarially review → verify → commit», затем следующая история;
  управление — обычный Python, а не LLM; ревью — отдельная свежая сессия, не более `max_review_cycles` (3);
  «One board writer»; опционально worktree на историю ([README](https://github.com/bmad-code-org/bmad-loop)).
- Параллельного исполнения нет. Ценно: ограничение кругов ревью, недоделки уходят в журнал `deferred-work.md`
  вместо бесконечного второго круга.

### Ruflo (claude-flow)
- Обвязка «100+ specialized agents, coordinated swarms, self-learning memory, federated comms»; плагин
  `ruflo-swarm` даёт worktree на агента и общий трекер задач; `ruflo-goals` — GOAP-планирование
  ([README](https://github.com/ruvnet/ruflo), [ruflo-swarm](https://github.com/ruvnet/ruflo/blob/main/plugins/ruflo-swarm/README.md)).
- Слишком велик и непрозрачен для базы, которая ставится «на любой проект без подготовки»; разложение фичи
  на независимые части не является его центральной функцией.

### wshobson/agents → agent-teams
- `/team-feature`: «Decomposes the feature into work streams with file ownership boundaries, gets your approval,
  then spawns implementers to build in parallel»; `/team-review` — параллельные ревьюеры по измерениям
  ([README](https://github.com/wshobson/agents/blob/main/plugins/agent-teams/README.md)).
- Скил parallel-feature-development: владение файлами (по каталогам, модулям, слоям), **контракты интерфейсов**
  (файл типов принадлежит лиду, исполнители только импортируют), выбор «вертикальный срез vs горизонтальный слой»,
  при этом прямо отмечено, что горизонтальные слои дают больше точек интеграции
  ([SKILL.md](https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/parallel-feature-development/SKILL.md)).
- Это самые близкие к нужному принципы, но реализация — тексты для LLM поверх экспериментальных Agent Teams;
  никакой проверки, что разложение действительно даёт ширину 4–5, нет.

### am-will/swarms
- swarm-planner требует от каждой задачи явных зависимостей, план проверяет сабагент; parallel-task исполняет
  волнами и проверяет работу между волнами ([README](https://github.com/am-will/swarms)).
- Сами авторы называют цену: «Swarms trades some parallelism for simplicity. Waves execute sequentially» —
  волна ждёт самую медленную задачу. 250 звёзд, лицензия не указана.

### Gas Town + Beads
- Beads — граф задач на Dolt, `bd ready` выдаёт работу без открытых блокеров, `bd update --claim` — захват
  ([README beads](https://github.com/gastownhall/beads)).
- Gas Town: работники Polecats, менеджер Witness ловит зависших, **Refinery** — очередь вливаний: «batches merge
  requests, runs verification gates, and merges to main using a Bors-style bisecting queue», упавшие изолируются
  и переотправляются; Scheduler ограничивает число одновременных работников
  ([README gastown](https://github.com/gastownhall/gastown)).
- Требует Go-инструменты, Dolt, sqlite3, tmux, демон — нарушает правило базы «только bash, git, python3».
  Идеи (готовность по графу, очередь вливаний с проверками вне критического пути исполнителя) — переносимы.

### Claude Code Agent Teams (встроенная возможность)
- Экспериментально (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). Общий список задач: pending / in progress /
  completed; «A task can also depend on other tasks and shows as blocked ... until they're completed»;
  тиммейт после своей задачи сам берёт следующую незаблокированную, захват — с файловой блокировкой
  ([документация](https://code.claude.com/docs/en/agent-teams)).
- Рекомендации документации: «Start with 3-5 teammates», «5-6 tasks per teammate», «Two teammates editing the same
  file leads to overwrites. Break the work so each teammate owns a different set of files»; для «sequential tasks,
  same-file edits, or work with many dependencies» команды неэффективны.
- Хуки `TaskCreated`, `TaskCompleted`, `TeammateIdle` (exit 2 возвращает работу) — точка для гейтов ревью.
- Ограничения: статус задачи может отставать и держать зависимые заблокированными; нет возобновления сессии
  с in-process тиммейтами; одна команда на сессию.

## Оценка: годится ли что-то как есть

Готового решения проблемы пользователя нет. Причина одна для всех: инструменты либо **исполняют** граф
(Agent Teams, Beads, Task Master, swarms), либо **описывают** формат задач (Spec Kit, CCPM), но ни один не
**проверяет и не перестраивает форму разложения** так, чтобы ширина графа была 4–5 на всём протяжении фичи.
Ширина определяется на этапе разложения, а не исполнения: если tasks.md — цепочка, никакой оркестратор её не
распараллелит.

По двум жалобам:
1. **Узкий граф.** Источник — послойный шаблон Spec Kit (модели → сервисы → эндпоинты, общая Foundational-фаза).
   Переносимые лекарства из найденного: контракты интерфейсов первыми и отдельной задачей (wshobson agent-teams),
   вертикальные срезы вместо слоёв, владение файлами и `conflicts_with` (CCPM), явные зависимости у каждой задачи
   и проверка плана до старта (swarms). Чего нет нигде и что придётся делать: измерение ширины/критического пути
   графа как гейт разложения.
2. **Последовательный цикл ревью внутри задачи.** Superpowers и bmad-loop делают его строго последовательно
   (у bmad-loop хотя бы предел 3 круга и журнал отложенного). Переносимое: ревью как отдельная очередь вне пути
   исполнителя (Refinery в Gas Town), исполнитель берёт следующую задачу, пока прежняя на ревью; мелкие замечания
   уходят в журнал, а не во второй круг (bmad-loop `deferred-work.md`); параллельное ревью по измерениям
   (wshobson `/team-review`, пример в документации Agent Teams).

Ограничение рамок базы: конвейер фич — чужой (ADR-0010), Spec Kit уже стоит у проектов. Значит, правка — не замена
Spec Kit, а надстройка над его tasks.md (форма разложения + проверка ширины) и над уже существующей механикой
параллельных пар исполнитель/ревьюер. Все кандидаты требуют серьёзной доработки либо противоречат правилу
зависимостей базы (Gas Town, Ruflo, Task Master — Node/Go/Dolt).
