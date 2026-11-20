#!/usr/bin/env bash
# SubagentStart / SubagentStop — журнал запусков.
# Без него в мультиагентном режиме невозможно восстановить, кто что сделал.
# Пишет JSONL и ничего не возвращает в контекст (стоимость контекста — ноль).
# На SubagentStop добавляет сводку стенограммы сабагента — модель, effort,
# токены, время (agent_usage.py): по ним выбирают модель под класс задачи, а
# сами стенограммы Claude Code удаляет через 30 дней. И описание запуска
# из .meta.json: в нём вид работы и шаг (ADR-0020).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

LOG_DIR="$(project_dir)/.claude/logs"
mkdir -p "$LOG_DIR" 2>/dev/null || exit 0

printf '%s' "$HOOK_INPUT" | python3 -c '
import json, sys, datetime
sys.path.insert(0, sys.argv[1])
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
rec = {
    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    "event": d.get("hook_event_name"),
    "agent_id": d.get("agent_id"),
    "agent_type": d.get("agent_type"),
    "session_id": d.get("session_id"),
    "cwd": d.get("cwd"),
}
if d.get("hook_event_name") == "SubagentStop" and d.get("agent_transcript_path"):
    try:
        from agent_usage import summarize
        rec.update(summarize(d["agent_transcript_path"]))
    except Exception:
        pass  # журнал важнее сводки: запись о запуске пишется всегда
    # Описание запуска несёт вид работы и шаг («fix/причина: …») — по ним
    # отчёт сверяет выбор роли с итогом задачи (ADR-0020). Claude Code держит
    # его в .meta.json рядом со стенограммой и удаляет вместе с ней.
    try:
        meta = d["agent_transcript_path"][:-len(".jsonl")] + ".meta.json"
        desc = (json.load(open(meta, encoding="utf-8")).get("description") or "").strip()
        if desc:
            rec["description"] = desc[:200]
    except Exception:
        pass
print(json.dumps(rec, ensure_ascii=False))
' "$(dirname "${BASH_SOURCE[0]}")" >> "$LOG_DIR/agents.jsonl" 2>/dev/null
exit 0
