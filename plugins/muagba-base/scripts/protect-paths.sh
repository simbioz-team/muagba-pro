#!/usr/bin/env bash
# PreToolUse: Edit|Write|NotebookEdit
# Блокирует правку защищённых путей. exit 2 = запрет, агент получает причину.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

FILE_PATH=$(jq_get tool_input.file_path)
[ -z "$FILE_PATH" ] && exit 0
FILE_PATH="${FILE_PATH//\\//}"   # нормализуем разделители Windows

LIST="$(project_dir)/.claude/protected-paths.txt"

if [ -f "$LIST" ]; then
  PATTERNS=()
  while IFS= read -r line; do
    line="${line%%#*}"; line="${line// /}"
    [ -n "$line" ] && PATTERNS+=("$line")
  done < "$LIST"
else
  # Значения по умолчанию, если проект не завёл свой список.
  PATTERNS=(".env" ".git/" "package-lock.json" "uv.lock" "poetry.lock" "yarn.lock")
fi

for p in "${PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$p"* ]]; then
    cat >&2 <<MSG
Запрещено: $FILE_PATH попадает под защищённый шаблон '$p'.
Что делать: если правка действительно нужна — попроси человека внести её
самому либо снять шаблон из .claude/protected-paths.txt. Не обходи запрет
через Bash: он проверяется отдельно.
MSG
    exit 2
  fi
done
exit 0
