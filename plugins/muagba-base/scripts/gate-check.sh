#!/usr/bin/env bash
# Stop и SubagentStop: гейт завершения хода.
# Запускает .claude/check.sh проекта. Нет файла — гейта нет, exit 0.
# Claude Code перебивает Stop-хук после 8 подряд блокировок, так что
# вечного цикла не будет.
#
# На сабагенте — только у исполнителя. Раньше SubagentStop гейта не имел
# вовсе: implementer гонял проверку лишь потому, что так написано в его
# промпте, то есть по просьбе, а не по механике. У проверяющего и
# исследователя проверять нечего — они не правят код.
#
# Остановка ради вопроса гейтом не держится. Гейт существует, чтобы агент
# не доложил «готово» при красной проверке. Агент, сделавший полдела и
# спрашивающий человека, «готово» не докладывает — а держать его значит
# заставить чинить вместо того, чтобы спросить. Красноту при этом не
# прячем: человек получает предупреждение. Нашёл проект narta на Э5–Э7.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

EVENT=$(jq_get hook_event_name)
# Каждое закрытие хода основной сессии — в журнал: без этого нечем
# откалибровать границу ходов в условии /goal. SubagentStop пишет log-agent.sh.
[ "$EVENT" = "Stop" ] && log_event turn
if [ "$EVENT" = "SubagentStop" ]; then
  case "$(jq_get agent_type)" in
    implementer|*:implementer) ;;
    *) exit 0 ;;
  esac
fi

# Важно: берём cwd из входа, а не CLAUDE_PROJECT_DIR. В worktree-сессии
# агент работает в своём дереве, и проверять надо именно его.
WORK=$(work_dir)
CHECK="$WORK/.claude/check.sh"
[ -x "$CHECK" ] || exit 0

OUTPUT=$(cd "$WORK" && bash "$CHECK" 2>&1)
STATUS=$?
[ $STATUS -eq 0 ] && exit 0

# Где упало: последняя строка-заголовок уровня `==> …`, если check.sh их
# печатает, иначе последняя непустая строка вывода. Повторяющаяся причина
# в журнале — кандидат в урок или правило.
FAILED_AT=$(printf '%s\n' "$OUTPUT" | python3 -c '
import sys
lines = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
heads = [l for l in lines if l.startswith("==>")]
print((heads or lines or [""])[-1][:200])')

# Вопрос — последняя непустая строка ответа кончается «?». Обёртки разметки
# и закрывающие кавычки не мешают.
if printf '%s' "$(jq_get last_assistant_message)" | python3 -c '
import sys
lines = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
sys.exit(0 if lines and lines[-1].rstrip("*_`»\")» ").endswith("?") else 1)
'; then
  python3 -c '
import json, sys
print(json.dumps({"systemMessage":
    f"Внимание: .claude/check.sh красный (код {sys.argv[1]}). Агент остановился "
    "ради вопроса, а не доложил готовность — работа не закончена."},
    ensure_ascii=False))' "$STATUS"
  log_event gate decision=released_on_question code="$STATUS" failed_at="$FAILED_AT"
  exit 0
fi

{
  echo "Гейт не пройден: .claude/check.sh завершился с кодом $STATUS."
  echo "Ход не может быть закрыт, пока проверка красная."
  echo "--- последние 50 строк вывода ---"
  printf '%s\n' "$OUTPUT" | tail -n 50
  echo "--- ---"
  echo "Что делать: исправь причину, а не подавляй симптом. Если проверка"
  echo "падает не из-за твоих правок или без человека дальше не пройти —"
  echo "задай ему вопрос: остановку ради вопроса гейт не держит, а человек"
  echo "увидит, что проверка красная."
} >&2
log_event gate decision=block code="$STATUS" failed_at="$FAILED_AT"
exit 2
