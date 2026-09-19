#!/usr/bin/env bash
# SessionStart (matcher: compact)
# После компакции детали теряются. Возвращаем инварианты в контекст:
# stdout SessionStart-хука добавляется как текст, который агент видит.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

# Рабочая директория, а не project_dir: в worktree-сессии инварианты берутся
# из дерева, в котором агент работает.
FILE="$(work_dir)/.claude/invariants.md"
[ -f "$FILE" ] || exit 0

echo "Напоминание после компакции — инварианты проекта, которые нельзя терять:"
# HTML-комментарии написаны автору файла, а не агенту. Возвращать их в
# контекст — тратить его на инструкцию, которая агенту не адресована.
sed '/<!--/,/-->/d' "$FILE" | sed '/^[[:space:]]*$/d'
exit 0
