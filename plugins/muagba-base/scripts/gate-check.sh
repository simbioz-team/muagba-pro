#!/usr/bin/env bash
# Stop и SubagentStop: гейт завершения хода.
# Запускает .claude/check.sh проекта. Нет файла — гейта нет, exit 0.
# Claude Code перебивает Stop-хук после 8 подряд блокировок, так что
# вечного цикла не будет.
#
# На сабагенте — только у того, кто сдаёт код. Раньше SubagentStop гейта не
# имел вовсе: implementer гонял проверку лишь потому, что так написано в его
# промпте, то есть по просьбе, а не по механике. У проверяющего и
# исследователя проверять нечего — они не правят код. Исполнитель базы
# держится по имени; роль проекта — по свойству (gate_scope.py): в её
# дереве есть то, чего нет в дереве сессии. По одному имени narta-вская
# implementer-high сдавала задачи без гейта с этапа 1.4.
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
# 651 минута, 130 зелёных. Отпечаток — хеш дерева рабочих файлов
# (gate_key.py), а не HEAD: коммит без правок — не новое дерево. Зелёные
# деревья пишутся в общий список всех рабочих деревьев репозитория
# ($(git rev-parse --git-common-dir)/muagba-gate-green): ff-слияние в дерево
# координатора приносит дерево, уже проверенное гейтом исполнителя. У narta
# на спеке 022 эти два случая — 43 лишних прогона, ~3 ч. Изменения вне git
# (база, окружение, файлы из .gitignore) отпечаток не видит.
# MUAGBA_GATE_ALWAYS=1 — проверять всегда.
#
# Проверка знает, кто её вызвал: MUAGBA_GATE_EVENT=Stop|SubagentStop. Проект
# может в ходе координатора гонять только быстрое (см. каркас check.sh).
# Поэтому сдаче исполнителя засчитывается только зелёное SubagentStop, а
# ходу координатора — любое: каркас исходит из того, что часть Stop не шире
# части SubagentStop.
#
# Что изменилось с последнего зелёного дерева этого рабочего дерева, гейт
# передаёт проверке: MUAGBA_GATE_BASE — то дерево, MUAGBA_GATE_CHANGED —
# файл со списком путей, по строке. Дорогие условные шаги (замеры вёрстки
# у narta) проект решает по нему, а не по всей ветке: ветка фичи трогает
# всё, и у narta замеры шли на каждом прогоне — 4 мин из 5. Зелёного
# дерева нет или оно потеряно — переменных нет, проект решает как прежде.
#
# Остановка «жду свой фоновый прогон» — не сдача: агент проснётся по
# уведомлению и остановится снова. Такие остановки гейт не держит и
# ничего не гоняет (decision=deferred), если во входе хука есть живые
# фоновые задачи самого агента (gate_key.py waiting). У narta на спеке 022
# это 22 прогона, ~1,5 ч нагрузки рядом с его же тестами. Предел: агент,
# оставивший бесконечную фоновую задачу, на каждой остановке ждёт, и гейт
# не идёт, пока она жива; MUAGBA_GATE_ALWAYS=1 снимает и это.
#
# Каждый прогон — в журнал с длительностью: decision=pass|block|timeout|
# released_on_question и duration_ms; пропуски — cached и deferred.
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
    # Служебные вызовы Claude Code — без роли, кода не сдают.
    '') exit 0 ;;
    # Роль проекта: держим, если она сдаёт код — см. gate_scope.py.
    *) python3 "$(dirname "${BASH_SOURCE[0]}")/gate_scope.py" "$(jq_get cwd)" \
         "$(jq_get transcript_path)" "$(project_dir)" || exit 0 ;;
  esac
fi

# Важно: берём cwd из входа, а не CLAUDE_PROJECT_DIR. В worktree-сессии
# агент работает в своём дереве, и проверять надо именно его.
WORK=$(work_dir)
CHECK="$WORK/.claude/check.sh"
[ -x "$CHECK" ] || exit 0

KEYPY="$(dirname "${BASH_SOURCE[0]}")/gate_key.py"
if [ -z "${MUAGBA_GATE_ALWAYS:-}" ]; then
  WAIT=$(printf '%s' "$HOOK_INPUT" | python3 "$KEYPY" waiting 2>/dev/null)
  if [ -n "$WAIT" ]; then
    log_event gate decision=deferred background="$WAIT"
    exit 0
  fi
fi

# Список зелёных — в общем каталоге git всех рабочих деревьев; последнее
# зелёное этого дерева — в его собственном каталоге git. Оба вне рабочего
# дерева: иначе они сами меняли бы отпечаток.
gitpath() {  # <аргументы rev-parse> → абсолютный путь или пусто
  local p
  p=$(git -C "$WORK" rev-parse "$@" 2>/dev/null) || return 0
  case "$p" in ''|/*) printf '%s' "$p" ;; *) printf '%s' "$WORK/$p" ;; esac
}
LEDGER=$(gitpath --git-common-dir); [ -n "$LEDGER" ] && LEDGER="$LEDGER/muagba-gate-green"
LAST=$(gitpath --git-path muagba-gate-last)
# Чьё зелёное засчитывается этому событию.
case "$EVENT" in
  SubagentStop) ACCEPT="SubagentStop" ;;
  *) ACCEPT="$EVENT SubagentStop" ;;
esac
green_has() {  # <дерево> → 0, если оно зелёное для этого события
  [ -f "$LEDGER" ] || return 1
  local e
  for e in $ACCEPT; do grep -qxF -- "$1 $e" <(cut -d' ' -f1,2 "$LEDGER") && return 0; done
  return 1
}
remember() {  # <дерево> <событие> — записать зелёное
  printf '%s %s %s\n' "$1" "$2" "$(date +%s)" >> "$LEDGER" 2>/dev/null
  printf '%s %s\n' "$1" "$2" > "$LAST" 2>/dev/null
  # Список растёт с каждым зелёным: держим последние 1000 строк.
  if [ "$(wc -l < "$LEDGER" 2>/dev/null || echo 0)" -gt 2000 ]; then
    tail -n 1000 "$LEDGER" > "$LEDGER.$$" 2>/dev/null && mv -f "$LEDGER.$$" "$LEDGER" 2>/dev/null
  fi
}

KEY=""
[ -n "$LEDGER" ] && [ -n "$LAST" ] && [ -z "${MUAGBA_GATE_ALWAYS:-}" ] && KEY=$(python3 "$KEYPY" key "$WORK" 2>/dev/null)
if [ -n "$KEY" ] && green_has "$KEY"; then
  # Последним зелёным этого дерева становится принесённое: следующий
  # прогон сравнивает с ним.
  printf '%s %s\n' "$KEY" "$EVENT" > "$LAST" 2>/dev/null
  log_event gate decision=cached
  exit 0
fi

# Последнее зелёное этого дерева, засчитанное событию, — база для
# MUAGBA_GATE_CHANGED. Объект дерева мог уйти с git gc — тогда базы нет.
BASE="" CHANGED=""
if [ -n "$KEY" ] && [ -f "$LAST" ]; then
  read -r LTREE LEVENT < "$LAST"
  case " $ACCEPT " in *" ${LEVENT:-} "*)
    if git -C "$WORK" cat-file -e "${LTREE:-x}^{tree}" 2>/dev/null; then
      CHANGED=$(mktemp "${TMPDIR:-/tmp}/muagba-gate-changed.XXXXXX") || CHANGED=""
      if [ -n "$CHANGED" ] && python3 "$KEYPY" changed "$WORK" "$LTREE" "$KEY" > "$CHANGED" 2>/dev/null; then
        BASE=$LTREE
      else
        rm -f "$CHANGED"; CHANGED=""
      fi
    fi ;;
  esac
fi
trap '[ -n "$CHANGED" ] && rm -f "$CHANGED"' EXIT

# Своя отсечка по времени — python, а не coreutils timeout: его нет на
# macOS. Проверка идёт в своей группе процессов и убивается целиком:
# pytest и браузер e2e иначе переживают check.sh.
START_MS=$(python3 -c 'import time;print(int(time.time()*1000))')
OUTPUT=$(cd "$WORK" && env MUAGBA_GATE_EVENT="$EVENT" \
  ${BASE:+"MUAGBA_GATE_BASE=$BASE" "MUAGBA_GATE_CHANGED=$CHANGED"} python3 -c '
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
DUR=$(( $(python3 -c 'import time;print(int(time.time()*1000))') - START_MS ))
if [ $STATUS -eq 124 ]; then
  python3 -c '
import json, sys
print(json.dumps({"systemMessage":
    f"Внимание: гейт хода не дождался .claude/check.sh — не уложился в {sys.argv[1]} с. "
    "Зелёная ли проверка, неизвестно: ход отпущен без неё. Ускорьте check.sh "
    "или поднимите MUAGBA_GATE_TIMEOUT (и timeout хука)."}, ensure_ascii=False))' \
    "${MUAGBA_GATE_TIMEOUT:-1500}"
  log_event gate decision=timeout limit_s="${MUAGBA_GATE_TIMEOUT:-1500}" duration_ms="$DUR"
  exit 0
fi
if [ $STATUS -eq 0 ]; then
  # Запоминаем, только если проверка сама не поменяла дерево: иначе
  # зелёным оказалось бы состояние, которое она не проверяла.
  if [ -n "$KEY" ] && [ "$(python3 "$KEYPY" key "$WORK" 2>/dev/null)" = "$KEY" ]; then
    remember "$KEY" "$EVENT"
  fi
  log_event gate decision=pass duration_ms="$DUR" ${BASE:+changed="$(wc -l < "$CHANGED" | tr -d ' ')"}
  exit 0
fi

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
  log_event gate decision=released_on_question code="$STATUS" failed_at="$FAILED_AT" duration_ms="$DUR"
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
log_event gate decision=block code="$STATUS" failed_at="$FAILED_AT" duration_ms="$DUR"
exit 2
