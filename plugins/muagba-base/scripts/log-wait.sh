#!/usr/bin/env bash
# PermissionRequest и PostToolUse (Bash) — где автономная работа стоит.
#
# PermissionRequest: Claude Code вот-вот спросит человека. Ночью это
# простой до утра, и ни журнал, ни уведомление его не отмечали — проект
# narta нашёл его, только проснувшись. Пишем событие `wait`; время простоя —
# до следующего события этой сессии в журнале. Решения не возвращаем:
# хук только наблюдает.
#
# PostToolUse: команда шла дольше MUAGBA_SLOW_MS (по умолчанию 60 с) —
# событие `slow`, чтобы видеть, куда уходит время.
#
# В журнал — класс команды (`git push+gh pr`), не её текст.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

TOOL=$(jq_get tool_name)
CLASS="$TOOL"
if [ "$TOOL" = "Bash" ]; then
  CLASS=$(jq_get tool_input.command | python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
from shell_split import command_class
print(command_class(sys.stdin.read()) or "Bash")' "$(dirname "${BASH_SOURCE[0]}")")
fi

case "$(jq_get hook_event_name)" in
  PermissionRequest)
    log_event wait tool="$TOOL" class="$CLASS"
    ;;
  PostToolUse)
    MS=$(jq_get duration_ms)
    case "$MS" in ''|*[!0-9]*) exit 0 ;; esac
    [ "$MS" -ge "${MUAGBA_SLOW_MS:-60000}" ] && log_event slow tool="$TOOL" class="$CLASS" duration_ms="$MS"
    ;;
esac
exit 0
