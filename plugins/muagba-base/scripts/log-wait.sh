#!/usr/bin/env bash
# PermissionRequest и PostToolUse (Bash) — где автономная работа стоит.
#
# PermissionRequest: Claude Code вот-вот спросит человека. Ночью это
# простой до утра, и ни журнал, ни уведомление его не отмечали — проект
# narta нашёл его, только проснувшись. Пишем событие `wait`; время простоя —
# до следующего события того же агента, не считая SubagentStart/Stop
# работающих рядом сабагентов (так считает preflight). Решения не
# возвращаем: хук только наблюдает.
#
# PostToolUse: команда шла дольше MUAGBA_SLOW_MS (по умолчанию 60 с) —
# событие `slow`, чтобы видеть, куда уходит время.
#
# В журнал — класс команды (`git push+gh pr`), не её текст.
#
# Ночной режим (MUAGBA_MODE=night, ставит лаунчер .claude/claude-night,
# ADR-0016): спрашивать некого, и вопрос висел бы до утра — так ночные
# прогоны вставали через полчаса после начала. Всё, что дошло до вопроса
# человеку, получает отказ с причиной, а в .claude/logs/morning.md
# записывается, что агенту было нужно: утром это список вопросов. Вопрос
# агента (AskUserQuestion) пишется целиком — его текст и есть то, что
# спросить. Контролёр ночью — режим auto Claude Code; сюда доходит только
# то, что он сам отдал бы человеку.
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
    # Ночь — переменная от лаунчера или пометка сессии от night_switch.py
    # (ночь в той же сессии, в том же терминале).
    NIGHT="${MUAGBA_MODE:-}"
    SID=$(jq_get session_id)
    if [ "$NIGHT" != night ] && [ -n "$SID" ] && [ -f "$HOME/.claude/muagba-night/sessions/$SID.json" ]; then
      NIGHT=night
    fi
    if [ "$NIGHT" = night ]; then
      log_event night_deferred tool="$TOOL" class="$CLASS"
      MORNING="$(project_dir)/.claude/logs/morning.md"
      [ -d "$(dirname "$MORNING")" ] || MORNING=""
      printf '%s' "$HOOK_INPUT" | python3 -c '
import json, sys, datetime
d = json.load(sys.stdin)
tool, cls, out = d.get("tool_name") or "?", sys.argv[1], sys.argv[2]
inp = d.get("tool_input") or {}
who = d.get("agent_type") or "координатор"
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
if tool == "AskUserQuestion":
    qs = inp.get("questions") or []
    body = "\n".join("  - " + str(q.get("question") or "") + (
        " — варианты: " + "; ".join(str(o.get("label")) for o in q.get("options") or [])
        if q.get("options") else "") for q in qs) or "  - (вопрос без текста)"
    entry = f"- {now} · {who} · вопрос:\n{body}\n"
    msg = ("Ночной режим: человека нет до утра, вопрос записан в .claude/logs/morning.md. "
           "Не жди ответа: прими решение по умолчанию с отметкой «Спросить: да», если оно "
           "обратимо, иначе отложи эту задачу и бери следующую независимую.")
else:
    # Текста команды не пишем — только класс и описание, как в журнале.
    what = inp.get("description") or cls
    entry = f"- {now} · {who} · нужно разрешение: {tool} — {what}\n"
    msg = ("Ночной режим: это действие требует человека, а его нет до утра. Записано в "
           ".claude/logs/morning.md. Не повторяй его в обход и не жди: отложи эту часть "
           "и бери следующую независимую задачу этапа.")
if out:
    with open(out, "a", encoding="utf-8") as f:
        f.write(entry)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                  "decision": {"behavior": "deny", "message": msg}}}, ensure_ascii=False))
' "$CLASS" "$MORNING"
      exit 0
    fi
    log_event wait tool="$TOOL" class="$CLASS"
    ;;
  PostToolUse)
    MS=$(jq_get duration_ms)
    case "$MS" in ''|*[!0-9]*) exit 0 ;; esac
    [ "$MS" -ge "${MUAGBA_SLOW_MS:-60000}" ] && log_event slow tool="$TOOL" class="$CLASS" duration_ms="$MS"
    ;;
esac
exit 0
