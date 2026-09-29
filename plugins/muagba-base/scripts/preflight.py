#!/usr/bin/env python3
"""Предстартовая проверка автономной сессии: что упрётся в подтверждение.

Ночью вызов инструмента, ждущий подтверждения, просто висит до утра. Проект
narta так и простоял: агент склеивал `git push && gh pr create …` в одну
команду, проектный хук разрешал только одиночные, а `gh issue …` не было в
разрешённых вовсе. Узнали утром. Проверить это можно до ухода человека.

Берёт список рутинных команд этапа — по одной на строку, из файла
`.claude/autonomy-commands.txt` или переданного аргументом — и для каждой
говорит, что будет: пройдёт, спросит или будет запрещена, и почему.

Что учитывается:
- правила `permissions.allow/ask/deny` вида `Bash(...)` из
  `~/.claude/settings.json`, `.claude/settings.json`,
  `.claude/settings.local.json`. Составная команда проверяется по каждой
  простой: разрешение нужно всем, запрета или вопроса хватает одной;
- хуки PreToolUse на Bash: `guard-bash.sh` базы и проектные из
  `settings.json`, вызванные на синтетическом входе. allow хука не
  перебивает ask- и deny-правила — Claude Code сверяет их независимо.

Чего не учитывается — и это сказано в выводе, а не спрятано: режим прав
(auto, acceptEdits, bypass меняют картину), управляемые настройки
организации, хуки других плагинов. Сопоставление правил приближённое:
`*` — любая последовательность, `:*` в конце — префикс.

Вторая часть — **вопросы к человеку, оставшиеся в спеках**: открытые
вопросы, решения со «Спросить: да», пометки «[ТРЕБУЕТ УТОЧНЕНИЯ». Этап,
упирающийся в них, ночью встанет в первый же час — так и вышло у narta, и
координатор заполнил простой спеками следующих этапов (`ADR-0014`, правила
4–5). Их собирают одним списком и отвечают до ухода человека. Узнаются
маркеры формы спек базы; у своей формы проект сверяет сам.

Третья часть — **где агент уже ждал**. Список команд пишет человек, а
агент выполняет их по-своему: у narta в списке стояли одиночные `git push`
и `gh pr create`, preflight был зелёным, а ночью агент склеил их в одну
команду и простоял до утра дважды — 5 ч 47 мин и 4 ч 51 мин. Поэтому
события `wait` из журнала агентов (`.claude/logs/agents.jsonl`) за
последние `MUAGBA_PREFLIGHT_DAYS` дней (по умолчанию 7) сверяются со
списком по классу команды (`git push+gh pr`): класса, которого в списке
нет, preflight не проверял — это находка. Текста команды журнал не хранит,
только класс, поэтому сверка идёт по нему. Вопросы человеку
(`AskUserQuestion`) называются числом: это не права.

Запуск: `python3 preflight.py [файл] [--cwd КАТАЛОГ]`. Код 1, если что-то
спросит, будет запрещено, в спеках остались вопросы к человеку или агент
ждал на команде, которой нет в списке.
"""
from __future__ import annotations

import datetime
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_split import command_class, segments  # noqa: E402

HERE = Path(__file__).resolve().parent


def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def settings_files(root: Path) -> list[Path]:
    return [Path.home() / ".claude" / "settings.json",
            root / ".claude" / "settings.json",
            root / ".claude" / "settings.local.json"]


def bash_rules(root: Path) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {"allow": [], "ask": [], "deny": []}
    for f in settings_files(root):
        perms = load(f).get("permissions") or {}
        for kind in rules:
            for r in perms.get(kind) or []:
                if isinstance(r, str) and r.startswith("Bash(") and r.endswith(")"):
                    rules[kind].append(r[5:-1])
                elif r == "Bash":
                    rules[kind].append("*")
    return rules


def rule_hits(pattern: str, cmd: str) -> bool:
    if pattern.endswith(":*"):
        return cmd == pattern[:-2] or cmd.startswith(pattern[:-2] + " ")
    if pattern.endswith(" *") and cmd == pattern[:-2]:
        return True
    return fnmatch.fnmatchcase(cmd, pattern)


def by_rules(command: str, rules: dict[str, list[str]]) -> tuple[str, str]:
    """(allow|ask|deny|none, почему) по правилам прав."""
    simple = [" ".join(s) for s in segments(command)] or [command]
    for kind in ("deny", "ask"):
        for s in simple:
            for p in rules[kind]:
                if rule_hits(p, s):
                    return kind, f"правило {kind}: Bash({p}) — на «{s.split()[0]} …»"
    missing = [s for s in simple if not any(rule_hits(p, s) for p in rules["allow"])]
    if not missing:
        return "allow", "все части в allow"
    what = ", ".join(sorted({m.split()[0] + (" " + m.split()[1] if len(m.split()) > 1 else "")
                              for m in missing}))
    return "none", f"нет правила allow для: {what}"


def hook_commands(root: Path) -> list[tuple[str, str]]:
    """(имя, команда) хуков PreToolUse на Bash: база плюс проектные."""
    out = [("guard-bash (база)", f'bash "{HERE / "guard-bash.sh"}"')]
    for f in settings_files(root)[1:]:
        for grp in (load(f).get("hooks") or {}).get("PreToolUse") or []:
            m = grp.get("matcher") or ""
            if m and m not in ("*", "Bash") and "Bash" not in m.split("|"):
                continue
            for h in grp.get("hooks") or []:
                if h.get("type") == "command" and h.get("command"):
                    out.append((Path(h["command"].split()[-1].strip('"')).name, h["command"]))
    return out


def by_hooks(command: str, root: Path) -> list[tuple[str, str, str]]:
    """[(хук, allow|ask|deny, почему)] — только хуки, что-то решившие."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command},
                          "cwd": str(root), "hook_event_name": "PreToolUse",
                          "session_id": "preflight"})
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    # Журнал предстартовой проверки не нужен: это не работа агента.
    env["MUAGBA_NO_LOG"] = "1"
    out = []
    for name, cmd in hook_commands(root):
        try:
            r = subprocess.run(cmd, shell=True, input=payload, capture_output=True,
                               text=True, cwd=root, env=env, timeout=30)
        except subprocess.TimeoutExpired:
            out.append((name, "ask", "хук не ответил за 30 с"))
            continue
        if r.returncode == 2:
            reason = next((l for l in r.stderr.splitlines() if l.strip()), "exit 2")
            out.append((name, "deny", reason[:160]))
            continue
        try:
            dec = json.loads(r.stdout).get("hookSpecificOutput") or {}
        except ValueError:
            continue
        kind = dec.get("permissionDecision")
        if kind in ("allow", "ask", "deny"):
            out.append((name, kind, (dec.get("permissionDecisionReason") or "")[:160]))
    return out


def verdict(command: str, root: Path, rules: dict) -> tuple[str, list[str]]:
    rk, rwhy = by_rules(command, rules)
    hooks = by_hooks(command, root)
    why = [rwhy] + [f"{n}: {k} — {w}" for n, k, w in hooks]
    kinds = {k for _, k, _ in hooks}
    if rk == "deny" or "deny" in kinds:
        return "ЗАПРЕТ", why
    if rk == "ask" or "ask" in kinds:
        return "СПРОСИТ", why
    if rk == "allow" or "allow" in kinds:
        return "пройдёт", why
    return "СПРОСИТ", why


MARK = "[ТРЕБУЕТ УТОЧНЕНИЯ"


def spec_questions(root: Path) -> list[tuple[str, int, int, int]]:
    """(спека, открытых вопросов, «Спросить: да», пометок) — где не ноль."""
    out = []
    for spec in sorted((root / "specs").glob("*/spec.md")):
        try:
            t = spec.read_text(encoding="utf-8")
        except OSError:
            continue
        oq = 0
        m = re.search(r"^## Открытые вопросы.*?(?=^## |\Z)", t, re.M | re.S)
        if m:
            # Вопрос — пункт списка или заголовок «В1.»; пояснения и строка
            # «Открытых вопросов нет: В1–В4 решены …» вопросами не считаются.
            body = re.sub(r"<!--.*?-->", "", m.group(0), flags=re.S).splitlines()[1:]
            oq = sum(1 for l in body if re.match(r"\s*(- |#{3,4} |\*\*)?В\d+[.:)]", l)
                     or re.match(r"- \S", l))
        ask = len(re.findall(r"^\s*Спросить:\s*да\b", t, re.M | re.I))
        marks = t.count(MARK)
        if oq or ask or marks:
            out.append((spec.parent.name, oq, ask, marks))
    return out


def agents_log(root: Path) -> Path | None:
    """Журнал агентов пишется в основной checkout (`CLAUDE_PROJECT_DIR`), а
    preflight могут запустить и из рабочего дерева."""
    own = root / ".claude" / "logs" / "agents.jsonl"
    if own.is_file():
        return own
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        main = Path(r.stdout.strip()).parent / ".claude" / "logs" / "agents.jsonl"
        if main.is_file():
            return main
    return None


def past_waits(root: Path, days: int) -> tuple[dict[str, list[float]], int]:
    """({класс Bash-команды: [секунд ожидания]}, вопросов человеку) за `days` дней.

    Ожидание — до следующего события того же агента: та же сессия, та же
    роль, и не SubagentStart/Stop — их пишут сабагенты, работающие рядом,
    пока ждущий стоит. Без этого ночное ожидание narta в 5 ч 47 мин
    выходило в 0: фоновый ревьюер закончил через пять секунд. Событие без
    продолжения даёт 0 — сколько ждало, неизвестно, но что ждало, известно.
    """
    log = agents_log(root)
    if not log:
        return {}, 0
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    events = []
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}, 0
    for line in lines:
        try:
            e = json.loads(line)
            ts = datetime.datetime.fromisoformat(e["ts"])
        except (ValueError, KeyError, TypeError):
            continue
        events.append((ts, e))
    waits: dict[str, list[float]] = {}
    asked = 0
    for i, (ts, e) in enumerate(events):
        if e.get("event") != "wait" or ts < since:
            continue
        if e.get("tool") != "Bash":
            asked += e.get("tool") == "AskUserQuestion"
            continue
        nxt = next((t for t, n in events[i + 1:] if same_actor(n, e)), ts)
        waits.setdefault(e.get("class") or "Bash", []).append((nxt - ts).total_seconds())
    return waits, asked


def same_actor(n: dict, e: dict) -> bool:
    return (n.get("session_id") == e.get("session_id")
            and (n.get("agent_type") or None) == (e.get("agent_type") or None)
            and n.get("event") not in ("SubagentStart", "SubagentStop"))


def span(sec: float) -> str:
    m = int(sec // 60)
    return f"{m // 60} ч {m % 60} мин" if m >= 60 else f"{m} мин"


def main() -> int:
    args = sys.argv[1:]
    root = Path.cwd()
    if "--cwd" in args:
        i = args.index("--cwd")
        root = Path(args[i + 1]).resolve()
        del args[i:i + 2]
    src = Path(args[0]) if args else root / ".claude" / "autonomy-commands.txt"
    cmds: list[str] = []
    if not src.is_file():
        print(f"preflight: нет {src}. Запиши туда рутинные команды этапа — по одной "
              "на строку, как их выполнит агент (с && и ; если он так склеивает).")
    else:
        cmds = [l.strip() for l in src.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.lstrip().startswith("#")]
    rules = bash_rules(root)
    stuck = 0
    for c in cmds:
        v, why = verdict(c, root, rules)
        stuck += v != "пройдёт"
        print(f"{v:8} {c}")
        for w in why:
            print(f"         {w}")
    if cmds:
        print(f"\npreflight: {len(cmds)} команд, упрётся в человека {stuck}. "
              "Не учтены: режим прав, управляемые настройки, хуки других плагинов.")
    qs = spec_questions(root)
    if qs:
        print("\nВопросы к человеку в спеках — ответить до ухода, иначе этап встанет:")
        for name, oq, ask, marks in qs:
            parts = [f"открытых {oq}" if oq else "", f"«Спросить: да» {ask}" if ask else "",
                     f"пометок {marks}" if marks else ""]
            print(f"  {name}: " + ", ".join(p for p in parts if p))
        print("Собери их одним списком по разделам задания; ответ — в источник, "
              "в спеке — ссылка (ADR-0014).")
    try:
        days = int(os.environ.get("MUAGBA_PREFLIGHT_DAYS", "7"))
    except ValueError:
        days = 7
    waits, asked = past_waits(root, days)
    listed = {command_class(c) for c in cmds}
    unlisted = {k: v for k, v in waits.items() if k not in listed}
    if waits:
        print(f"\nГде агент ждал подтверждения за {days} дн. (журнал агентов):")
        for k, v in sorted(waits.items(), key=lambda kv: -sum(kv[1])):
            mark = "НЕТ В СПИСКЕ" if k in unlisted else "в списке"
            print(f"  {mark:12} {k} — {len(v)} раз, ждал {span(sum(v))}")
        if unlisted:
            print("Этих команд в списке нет, и preflight их не проверял: агент выполняет "
                  "их в другом виде — склейкой, с `| tail`. Допиши в список как есть или "
                  "разбей их правилом (например, отказ хука на склейку с подсказкой).")
    if asked:
        print(f"\nВопросов человеку за {days} дн.: {asked}. Это не права: такие вопросы "
              "собирают до ухода человека (ADR-0014).")
    return 1 if stuck or qs or unlisted else 0


if __name__ == "__main__":
    sys.exit(main())
