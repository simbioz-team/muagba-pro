#!/usr/bin/env bash
# SubagentStart / SubagentStop — журнал запусков.
# Без него в мультиагентном режиме невозможно восстановить, кто что сделал.
# Пишет JSONL и ничего не возвращает в контекст (стоимость контекста — ноль).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

LOG_DIR="$(project_dir)/.claude/logs"
mkdir -p "$LOG_DIR" 2>/dev/null || exit 0

printf '%s' "$HOOK_INPUT" | python3 -c '
import json, sys, datetime
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(json.dumps({
    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    "event": d.get("hook_event_name"),
    "agent_id": d.get("agent_id"),
    "agent_type": d.get("agent_type"),
    "session_id": d.get("session_id"),
    "cwd": d.get("cwd"),
}, ensure_ascii=False))
' >> "$LOG_DIR/agents.jsonl" 2>/dev/null
exit 0
