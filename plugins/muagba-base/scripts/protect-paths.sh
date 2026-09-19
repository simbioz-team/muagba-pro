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
  # Шаблон с префиксом '+' означает «записывается один раз»: создать файл
  # можно, изменить уже созданный — нет. Нужно каталогам вроде docs/sources/,
  # куда материал приносят, но потом не правят. Обычный шаблон так не годится:
  # он ловит и Write, и тогда положить туда что-либо вообще нельзя.
else
  # Значения по умолчанию, если проект не завёл свой список.
  PATTERNS=(".env" ".git/" "package-lock.json" "uv.lock" "poetry.lock" "yarn.lock")
fi

for p in "${PATTERNS[@]}"; do
  WRITE_ONCE=0
  case "$p" in
    +*) WRITE_ONCE=1; p="${p#+}" ;;
  esac
  [ -z "$p" ] && continue
  [[ "$FILE_PATH" == *"$p"* ]] || continue

  if [ "$WRITE_ONCE" -eq 1 ]; then
    # Файла ещё нет — это создание, оно разрешено.
    [ -e "$FILE_PATH" ] || continue
    cat >&2 <<MSG
Запрещено: $FILE_PATH попадает под шаблон '$p' — записывается один раз.
Что делать: этот файл менять нельзя, его правят только руками человека.
Если содержимое устарело — принеси новую версию отдельным файлом, а старую
пометь как устаревшую. Исправления по существу идут в документы проекта.
MSG
    exit 2
  fi

  cat >&2 <<MSG
Запрещено: $FILE_PATH попадает под защищённый шаблон '$p'.
Что делать: если правка действительно нужна — попроси человека внести её
самому либо снять шаблон из .claude/protected-paths.txt. Не обходи запрет
через Bash: он проверяется отдельно.
MSG
  exit 2
done
exit 0
