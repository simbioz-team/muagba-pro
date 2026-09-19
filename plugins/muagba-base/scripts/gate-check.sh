#!/usr/bin/env bash
# Stop: гейт завершения хода.
# Запускает .claude/check.sh проекта. Нет файла — гейта нет, exit 0.
# Claude Code перебивает Stop-хук после 8 подряд блокировок, так что
# вечного цикла не будет.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

# Важно: берём cwd из входа, а не CLAUDE_PROJECT_DIR. В worktree-сессии
# агент работает в своём дереве, и проверять надо именно его.
WORK=$(work_dir)
CHECK="$WORK/.claude/check.sh"
[ -x "$CHECK" ] || exit 0

OUTPUT=$(cd "$WORK" && bash "$CHECK" 2>&1)
STATUS=$?
[ $STATUS -eq 0 ] && exit 0

{
  echo "Гейт не пройден: .claude/check.sh завершился с кодом $STATUS."
  echo "Ход не может быть закрыт, пока проверка красная."
  echo "--- последние 50 строк вывода ---"
  printf '%s\n' "$OUTPUT" | tail -n 50
  echo "--- ---"
  echo "Что делать: исправь причину, а не подавляй симптом. Если проверка"
  echo "падает не из-за твоих правок — скажи об этом человеку и остановись."
} >&2
exit 2
