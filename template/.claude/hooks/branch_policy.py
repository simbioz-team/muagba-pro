#!/usr/bin/env python3
"""PreToolUse (Bash): пуш, PR и слияние без вопроса — только для веток фич.

ОБРАЗЕЦ, по умолчанию выключен. Взят из проекта narta, где работал на
живой разработке; база его не подключает — схема веток у каждого проекта
своя, а работу с гитом база не подменяет.

Что делает:
- git push только в ветки фич — allow; в защищённые ветки, с --force,
  --delete, --tags, refspec с «+» или «:ветка» — ask с причиной;
- gh pr create — allow, только при явном --base <BASE> и head — ветке фичи;
- gh pr merge — allow, только если PR на хостинге идёт из ветки фичи в BASE;
  --admin — ask.
Разрешение выдаётся лишь одиночной команде без &&, ;, |, подстановок и
перенаправлений: иначе allow протащил бы соседнюю команду. Остальное хук
не решает — оно идёт обычным путём прав.

Как включить:
1. Поправь PROTECTED и BASE ниже под схему веток из docs/workflow.md,
   «Ветки и мерж».
2. Подключи в .claude/settings.json:
     "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
       "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/branch_policy.py\"",
       "timeout": 30}]}]}
3. **Убери `Bash(git push *)` из `permissions.ask`.** Правила ask и deny
   Claude Code проверяет независимо от того, что вернул хук: allow хука
   ask-правило не перебивает, и хук молча не работал бы. Запреты в deny
   (push --force и т.п.) оставь — они и должны перебивать.
4. Тесты: python3 -m unittest discover -s .claude/hooks — стоит вызвать из
   .claude/check.sh.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys

# Схема веток. По умолчанию — одна основная ветка, фичи сливаются в неё.
# Схема с интеграционной веткой: PROTECTED = {"develop", "main"}, BASE = "develop".
PROTECTED = {"main"}
BASE = "main"
SHELL_META = ("&&", "||", ";", "|", "`", "$(", ">", "<", "\n")
RISKY_PUSH_FLAGS = {"-f", "--force", "--force-with-lease", "--force-if-includes", "-d", "--delete",
                    "--all", "--mirror", "--tags", "--prune", "--no-verify"}


def decision(kind: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": kind, "permissionDecisionReason": reason}}


def current_branch(cwd: str | None) -> str | None:
    out = subprocess.run(["git", "branch", "--show-current"], cwd=cwd, capture_output=True, text=True)
    return out.stdout.strip() or None


def is_feature(branch: str | None) -> bool:
    return bool(branch) and branch not in PROTECTED and not branch.startswith("-")


def push_targets(args: list[str], cwd: str | None) -> tuple[list[str], str | None]:
    """Ветки назначения `git push …` и причина отказа разбирать, если есть."""
    flags = [a for a in args if a.startswith("-")]
    risky = sorted(set(flags) & RISKY_PUSH_FLAGS | {f for f in flags if f.startswith("--force")})
    if risky:
        return [], f"флаги {', '.join(risky)}"
    positional = [a for a in args if not a.startswith("-")]
    refspecs = positional[1:]  # первый позиционный — remote
    if not refspecs:
        branch = current_branch(cwd)
        return ([branch] if branch else []), (None if branch else "не определена текущая ветка")
    targets = []
    for spec in refspecs:
        if spec.startswith("+"):
            return [], "принудительный refspec +"
        if spec.startswith(":"):
            return [], f"удаление ветки {spec[1:]}"
        dst = spec.split(":", 1)[1] if ":" in spec else spec
        if dst == "HEAD":
            dst = current_branch(cwd) or ""
        targets.append(dst.removeprefix("refs/heads/"))
    return targets, None


def option(args: list[str], *names: str) -> str | None:
    for i, a in enumerate(args):
        for n in names:
            if a == n and i + 1 < len(args):
                return args[i + 1]
            if a.startswith(n + "="):
                return a.split("=", 1)[1]
    return None


def judge(cmd: str, cwd: str | None) -> dict | None:
    try:
        words = shlex.split(cmd)
    except ValueError:
        return None
    if len(words) < 2:
        return None
    single = not any(m in cmd for m in SHELL_META)
    tool, sub = words[0], words[1:3]

    if tool == "git" and sub[0] == "push":
        targets, problem = push_targets(words[2:], cwd)
        if problem or not targets:
            return decision("ask", f"git push: {problem or 'не определена ветка назначения'} — решает человек")
        bad = [t for t in targets if not is_feature(t)]
        if bad:
            return decision("ask", f"пуш в {', '.join(bad)} — без вопроса можно только в ветки фич")
        if single:
            return decision("allow", f"пуш в ветку фичи {', '.join(targets)}")
        return None

    if tool == "gh" and sub == ["pr", "create"]:
        base = option(words, "--base", "-B")
        head = option(words, "--head", "-H") or current_branch(cwd)
        if base == BASE and is_feature(head) and single:
            return decision("allow", f"PR из ветки фичи {head} в {BASE}")
        return decision("ask", f"PR {head or '?'} → {base or 'ветка по умолчанию'}: "
                               f"без вопроса — только из ветки фичи в {BASE} с явным --base {BASE}")

    if tool == "gh" and sub == ["pr", "merge"]:
        if "--admin" in words:
            return decision("ask", "gh pr merge --admin — решает человек")
        target = next((w for w in words[3:] if not w.startswith("-")), None)
        view = ["gh", "pr", "view", *([target] if target else []), "--json", "baseRefName,headRefName"]
        out = subprocess.run(view, cwd=cwd, capture_output=True, text=True)
        try:
            pr = json.loads(out.stdout)
        except json.JSONDecodeError:
            return decision("ask", "не удалось узнать ветки PR — решает человек")
        base, head = pr.get("baseRefName"), pr.get("headRefName")
        if base == BASE and is_feature(head) and single:
            return decision("allow", f"слияние PR {head} → {BASE}")
        return decision("ask", f"слияние PR {head} → {base}: без вопроса — только из ветки фичи в {BASE}")

    return None


def main() -> None:
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command") or ""
    result = judge(cmd, data.get("cwd"))
    if result:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
