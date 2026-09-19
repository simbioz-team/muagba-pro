# Роли этого проекта

Базовые роли (`implementer`, `reviewer`, `researcher`) приходят с плагином
`muagba-base`. Сюда кладутся роли, специфичные для проекта.

Приоритет: managed → флаг `--agents` → `.claude/agents/` (здесь) →
`~/.claude/agents/` → плагин. Файл с тем же `name` перекрывает плагинный.

Пример:

```markdown
---
name: migration-writer
description: Пишет и проверяет миграции схемы
tools: Read, Edit, Bash
isolation: worktree
---
<инструкции>
```
