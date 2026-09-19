# Изменения

Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии по [SemVer](https://semver.org/lang/ru/).

> **Пока версия `0.x` минорный номер означает ломающее изменение.**

Версионируется плагин `muagba-base`. Шаблон `template/` версии не имеет: он
копируется один раз и дальше живёт в проекте своей жизнью.

## [0.1.0] — 2026-09-19

Первая версия.

- Плагин `muagba-base`: пять хуков (защита путей, запрет деструктивных
  git-команд, гейт проверки на `Stop`, пере-инъекция инвариантов после
  компакции, журнал агентов), роли `implementer`, `reviewer`, `researcher`,
  скилы `/setup-project`, `/new-feature`, `/write-adr`.
- Шаблон: `AGENTS.md` с обёрткой `CLAUDE.md`, восемь документов рамок, права,
  `.worktreeinclude`, реестры документации, CI.
- `check-frames.py` — сканер незаполненных заготовок.
- Подключение `muagba-base` и `docsys` в шаблоне через `extraKnownMarketplaces`
  и `enabledPlugins`.
