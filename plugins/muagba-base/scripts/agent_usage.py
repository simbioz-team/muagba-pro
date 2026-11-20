#!/usr/bin/env python3
"""Сводка по стенограмме сабагента: модель, effort, токены, время.

Зачем: выбирать модель под класс задачи можно только по данным, а данные
жили лишь в стенограммах, которые Claude Code удаляет через 30 дней
(`cleanupPeriodDays`). Журнал агентов живёт дольше и без стенограмм
отвечает, какой моделью и за сколько сделан запуск.

Итоги накопительные на момент SubagentStop: сабагент, продолженный
через SendMessage, останавливается снова, и последняя запись по его
`agent_id` — итог. Цену не считаем: прайс меняется, токены — нет.

Размер задачи — `requests`, `compactions` и `ctx_max` (наибольший контекст
запроса). Каждый запрос перечитывает весь контекст, поэтому цена задачи
растёт быстрее её длины: у исполнителей за 13–20.11 88% цены пришлось на
запросы с контекстом больше 120K. Уплотнение больше одного раза — признак
задачи, которую стоило резать (правило «Кому отдать работу»).

Запросы считаются по `requestId`: один ответ модели пишется в стенограмму
несколькими записями (текст, вызовы инструментов), и usage у них общий.
"""
from __future__ import annotations

import json
import sys


def summarize(path: str) -> dict:
    seen: dict[str, dict] = {}
    models: list[str] = []
    effort = None
    first = last = None
    compactions = 0
    ctx_max = 0
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return {}
    with f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ts = e.get("timestamp")
            if ts:
                first = first or ts
                last = ts
            if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
                compactions += 1
                continue
            m = e.get("message")
            if e.get("type") != "assistant" or not isinstance(m, dict):
                continue
            model = m.get("model")
            if not model or model.startswith("<"):
                continue
            if not models or models[-1] != model:
                models.append(model)
            if e.get("effort"):
                effort = e["effort"]
            u = m.get("usage")
            if isinstance(u, dict):
                seen[e.get("requestId") or m.get("id") or str(len(seen))] = u
                ctx_max = max(ctx_max, sum(int(u.get(k) or 0) for k in (
                    "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")))
    if not seen:
        return {}
    tot = {k: sum(int(u.get(k) or 0) for u in seen.values()) for k in (
        "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
        "output_tokens")}
    out = {"model": models[-1], "effort": effort, "requests": len(seen),
           "tok_in": tot["input_tokens"], "tok_cache_read": tot["cache_read_input_tokens"],
           "tok_cache_write": tot["cache_creation_input_tokens"],
           "tok_out": tot["output_tokens"], "first_ts": first, "last_ts": last,
           "compactions": compactions, "ctx_max": ctx_max}
    if len(set(models)) > 1:
        out["models"] = sorted(set(models))
    return out


if __name__ == "__main__":
    print(json.dumps(summarize(sys.argv[1]) if len(sys.argv) > 1 else {}))
