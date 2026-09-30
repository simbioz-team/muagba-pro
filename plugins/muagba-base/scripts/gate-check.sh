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
#
# Уже проверенное зелёным заново не проверяется. У координатора ход
# кончается постоянно — отдал задачу и ждёт, прочитал, ответил человеку, —
# и гейт гонял полный check.sh впустую: у narta за этап 1.4 это 131 прогон,
# 651 минута, 130 зелёных. После зелёного прогона запоминается отпечаток
# дерева (gate_key.py: HEAD, изменения, неотслеживаемые файлы); совпал —
# ход отпускается без прогона. Изменения вне git (база, окружение, файлы
# из .gitignore) отпечаток не видит. MUAGBA_GATE_ALWAYS=1 — проверять
# всегда.
#
# Проверка ограничена по времени самим гейтом: MUAGBA_GATE_TIMEOUT секунд
# (по умолчанию 1500), с запасом до тайм-аута хука в hooks.json (1800).
# Хук, оборванный Claude Code по тайм-ауту, агента молча отпускает — так
# у narta гейт исполнителя не работал вовсе: check.sh шёл 13–17 минут при
# тайм-ауте хука 600 с. Не уложилась — ход отпускается (держать медленную,
# но, может быть, зелёную проверку значит крутить агента до предела в 8
# блокировок), но человек видит предупреждение, а журнал — decision=timeout.
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

KEYPY="$(dirname "${BASH_SOURCE[0]}")/gate_key.py"
# Файл отпечатка — в каталоге git этого дерева, а не в рабочем дереве:
# иначе он сам менял бы отпечаток. У рабочих деревьев git-path свой.
GREEN=$(git -C "$WORK" rev-parse --git-path muagba-gate-green 2>/dev/null)
case "$GREEN" in ''|/*) ;; *) GREEN="$WORK/$GREEN" ;; esac
KEY=""
[ -n "$GREEN" ] && [ -z "${MUAGBA_GATE_ALWAYS:-}" ] && KEY=$(python3 "$KEYPY" key "$WORK" 2>/dev/null)
if [ -n "$KEY" ] && [ "$(cat "$GREEN" 2>/dev/null)" = "$KEY" ]; then
  log_event gate decision=cached
  exit 0
fi

# Своя отсечка по времени — python, а не coreutils timeout: его нет на
# macOS. Проверка идёт в своей группе процессов и убивается целиком:
# pytest и браузер e2e иначе переживают check.sh.
OUTPUT=$(cd "$WORK" && python3 -c '
import os, signal, subprocess, sys
p = subprocess.Popen(["bash", sys.argv[2]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     start_new_session=True)
try:
    out, _ = p.communicate(timeout=float(sys.argv[1]))
except subprocess.TimeoutExpired:
    os.killpg(p.pid, signal.SIGKILL)
    out, _ = p.communicate()
    sys.stdout.buffer.write(out)
    sys.exit(124)
sys.stdout.buffer.write(out)
sys.exit(p.returncode)' "${MUAGBA_GATE_TIMEOUT:-1500}" "$CHECK")
STATUS=$?
if [ $STATUS -eq 124 ]; then
  [ -n "$GREEN" ] && rm -f "$GREEN" 2>/dev/null
  python3 -c '
import json, sys
print(json.dumps({"systemMessage":
    f"Внимание: гейт хода не дождался .claude/check.sh — не уложился в {sys.argv[1]} с. "
    "Зелёная ли проверка, неизвестно: ход отпущен без неё. Ускорьте check.sh "
    "или поднимите MUAGBA_GATE_TIMEOUT (и timeout хука)."}, ensure_ascii=False))' \
    "${MUAGBA_GATE_TIMEOUT:-1500}"
  log_event gate decision=timeout limit_s="${MUAGBA_GATE_TIMEOUT:-1500}"
  exit 0
fi
if [ $STATUS -eq 0 ]; then
  # Запоминаем, только если проверка сама не поменяла дерево: иначе
  # зелёным оказалось бы состояние, которое она не проверяла.
  if [ -n "$KEY" ] && [ "$(python3 "$KEYPY" key "$WORK" 2>/dev/null)" = "$KEY" ]; then
    printf '%s' "$KEY" > "$GREEN" 2>/dev/null
  fi
  exit 0
fi
[ -n "$GREEN" ] && rm -f "$GREEN" 2>/dev/null

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
