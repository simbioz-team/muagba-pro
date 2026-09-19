#!/usr/bin/env bash
# SessionStart (matcher: compact)
# После компакции детали теряются. Возвращаем инварианты в контекст:
# stdout SessionStart-хука добавляется как текст, который агент видит.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

FILE="$(project_dir)/.claude/invariants.md"
[ -f "$FILE" ] || exit 0

echo "Напоминание после компакции — инварианты проекта, которые нельзя терять:"
cat "$FILE"
exit 0
