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
Разрешение выдаётся лишь одиночной команде — без &&, ||, ;, |, фонового
&, скобок, подстановок, перенаправлений и обёрток вроде `bash -c`: иначе
allow протащил бы соседнюю команду. Составная команда с пушем или PR
запрещается с подсказкой «выполни по отдельности»: вопрос человеку в
автономной работе висит до утра. Остальное хук не решает — оно идёт
обычным путём прав.

Команда делится на простые оболочечным лексером (shlex с
punctuation_chars), а не поиском слов по строке. Поиск по строке ошибался
в обе стороны (нашёл ревьюер narta): `git status && grep push docs`
запрещался как пуш, а `git push … & rm -rf x` — фоновый `&` не считался
разделителем — разрешался целиком. Глобальные флаги (`git -C путь`,
`gh -R репо`) и путь к программе (`/usr/bin/git`) пуш не прячут.

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
import os
import shlex
import subprocess
import sys

# Схема веток. По умолчанию — одна основная ветка, фичи сливаются в неё.
# Схема с интеграционной веткой: PROTECTED = {"develop", "main"}, BASE = "develop".
PROTECTED = {"main"}
BASE = "main"
# Подстановка выполняется и внутри двойных кавычек — лексер её не видит.
SUBST = ("`", "$(")
OPERATOR = set("();<>|&")
WRAPPERS = {"bash", "sh", "zsh", "dash"}
PREFIXES = {"env", "command", "exec", "nohup", "time"}
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}
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


def split(cmd: str) -> tuple[list[list[str]], bool]:
    """(простые команды, были ли операторы). Перевод строки — разделитель."""
    lex = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    segs: list[list[str]] = [[]]
    ops = False
    for t in lex:
        if t and set(t) <= OPERATOR:
            ops = True
            segs.append([])
        else:
            segs[-1].append(t)
    return [s for s in segs if s], ops


def normalize(seg: list[str]) -> list[str]:
    """Без присваиваний и префиксов (`env`, `command`…); программа — по имени."""
    i = 0
    while i < len(seg) and ("=" in seg[i] and not seg[i].startswith("-") or seg[i] in PREFIXES):
        i += 1
    seg = seg[i:]
    return [os.path.basename(seg[0]).lstrip("\\"), *seg[1:]] if seg else []


def parse(seg: list[str]) -> tuple[str, list[str], dict]:
    """(инструмент, [подкоманда, аргументы…], глобальные опции) для git и gh."""
    seg = normalize(seg)
    if not seg:
        return "", [], {}
    tool, rest, opts = seg[0], seg[1:], {}
    if tool == "git":
        i = 0
        while i < len(rest) and rest[i].startswith("-"):
            if rest[i] in GIT_VALUE_OPTS and i + 1 < len(rest):
                opts[rest[i]] = rest[i + 1]
                i += 2
            else:
                i += 1
        rest = rest[i:]
    elif tool == "gh":
        out, i = [], 0
        while i < len(rest):
            if rest[i] in ("-R", "--repo") and i + 1 < len(rest):
                opts["repo"] = rest[i + 1]
                i += 2
                continue
            if rest[i].startswith("--repo="):
                opts["repo"] = rest[i].split("=", 1)[1]
            else:
                out.append(rest[i])
            i += 1
        rest = out
    return tool, rest, opts


def touches_remote(seg: list[str]) -> bool:
    tool, rest, _ = parse(seg)
    if tool in WRAPPERS and "-c" in rest:
        inner = rest[rest.index("-c") + 1:rest.index("-c") + 2]
        try:
            return any(touches_remote(s) for s in split(inner[0])[0]) if inner else False
        except ValueError:
            return True
    return (tool == "git" and rest[:1] == ["push"]) or (
        tool == "gh" and rest[:1] == ["pr"] and rest[1:2] in (["create"], ["merge"]))


def judge(cmd: str, cwd: str | None) -> dict | None:
    try:
        segs, ops = split(cmd)
    except ValueError:
        return None
    if not segs:
        return None
    tool, rest, opts = parse(segs[0])
    wrapped = tool in WRAPPERS
    single = len(segs) == 1 and not ops and not wrapped and not any(m in cmd for m in SUBST)

    # Составная команда с пушем или PR: разбирать её целиком нельзя — слова
    # соседних команд принимаются за ветки (`--base develop` у gh pr читался
    # как пуш в develop). А отдать на обычный путь прав значит повесить
    # вопрос человеку: ночью это простой до утра, так и простоял проект
    # narta. Запрет с причиной агент видит и перезапускает по отдельности.
    if not single and any(touches_remote(s) for s in segs):
        return decision("deny", "составная команда с git push / gh pr: выполни их "
                                "отдельными вызовами, без &&, ;, |, &, скобок и bash -c — "
                                "одиночные пуш в ветку фичи и PR в " + BASE + " проходят без вопроса")
    if not single:
        return None
    if "-C" in opts:
        cwd = os.path.join(cwd or ".", opts["-C"])
    words = [tool, *rest]
    sub = rest[:2] or [""]

    if tool == "git" and sub[0] == "push":
        targets, problem = push_targets(words[2:], cwd)
        if problem or not targets:
            return decision("ask", f"git push: {problem or 'не определена ветка назначения'} — решает человек")
        bad = [t for t in targets if not is_feature(t)]
        if bad:
            return decision("ask", f"пуш в {', '.join(bad)} — без вопроса можно только в ветки фич")
        return decision("allow", f"пуш в ветку фичи {', '.join(targets)}")

    if tool == "gh" and sub == ["pr", "create"]:
        base = option(words, "--base", "-B")
        head = option(words, "--head", "-H") or current_branch(cwd)
        if base == BASE and is_feature(head):
            return decision("allow", f"PR из ветки фичи {head} в {BASE}")
        return decision("ask", f"PR {head or '?'} → {base or 'ветка по умолчанию'}: "
                               f"без вопроса — только из ветки фичи в {BASE} с явным --base {BASE}")

    if tool == "gh" and sub == ["pr", "merge"]:
        if "--admin" in words:
            return decision("ask", "gh pr merge --admin — решает человек")
        target = next((w for w in words[3:] if not w.startswith("-")), None)
        view = ["gh", *(["-R", opts["repo"]] if "repo" in opts else []), "pr", "view",
                *([target] if target else []), "--json", "baseRefName,headRefName"]
        out = subprocess.run(view, cwd=cwd, capture_output=True, text=True)
        try:
            pr = json.loads(out.stdout)
        except json.JSONDecodeError:
            return decision("ask", "не удалось узнать ветки PR — решает человек")
        base, head = pr.get("baseRefName"), pr.get("headRefName")
        if base == BASE and is_feature(head):
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
