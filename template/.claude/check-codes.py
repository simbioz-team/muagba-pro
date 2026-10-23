#!/usr/bin/env python3
"""Коды ответа сетевых взаимодействий сверяются с реестром (ADR-0019).

    python3 .claude/check-codes.py            # проверка; из check.sh
    python3 .claude/check-codes.py --stats    # сколько употреблений видит каждый шаблон
    python3 .claude/check-codes.py adopt <реестр>   # внести незнакомые коды как unreviewed

Без `.claude/response-codes.json` — ничего не делает: у проекта нет
сетевых ответов или он ещё не решил. Выход 0 — чисто, 1 — нарушения,
2 — конфиг или реестр не читается.

Конфиг проекта `.claude/response-codes.json`:

    {"registries": ["api/response-codes.json"],
     "usage": [{"files": ["api/**/*.py"], "pattern": "\\"(/problems/[a-z0-9/-]+)\\"",
                "exclude": ["api/problems_gen.py"]}],
     "base": "origin/main"}

Или `{"none": "<почему у проекта нет своих сетевых ответов>"}`.

`pattern` — регулярное выражение употребления кода в файлах `files`;
первая группа (или всё совпадение) — `id` записи либо её `name` (имя
элемента перечисления, если код строится из реестра генерацией).
Шаблонов может быть несколько: литералы и ссылки на перечисление.

Реестр — JSON, список записей или `{"codes": [...]}`. Запись:
`id`, `class` (статус или класс по стандарту транспорта), `meaning`,
`client_action`, `state` (active | deprecated | unreviewed), `added_by`;
у deprecated — `replaced_by` и `remove_after` (ГГГГ-ММ-ДД); `name` — по
желанию.

Проверяется:
- запись полна, `id` и `name` уникальны по всем реестрам репозитория;
- в коде нет кода вне реестра; нет active-записи без употребления;
- выведенная запись с истёкшим `remove_after` больше не употребляется;
- против реестра на базе ветки: запись не исчезла и не сменила класс,
  кроме выведенной с истёкшим сроком; новая запись — с `added_by` и не
  unreviewed (unreviewed — только для кодов, внесённых при заведении
  реестра; это храповик: старое не разобрано, новое — по правилам).

Зависимости — только python3 и git: файл база кладёт в любой проект.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG = ".claude/response-codes.json"
STATES = ("active", "deprecated", "unreviewed")
BASES = ("origin/HEAD", "origin/main", "origin/master", "origin/develop", "main", "master", "develop")


def git(root: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def glob_re(pat: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pat.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pat[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pat[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pat[i]), i + 1
    return re.compile(out + r"\Z")


def entries(data) -> list[dict] | None:
    if isinstance(data, dict):
        data = data.get("codes")
    if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
        return None
    return data


def load_registry(text: str) -> list[dict] | None:
    try:
        return entries(json.loads(text))
    except ValueError:
        return None


def resolve_base(root: Path, cfg: dict) -> str | None:
    want = cfg.get("base") or os.environ.get("MUAGBA_CODES_BASE")
    for ref in ([want] if want else BASES):
        rc, out = git(root, "merge-base", "HEAD", ref)
        if rc == 0 and out.strip():
            return out.strip()
    return None


def date(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s))
    except ValueError:
        return None


def scan(root: Path, cfg: dict, skip: set[str]) -> tuple[list[tuple[str, str, int]], list[dict]]:
    """Употребления: (токен, файл, строка) и счёт по каждому шаблону."""
    rc, out = git(root, "ls-files", "-co", "--exclude-standard")
    files = out.splitlines() if rc == 0 else []
    hits, stats = [], []
    for u in cfg.get("usage") or []:
        inc = [glob_re(p) for p in u.get("files") or []]
        exc = [glob_re(p) for p in u.get("exclude") or []]
        rx = re.compile(u["pattern"])
        n = 0
        for f in files:
            if f in skip or not any(r.match(f) for r in inc) or any(r.match(f) for r in exc):
                continue
            try:
                text = (root / f).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for m in rx.finditer(text):
                tok = m.group(1) if rx.groups else m.group(0)
                hits.append((tok, f, text.count("\n", 0, m.start()) + 1))
                n += 1
        stats.append({"pattern": u["pattern"], "files": u.get("files"), "hits": n})
    return hits, stats


def check(root: Path, cfg: dict) -> tuple[list[str], list[str]]:
    bad, note = [], []
    today = dt.date.today()
    regs: dict[str, list[dict]] = {}
    for path in cfg.get("registries") or []:
        try:
            got = load_registry((root / path).read_text(encoding="utf-8"))
        except OSError:
            got = None
        if got is None:
            raise SystemExit(f"check-codes: реестр {path} не читается (JSON-список или {{\"codes\": [...]}})")
        regs[path] = got

    by_id: dict[str, tuple[str, dict]] = {}
    by_name: dict[str, str] = {}
    for path, codes in regs.items():
        for e in codes:
            cid = e.get("id")
            if not cid:
                bad.append(f"{path}: запись без id: {json.dumps(e, ensure_ascii=False)[:80]}")
                continue
            where = f"{path}: {cid}"
            if cid in by_id:
                bad.append(f"{where}: id уже есть в {by_id[cid][0]} — один код, одно событие")
            by_id[cid] = (path, e)
            if e.get("name"):
                if e["name"] in by_name:
                    bad.append(f"{where}: name {e['name']} уже у {by_name[e['name']]}")
                by_name[e["name"]] = cid
            st = e.get("state")
            if st not in STATES:
                bad.append(f"{where}: state «{st}» — нужно {' | '.join(STATES)}")
                continue
            if st != "unreviewed":
                miss = [k for k in ("class", "meaning", "client_action", "added_by") if not e.get(k)]
                if miss:
                    bad.append(f"{where}: не заполнено {', '.join(miss)}")
            if st == "deprecated":
                if "replaced_by" not in e:
                    bad.append(f"{where}: выведен без replaced_by (нет замены — пустая строка)")
                if not date(e.get("remove_after")):
                    bad.append(f"{where}: выведен без remove_after ГГГГ-ММ-ДД")

    skip = set(regs) | {CONFIG}
    hits, _ = scan(root, cfg, skip)
    used: dict[str, list[str]] = {}
    for tok, f, line in hits:
        cid = tok if tok in by_id else by_name.get(tok)
        if cid is None:
            bad.append(f"{f}:{line}: код {tok} не записан в реестре — добавить записью с added_by "
                       "или взять существующий")
            continue
        used.setdefault(cid, []).append(f"{f}:{line}")
    for cid, (path, e) in by_id.items():
        st, after = e.get("state"), date(e.get("remove_after"))
        if st == "active" and cid not in used:
            bad.append(f"{path}: {cid} active, но нигде не употребляется — вывести или удалить")
        elif st == "unreviewed" and cid not in used:
            note.append(f"{path}: {cid} не разобран и не употребляется — кандидат на удаление")
        elif st == "deprecated" and after and after < today:
            if cid in used:
                bad.append(f"{path}: {cid} выведен до {after}, а ещё употребляется: {used[cid][0]}")
            else:
                note.append(f"{path}: {cid} выведен, срок {after} прошёл — запись можно удалить")

    base = resolve_base(root, cfg)
    if base is None:
        note.append("база ветки не найдена — сверка с прежним реестром пропущена "
                    "(\"base\" в конфиге или MUAGBA_CODES_BASE)")
        return bad, note
    for path, codes in regs.items():
        rc, text = git(root, "show", f"{base}:{path}")
        if rc != 0:
            continue  # реестр заводится в этой ветке: внесённое — как есть
        old = load_registry(text) or []
        now = {e.get("id"): e for e in codes}
        old_ids = {e.get("id") for e in old}
        for o in old:
            oid = o.get("id")
            if oid not in now:
                after = date(o.get("remove_after"))
                if o.get("state") == "deprecated" and after and after <= today:
                    continue
                bad.append(f"{path}: {oid} удалён без выведения — сначала deprecated, replaced_by, "
                           "remove_after; удалить после срока")
                continue
            n = now[oid]
            if o.get("class") and n.get("class") != o.get("class"):
                bad.append(f"{path}: {oid} сменил класс {o.get('class')} → {n.get('class')} — "
                           "это новый код, старый выводится")
            if o.get("state") in ("active", "deprecated") and n.get("state") == "unreviewed":
                bad.append(f"{path}: {oid} вернулся в unreviewed")
        for cid, e in now.items():
            if cid in old_ids:
                continue
            if e.get("state") == "unreviewed":
                bad.append(f"{path}: {cid} новый и unreviewed — unreviewed только для внесённых "
                           "при заведении реестра")
            elif not e.get("added_by"):
                bad.append(f"{path}: {cid} новый без added_by")
    return bad, note


def adopt(root: Path, cfg: dict, target: str) -> int:
    p = root / target
    try:
        raw = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    except ValueError:
        print(f"check-codes: {target} не читается")
        return 2
    was_list = isinstance(raw, list) and bool(raw)
    codes = entries(raw)
    if codes is None:
        print(f"check-codes: {target} — не реестр")
        return 2
    known = set()
    for path in cfg.get("registries") or []:
        try:
            for e in load_registry((root / path).read_text(encoding="utf-8")) or []:
                known |= {e.get("id"), e.get("name")}
        except OSError:
            pass
    hits, _ = scan(root, cfg, set(cfg.get("registries") or []) | {CONFIG})
    new = sorted({t for t, _, _ in hits if t not in known})
    codes += [{"id": t, "class": "", "meaning": "", "client_action": "", "state": "unreviewed",
               "added_by": ""} for t in new]
    out = codes if was_list else {**(raw if isinstance(raw, dict) else {}), "codes": codes}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"внесено как unreviewed: {len(new)}")
    return 0


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    try:
        cfg = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except OSError:
        return 0
    except ValueError as e:
        print(f"check-codes: {CONFIG} не JSON: {e}")
        return 2
    if not isinstance(cfg, dict):
        print(f"check-codes: {CONFIG} — ожидается объект")
        return 2
    if cfg.get("none") and not cfg.get("registries"):
        return 0
    try:
        for u in cfg.get("usage") or []:
            re.compile(u["pattern"])
    except (KeyError, TypeError, re.error) as e:
        print(f"check-codes: шаблон употребления не читается: {e}")
        return 2
    if argv[:1] == ["adopt"] and len(argv) == 2:
        return adopt(root, cfg, argv[1])
    if argv[:1] == ["--stats"]:
        _, stats = scan(root, cfg, set(cfg.get("registries") or []) | {CONFIG})
        print(json.dumps(stats, ensure_ascii=False))
        return 0
    try:
        bad, note = check(root, cfg)
    except SystemExit as e:
        print(e)
        return 2
    for n in note:
        print(f"check-codes: заметка: {n}")
    for b in bad:
        print(f"check-codes: {b}")
    if bad:
        print(f"check-codes: нарушений {len(bad)} — коды ответа сверяются с реестром (ADR-0019)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
