#!/usr/bin/env python3
"""Журнал сессии через сжатие контекста.

Агент не может сам вызвать /compact: ни инструмента, ни хука для этого нет.
Сжимает Claude Code, когда контекст подходит к окну. Задача здесь — чтобы к
этому моменту журнал был записан, а после сжатия агент его перечитал.

Три режима, по одному на хук:

  tick        PostToolUse. Контекст вырос на N токенов с последней записи
              журнала — напомнить агенту обновить журнал.
  postcompact PostCompact. Сохранить выжимку, которую сделал сам Claude Code,
              в .claude/logs/compact/. Страховка: агент мог журнал не дописать.
  reinject    SessionStart (compact). Вернуть агенту путь к журналу и
              указание перечитать его и продолжить.

Включается каталогом docs/journal/ в рабочей директории. Нет каталога —
молчим: база ставится на любой проект без подготовки.

Порог — рост на N токенов, а не процент окна. Размер окна хуку никто не
передаёт: он зависит от модели и настроек (200K, ~967K, autoCompactWindow,
CLAUDE_CODE_AUTO_COMPACT_WINDOW), и угаданное окно промахивалось бы молча.
Рост от последней записи окна знать не требует и одинаково работает на 200K
и на 1M.

Хук PreCompact намеренно не используется. Он умеет запретить сжатие, но
если сжатие запущено уже после ошибки переполнения, запрет роняет запрос —
ночной прогон встал бы.
"""
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

EVERY_DEFAULT = 150_000
# Хвоста хватает, чтобы найти последний ответ модели: transcript на ночном
# прогоне вырастает до сотен мегабайт, читать его целиком на каждый вызов
# инструмента — заметная задержка.
TAIL_BYTES = 1 << 20


def journal_dir(inp):
    cwd = inp.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    d = Path(cwd) / "docs" / "journal"
    return d if d.is_dir() else None


def used_tokens(transcript):
    """Сколько контекста занято: usage последнего ответа основной ветки.

    transcript пишется асинхронно и может отставать на ход — для порога в
    сотню тысяч токенов это неважно.
    """
    try:
        with open(transcript, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL_BYTES))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue  # первая строка хвоста обычно обрезана
        m = e.get("message")
        if e.get("type") != "assistant" or e.get("isSidechain") or not isinstance(m, dict):
            continue
        u = m.get("usage")
        if isinstance(u, dict):
            return sum(int(u.get(k) or 0) for k in (
                "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return None


def entries(jd):
    """Записи журнала: *.md верхнего уровня, кроме README."""
    return [p for p in jd.glob("*.md") if p.name.lower() != "readme.md"]


def newest(jd):
    es = entries(jd)
    return max(es, key=lambda p: p.stat().st_mtime) if es else None


def state_path(inp):
    # Состояние на сессию, не в репозитории: в чужом проекте .claude/logs/
    # может не стоять в .gitignore, и хук наплодил бы неотслеживаемых файлов.
    base = inp.get("scratchpad_dir") or os.path.join(
        tempfile.gettempdir(), f"muagba-journal-{os.getuid()}")
    sid = "".join(c for c in str(inp.get("session_id") or "nosession") if c.isalnum() or c in "-_")
    return Path(base) / f"journal-watch-{sid}.json"


def tick(inp):
    # Сабагент живёт в своём контексте и журнал сессии не ведёт.
    if inp.get("agent_id"):
        return
    jd = journal_dir(inp)
    if not jd:
        return
    used = used_tokens(inp.get("transcript_path") or "")
    if used is None:
        return
    try:
        every = int(os.environ.get("MUAGBA_JOURNAL_EVERY") or EVERY_DEFAULT)
    except ValueError:
        every = EVERY_DEFAULT
    nw = newest(jd)
    mtime = nw.stat().st_mtime if nw else 0.0

    sp = state_path(inp)
    try:
        st = json.loads(sp.read_text())
    except (OSError, ValueError):
        st = None
    if st is None:
        # Первый вызов в сессии: точка отсчёта — то, что есть сейчас.
        st = {"mark": used, "seen": mtime, "nagged": 0}
    else:
        if mtime > st["seen"]:
            # Журнал записан — отсчёт заново.
            st.update(mark=used, seen=mtime, nagged=0)
        if used < st["mark"]:
            # Контекст стал меньше отметки — было сжатие.
            st.update(mark=used, nagged=0)
        grown = used - st["mark"]
        # Проигнорированное напоминание повторяем, но не на каждый вызов
        # инструмента: раз в четверть порога.
        if grown >= every and (not st["nagged"] or used - st["nagged"] >= every // 4):
            st["nagged"] = used
            rule = " по правилу из docs/journal/README.md" if (jd / "README.md").is_file() else ""
            target = f" (последняя запись: docs/journal/{nw.name})" if nw else ""
            msg = (
                f"Контекст вырос на ~{grown // 1000}K токенов с последней записи журнала "
                f"сессии (занято ~{used // 1000}K). Обнови журнал в docs/journal/{target}{rule}: "
                "что сделано, где ошибался и чем поймал, принятые решения, что открыто и "
                "следующий шаг. Сжатие контекста может прийти в любой момент, и всё, чего "
                "нет в журнале, после него придётся восстанавливать. Затем продолжай работу."
            )
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PostToolUse", "additionalContext": msg}}, ensure_ascii=False))
    try:
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(st))
    except OSError:
        pass


def postcompact(inp):
    jd = journal_dir(inp)
    summary = (inp.get("compact_summary") or "").strip()
    if not jd or not summary:
        return
    # Не в docs/: выжимка — сырьё без frontmatter, и система документации
    # роняла на ней свой гейт (нашёл проект narta). .claude/logs/ каркас и
    # так держит в .gitignore.
    raw = jd.parent.parent / ".claude" / "logs" / "compact"
    raw.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    sid = str(inp.get("session_id") or "")[:8]
    p = raw / f"{now:%Y-%m-%d-%H%M%S}-{sid or 'nosession'}.md"
    p.write_text(
        f"# Выжимка сжатия контекста — {now:%Y-%m-%d %H:%M}\n\n"
        f"Сохранена хуком автоматически (trigger: {inp.get('trigger') or '?'}, "
        f"сессия {sid or '?'}). Это сырьё: важное из неё переносится в журнал.\n\n"
        f"{summary}\n",
        encoding="utf-8")


def reinject(inp):
    jd = journal_dir(inp)
    if not jd:
        return
    nw = newest(jd)
    lines = ["Контекст только что сжат. Журнал сессии ведётся в docs/journal/. Прежде чем продолжать:"]
    if nw:
        lines.append(f"1. Перечитай последнюю запись журнала: docs/journal/{nw.name}.")
    else:
        lines.append("1. Записей журнала пока нет — заведи её до продолжения работы.")
    lines.append("2. Выжимка этого сжатия сохраняется в .claude/logs/compact/ — сверь её с "
                 "журналом и перенеси в журнал то, чего там нет.")
    lines.append("3. Продолжай с того, что в журнале названо следующим шагом.")
    print("\n".join(lines))


def main():
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        return
    if not isinstance(inp, dict):
        return
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    {"tick": tick, "postcompact": postcompact, "reinject": reinject}.get(mode, lambda _: None)(inp)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Хук журнала не должен ронять работу: он напоминание, а не гейт.
        pass
