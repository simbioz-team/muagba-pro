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

Запуск: `python3 preflight.py [файл] [--cwd КАТАЛОГ]`. Код 1, если что-то
спросит или будет запрещено.
"""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_split import segments  # noqa: E402

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


def main() -> int:
    args = sys.argv[1:]
    root = Path.cwd()
    if "--cwd" in args:
        i = args.index("--cwd")
        root = Path(args[i + 1]).resolve()
        del args[i:i + 2]
    src = Path(args[0]) if args else root / ".claude" / "autonomy-commands.txt"
    if not src.is_file():
        print(f"preflight: нет {src}. Запиши туда рутинные команды этапа — по одной "
              "на строку, как их выполнит агент (с && и ; если он так склеивает).")
        return 0
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
    print(f"\npreflight: {len(cmds)} команд, упрётся в человека {stuck}. "
          "Не учтены: режим прав, управляемые настройки, хуки других плагинов.")
    return 1 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
