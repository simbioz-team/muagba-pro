#!/usr/bin/env python3
"""Где остановилась настройка проекта.

Состояние не хранится, а выводится: скрипт прогоняет пробы по репозиторию и
называет первый незакрытый этап. Поэтому прерывание настройки ничего не стоит.

Спецификация проб — docs/gates.md базы, устройство — docs/setup-state.md,
обоснование — ADR-0004. Зависимости: только стандартная библиотека.

Скрипт ничего не чинит и не пишет в репозиторий. Единственный файл, который он
трогает, — .claude/setup.json, и только по командам confirm/unconfirm/trait.
"""
from __future__ import annotations

import argparse
import hashlib
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Вердикты
# --------------------------------------------------------------------------
OK, FAIL, SKIP, UNKNOWN, NOTRUN = "ok", "fail", "skip", "unknown", "notrun"
MACHINE, HUMAN = "М", "Ч"
CHEAP, EXPENSIVE = "cheap", "expensive"

MARK = {OK: "✓", FAIL: "✗", SKIP: "∅", UNKNOWN: "?", NOTRUN: "·"}
# Что мешает считать этап закрытым. NOTRUN добавляется, если дорогие пробы не
# отключены явно: непрогнанная проба — не то же самое, что пройденная.
BLOCKING = {FAIL, UNKNOWN}


def short(text: str, limit: int = 120) -> str:
    """Вывод чужого скрипта бывает на сотни строк. В таблицу идёт начало,
    за полным списком проба отправляет к самому скрипту."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class V:
    __slots__ = ("verdict", "detail", "fix")

    def __init__(self, verdict: str, detail: str = "", fix: str = ""):
        self.verdict, self.detail, self.fix = verdict, short(detail), fix


def ok(detail: str = "") -> V:
    return V(OK, detail)


def bad(detail: str, fix: str = "") -> V:
    return V(FAIL, detail, fix)


def skip(detail: str) -> V:
    return V(SKIP, detail)


class Probe:
    __slots__ = ("id", "stage", "title", "kind", "needs", "cost", "watch", "fills",
                 "run", "applies", "confirm_at")

    def __init__(self, id, stage, title, kind=MACHINE, needs=None, cost=CHEAP,
                 watch=(), fills=None, run=None, applies=None, confirm_at=None):
        self.id, self.stage, self.title = id, stage, title
        self.kind, self.needs, self.cost = kind, needs, cost
        self.watch, self.fills, self.run = tuple(watch), fills, run
        # Условие, которое не выражается признаком: (ctx) -> bool. Нужно
        # человеческим пробам — у них нет run(), и сказать «неприменимо»
        # им было нечем.
        self.applies = applies
        # Этап, на котором проба физически может быть подтверждена. Отличается
        # от stage, когда обещание даётся раньше, чем появляется механика:
        # пометка «машинно» ставится на Э3, а хук под неё пишется на Э7. Без
        # этого поля Э3 не закрывался никогда, а конвейер велел не идти дальше.
        self.confirm_at = confirm_at


STAGES = [
    ("Э0", "Каркас и гигиена git"),
    ("Э1", "Точка входа для агентов"),
    ("Э2", "Продуктовая рамка"),
    ("Э3", "Конституция и «готово»"),
    ("Э4", "Стек и структура"),
    ("Э5", "Рабочая среда"),
    ("Э6", "Контракт проверки"),
    ("Э7", "Принудительные рамки"),
    ("Э8", "Роли и параллелизм"),
    ("Э9", "Рабочий цикл"),
    ("Э10", "Наблюдаемость и накопление"),
    ("Э11", "Холостой прогон"),
]
STAGE_TITLE = dict(STAGES)
STAGE_ORDER = [s for s, _ in STAGES]

TRAITS = {
    "ui": "есть интерфейс, который человек открывает в браузере",
    "storage": "есть постоянное хранилище",
    "remote": "есть удалённый репозиторий",
    "model": "проект обучает или применяет модель",
}

# --------------------------------------------------------------------------
# Разбор документов
# --------------------------------------------------------------------------
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# Слот шаблона. Может быть многострочным: в заготовках базы пояснение внутри
# угловых скобок занимает три-четыре строки.
SLOT = re.compile(r"<[^<>]{0,800}>")
FENCE = re.compile(r"```.*?```", re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
CODE_SPAN = re.compile(r"`[^`\n]*`")
NOISE = re.compile(r"[\s|\-*>`:,.;!?—–~()\[\]{}]+")


def norm(s: str) -> str:
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[«»„“”\"'`]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def section(text: str, needle: str) -> str | None:
    """Тело раздела, чей заголовок содержит needle. None — раздела нет."""
    if not text:
        return None
    lines = text.splitlines()
    want, start, level = norm(needle), None, None
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if not m:
            continue
        if start is None:
            if want in norm(m.group(2)):
                start, level = i + 1, len(m.group(1))
            continue
        if len(m.group(1)) <= level:
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:]) if start is not None else None


def meaningful(text: str | None) -> str:
    """Текст без заготовок. Пусто — раздел не заполнен, что бы в нём ни стояло.

    Порядок важен: сначала прячем код, потом снимаем слоты. Иначе `<T>` внутри
    обратных кавычек посчитается незаполненным слотом, и рабочий текст будет
    объявлен пустым.
    """
    if not text:
        return ""
    text = FENCE.sub("", text)
    text = COMMENT.sub("", text)
    text = CODE_SPAN.sub("КОД", text)
    text = SLOT.sub("", text)
    kept = []
    for line in text.splitlines():
        if HEADING.match(line):
            continue
        if NOISE.sub("", line):
            kept.append(line.strip())
    return "\n".join(kept).strip()


def tables(text: str | None) -> list[list[list[str]]]:
    """Таблицы документа по отдельности, каждая — список строк ячеек.

    По отдельности, а не одной кучей: у второй таблицы своя шапка, и если
    собирать всё подряд, она поедет в данные. На этом `product.glossary`
    зеленела на нетронутой заготовке.
    """
    out, cur = [], []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):  # строка-разделитель
                cur.append(cells)
            continue
        if cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def filled_rows(table: list[list[str]]) -> list[list[str]]:
    """Строки таблицы, где заполнено хоть что-то, кроме первой колонки.

    Первая колонка в заготовках базы подписана заранее («Язык и версия»), а
    значения — слоты. Считать такую строку заполненной значит объявить
    незаполненный стек зафиксированным.
    """
    return [r for r in table[1:] if any(meaningful(c) for c in r[1:])]


def table_rows(text: str | None) -> list[list[str]]:
    """Заполненные строки всех таблиц документа."""
    return [r for t in tables(text) for r in filled_rows(t)]


# --------------------------------------------------------------------------
# Контекст проекта
# --------------------------------------------------------------------------
class Ctx:
    def __init__(self, root: Path):
        self.root = root
        self._cache: dict[str, str | None] = {}

    def p(self, rel: str) -> Path:
        return self.root / rel

    def exists(self, rel: str) -> bool:
        return self.p(rel).exists()

    def read(self, rel: str) -> str | None:
        if rel not in self._cache:
            try:
                self._cache[rel] = self.p(rel).read_text(encoding="utf-8")
            except OSError:
                self._cache[rel] = None
        return self._cache[rel]

    def glob(self, pattern: str) -> list[Path]:
        return sorted(self.root.glob(pattern))

    def json(self, rel: str):
        raw = self.read(rel)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return None

    def git(self, *args: str) -> tuple[int, str]:
        try:
            r = subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                               text=True, timeout=10)
            return r.returncode, r.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return 1, ""

    def rules_file(self) -> str | None:
        """Свод правил: AGENTS.md либо CLAUDE.md, что есть."""
        for name in ("AGENTS.md", "CLAUDE.md"):
            if self.exists(name):
                return name
        return None

    def rules_text(self) -> str:
        return "\n".join(self.read(n) or "" for n in ("AGENTS.md", "CLAUDE.md"))

    def settings(self) -> dict:
        return self.json(".claude/settings.json") or {}

    def doc_config(self) -> dict:
        return self.json(".claude/doc-config.json") or {}

    def registry(self) -> str:
        cfg = self.doc_config()
        idx = (cfg.get("registries") or {}).get("index", "docs/INDEX.md")
        return self.read(idx) or ""

    def frames(self, rel: str, *headings: str) -> V:
        """Общий случай: документ есть и названный раздел заполнен."""
        text = self.read(rel)
        if text is None:
            return bad(f"нет {rel}", f"завести {rel}")
        for h in headings:
            body = section(text, h)
            if body is None:
                return bad(f"в {rel} нет раздела «{h}»", f"{rel}: добавить раздел «{h}»")
            if not meaningful(body):
                return bad(f"раздел «{h}» не заполнен", f"{rel}, раздел «{h}»")
        return ok()


def find_root(start: Path) -> Path | None:
    """Корень проекта. Домашний каталог корнем не считается никогда.

    `~/.claude/` — конфиг самого Claude Code, а не проект. Поиск по признаку
    «есть .claude/» доезжал до дома и объявлял корнем его: в пустой папке без
    git первая же команда `trait` писала в ГЛОБАЛЬНЫЙ `~/.claude/setup.json`.
    Найдено обкаткой; самый дорогой дефект из первого круга.
    """
    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        home = None
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
        if home is not None and d == home:
            break
        if (d / ".claude").is_dir():
            return d
    return None


# --------------------------------------------------------------------------
# Синтетические вызовы хуков
# --------------------------------------------------------------------------
def call_hook(script: str, payload: dict, cwd: Path, timeout: int = 10,
              bare: bool = False) -> int:
    """Синтетический вызов хука.

    `bare=True` — без `cwd` во входе и без `CLAUDE_PROJECT_DIR` в окружении.
    Так самотест проверяет то, что ломалось на самом деле: хук обязан понять,
    какому проекту принадлежит файл, по самому файлу. Подставлять правильный
    корень и радоваться зелёному — обманывать себя, и первая обкатка это
    показала.
    """
    path = HERE / script
    if not path.exists():
        return -1
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if not bare:
        env["CLAUDE_PROJECT_DIR"] = str(cwd)
    try:
        r = subprocess.run(["bash", str(path)], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=timeout,
                           cwd=str(cwd), env=env)
        return r.returncode
    except (OSError, subprocess.SubprocessError):
        return -1


# --------------------------------------------------------------------------
# Пробы
# --------------------------------------------------------------------------
# Э0 ------------------------------------------------------------------------
def pr_git_repo(c: Ctx) -> V:
    rc, out = c.git("rev-parse", "--is-inside-work-tree")
    if rc == 0 and out == "true":
        return ok()
    return bad("это не git-репозиторий", "git init")


AGENT_IGNORES = [".claude/worktrees/", ".claude/settings.local.json",
                 ".claude/logs/", "CLAUDE.local.md", ".env"]


# Каталог сам по себе check-ignore не проверяет — нужен путь внутри него.
IGNORE_SAMPLES = {
    ".claude/worktrees/": ".claude/worktrees/w/README.md",
    ".claude/settings.local.json": ".claude/settings.local.json",
    ".claude/logs/": ".claude/logs/agents.jsonl",
    "CLAUDE.local.md": "CLAUDE.local.md",
    ".env": ".env",
}


def pr_git_ignore(c: Ctx) -> V:
    if c.read(".gitignore") is None:
        return bad("нет .gitignore", "завести .gitignore с агентскими записями")
    rc, _ = c.git("rev-parse", "--git-dir")
    if rc != 0:
        return bad("не git-репозиторий, спросить git нечем", "git init")
    # Спрашиваем git, а не ищем подстроку. Строка с комментарием в конце —
    # `.claude/logs/    # журнал` — в файле есть, но шаблоном становится вся
    # строка целиком, вместе с пробелами и словом «журнал», и не игнорирует
    # ничего. Круг 2 поймал это на самом каркасе: два прогона независимо, и
    # оба — последствием (git add -A утащил рабочие деревья), а не чтением.
    samples = [IGNORE_SAMPLES[n] for n in AGENT_IGNORES]
    _, out = c.git("check-ignore", "-v", "--no-index", *samples)
    covered = set()
    for line in out.splitlines():
        src, _, _ = line.partition(":")
        path = line.split("\t", 1)[1] if "\t" in line else ""
        # Правило из личного ~/.config/git/ignore не считается: у него
        # абсолютный путь, на чужой машине его нет, а каркас обязан быть
        # самодостаточным. Ровно этим на одной машине маскировался промах.
        if path and not src.startswith("/"):
            covered.add(path)
    missing = [n for n in AGENT_IGNORES if IGNORE_SAMPLES[n] not in covered]
    if missing:
        return bad("git не игнорирует: " + ", ".join(missing),
                   ".gitignore: комментарий пишется над строкой, а не в её конце")
    return ok()


def pr_git_commit(c: Ctx) -> V:
    rc, out = c.git("rev-list", "--count", "HEAD")
    if rc == 0 and out.isdigit() and int(out) > 0:
        return ok()
    return bad("нет ни одного коммита", "сделать первый коммит: от него считается любой диф")


# Э1 ------------------------------------------------------------------------
def pr_entry_files(c: Ctx) -> V:
    if c.rules_file():
        return ok()
    return bad("нет ни AGENTS.md, ни CLAUDE.md", "завести свод правил")


def pr_entry_import(c: Ctx) -> V:
    if not (c.exists("AGENTS.md") and c.exists("CLAUDE.md")):
        return ok("файл один, расходиться нечему")
    if "@AGENTS.md" in (c.read("CLAUDE.md") or ""):
        return ok()
    return bad("есть оба файла, но CLAUDE.md не импортирует AGENTS.md — "
               "Claude Code прочитает только первый",
               "CLAUDE.md: строка @AGENTS.md")


def pr_entry_size(c: Ctx) -> V:
    long = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        txt = c.read(name)
        if txt is not None:
            n = len(txt.splitlines())
            if n > 200:
                long.append(f"{name}: {n} строк")
    if long:
        return bad("свод разросся — " + ", ".join(long),
                   "вынести то, что касается части кода, в .claude/rules/")
    return ok()


def pr_entry_plugins(c: Ctx) -> V:
    enabled = c.settings().get("enabledPlugins") or {}
    have = {k.split("@")[0] for k, v in enabled.items() if v}
    missing = [p for p in ("muagba-base", "docsys") if p not in have]
    if missing:
        return bad("не объявлены плагины конвейера: " + ", ".join(missing),
                   ".claude/settings.json → enabledPlugins")
    return ok()


def pr_entry_docsys(c: Ctx) -> V:
    if c.exists(".claude/doc-config.json"):
        return ok()
    return bad("система документации не развёрнута", "/doc-init")


def pr_entry_sources(c: Ctx) -> V:
    files = [p for p in c.glob("docs/sources/*.md") if p.name.lower() != "readme.md"]
    if not files:
        return skip("принесённых материалов нет")
    registry = c.registry()
    problems = []
    for f in files:
        rel = f.relative_to(c.root).as_posix()
        head = f.read_text(encoding="utf-8", errors="replace")[:2000]
        fm = head.split("---")[1] if head.startswith("---") and head.count("---") >= 2 else ""
        if not re.search(r"^origin:\s*\S", fm, re.M) or "[ORIGIN" in fm:
            problems.append(f"{rel}: не заполнен origin")
        elif f.name not in registry and rel not in registry:
            problems.append(f"{rel}: нет в реестре")
    if problems:
        return bad("; ".join(problems),
                   "origin отвечает, чей это материал и когда написан; "
                   "реестр пересобирается rebuild_registries.py")
    return ok()


# Э2 ------------------------------------------------------------------------
PRODUCT_DOCS = ["docs/product/mission.md", "docs/product/roadmap.md",
                "docs/product/glossary.md"]
# Документы замысла: их человек подтверждает как свой текст. Словарь сюда не
# входит — он живой справочник, а не заявление о намерении.
PRODUCT_INTENT = PRODUCT_DOCS[:2]


def pr_product_docs(c: Ctx) -> V:
    missing = [d for d in PRODUCT_DOCS if not c.exists(d)]
    if missing:
        return bad("нет документов: " + ", ".join(missing), "/doc-new")
    registry = c.registry()
    unlisted = [d for d in PRODUCT_DOCS if Path(d).name not in registry and d not in registry]
    if unlisted:
        return bad("нет в реестре: " + ", ".join(unlisted),
                   "пересобрать реестры: rebuild_registries.py")
    return ok()


def find_docsys_script(name: str) -> Path | None:
    """Скрипт docsys. База зависит от него как от плагина класса А (ADR-0001),
    но лежит он отдельно, поэтому ищем по известным местам."""
    env = os.environ.get("DOCSYS_SCRIPTS")
    candidates = []
    if env:
        candidates.append(Path(env) / name)
    # Кэш плагинов: <cache>/<маркетплейс>/<плагин>/<версия>/scripts/
    for parent in HERE.resolve().parents:
        if parent.name == "cache":
            candidates += sorted(parent.glob(f"*/docsys/*/scripts/{name}"), reverse=True)
            break
    candidates += sorted(Path.home().glob(f".claude/plugins/cache/*/docsys/*/scripts/{name}"),
                         reverse=True)
    # Рядом, если базу и docsys держат в соседних каталогах
    candidates.append(HERE.parents[2] / "docsys" / "plugins" / "docsys" / "scripts" / name)
    for p in candidates:
        if p.exists():
            return p
    return None


def pr_product_meta(c: Ctx) -> V:
    script = find_docsys_script("check_frontmatter.py")
    if script is None:
        return bad("не найден check_frontmatter.py из docsys",
                   "поставить docsys либо указать путь в DOCSYS_SCRIPTS")
    # Только продуктовые документы. Без ограничения области проба требовала
    # frontmatter у workflow.md и toolchain.md, которые заполняются на Э9-Э10:
    # Э2 не закрывался, пока не сделана работа поздних этапов.
    try:
        r = subprocess.run([sys.executable, str(script), *PRODUCT_DOCS], cwd=c.root,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return bad(f"check_frontmatter.py не запустился: {e}")
    if r.returncode == 0:
        return ok()
    tail = (r.stdout + r.stderr).strip().splitlines()
    return bad("; ".join(tail[:3]) or "метаданные не прошли проверку",
               "check_frontmatter.py покажет полный список")


def pr_product_antigoals(c: Ctx) -> V:
    return c.frames("docs/product/mission.md", "Чего продукт НЕ делает")


def pr_product_glossary(c: Ctx) -> V:
    text = c.read("docs/product/glossary.md")
    if text is None:
        return bad("нет docs/product/glossary.md", "/doc-new")
    got = tables(text)
    if got:
        for row in filled_rows(got[0]):  # первая таблица — термины
            if len(row) >= 2 and meaningful(row[0]) and meaningful(row[1]):
                return ok()
    return bad("в словаре нет ни одного термина с написанием в коде",
               "docs/product/glossary.md: вторая колонка и есть контракт для имён")


# Э3 ------------------------------------------------------------------------
PRINCIPLE = re.compile(r"^###\s+(.+?)\s*$", re.M)


# Конституция бывает не только нашей: Spec Kit держит её в
# `.specify/memory/constitution.md`. Проба обязана проверять свойство, а не
# адрес нашего файла (ADR-0007). Список закрыт и короток намеренно: открытый
# поиск по дереву начнёт находить чужое.
CONST_PLACES = ("docs/constitution.md", ".specify/memory/constitution.md",
                "memory/constitution.md")
CONST_HEADS = ("Принципы", "Core Principles")
GOVERNANCE_HEADS = ("Изменение конституции", "Governance", "Порядок изменения")


def const_path(c: Ctx) -> str | None:
    for rel in CONST_PLACES:
        if c.exists(rel):
            return rel
    return None


def principles(c: Ctx) -> list[str]:
    rel = const_path(c)
    if rel is None:
        return []
    text = c.read(rel) or ""
    body = next((s for h in CONST_HEADS if (s := section(text, h))), None)
    if not body:
        return []
    out = []
    chunks = PRINCIPLE.split(body)
    for i in range(1, len(chunks), 2):
        out.append(chunks[i] + "\n" + chunks[i + 1])
    return out


def pr_const_exists(c: Ctx) -> V:
    rel = const_path(c)
    if rel is None:
        return bad("конституции нет ни в одном известном месте: "
                   + ", ".join(CONST_PLACES), "/doc-new")
    # Реестр спрашиваем только со своего места: ADR-0001 требует, чтобы
    # документы рамок были документами системы документации, но чужой
    # конвейер кладёт конституцию мимо неё, и это его право.
    if rel.startswith("docs/") and Path(rel).name not in c.registry():
        return bad("конституции нет в реестре", "пересобрать реестры")
    return ok("" if rel == CONST_PLACES[0] else f"конституция проекта: {rel}")


NUMBERING = re.compile(r"^[\s]*[IVXLCDM]+[.)]?\s*|^[\s]*\d+[.)]?\s*")


def named_principles(c: Ctx) -> list[str]:
    """Принципы с именем и телом. Заголовок вида «I. <Имя принципа>» после
    снятия слота оставляет номер — раньше номера хватало, чтобы заготовка
    засчиталась настоящим принципом."""
    out = []
    for p in principles(c):
        head, _, body = p.partition("\n")
        if meaningful(NUMBERING.sub("", head)) and meaningful(body):
            out.append(p)
    return out


def pr_const_count(c: Ctx) -> V:
    named = named_principles(c)
    n = len(named)
    if n < 5:
        return bad(f"принципов {n}, нужно 5–9", "docs/constitution.md → «Принципы»")
    if n > 9:
        return bad(f"принципов {n}, больше девяти не запоминается и не соблюдается",
                   "docs/constitution.md: объединить или убрать лишние")
    return ok()


def pr_const_markers(c: Ctx) -> V:
    bare = []
    for p in named_principles(c):
        head = p.splitlines()[0].strip()
        # Значение может уехать на следующую строку — редактор переносит по
        # ширине, а проба этого не прощала и подсказки не давала.
        m = re.search(r"Исполнение:\s*(.{0,80})", p, re.S)
        if not m or not re.search(r"машинно|только совет", m.group(1)):
            bare.append(head)
    if bare:
        return bad("без строки «Исполнение:» — " + "; ".join(bare[:3]),
                   "у каждого принципа: Исполнение: машинно | только совет. "
                   "Принцип без способа исполнения — пожелание; в чужих шаблонах "
                   "конституции этого поля нет, его дописывают")
    return ok()


def pr_const_governance(c: Ctx) -> V:
    rel = const_path(c)
    if rel is None:
        return bad("конституции нет", "Э3: завести конституцию")
    text = c.read(rel) or ""
    for h in GOVERNANCE_HEADS:
        if meaningful(section(text, h)):
            return ok()
    return bad(f"в {rel} не заполнен раздел про порядок изменения",
               "раздел «Изменение конституции» (у чужого шаблона — «Governance»): "
               "кто меняет, как принимается, что делать с уже написанным")


def pr_dod_exists(c: Ctx) -> V:
    text = c.read("docs/definition-of-done.md")
    if text is None:
        return bad("нет docs/definition-of-done.md", "завести определение готовности")
    if "check.sh" not in text:
        return bad("«готово» не ссылается на команду проверки",
                   "docs/definition-of-done.md: пункт про ./.claude/check.sh")
    return ok()


# Э4 ------------------------------------------------------------------------
def pr_stack_exists(c: Ctx) -> V:
    text = c.read("docs/tech-stack.md")
    if text is None:
        return bad("нет docs/tech-stack.md", "/doc-new")
    if not table_rows(text):
        return bad("таблица стека не заполнена", "docs/tech-stack.md")
    return ok()


def pr_stack_forbidden(c: Ctx) -> V:
    return c.frames("docs/tech-stack.md", "Запрещено тянуть")


def pr_structure_exists(c: Ctx) -> V:
    if c.exists("docs/structure.md"):
        return ok()
    return bad("нет docs/structure.md", "/doc-new")


def pr_structure_principle(c: Ctx) -> V:
    return c.frames("docs/structure.md", "Принцип")


def pr_adr_first(c: Ctx) -> V:
    found = [p for p in c.glob("docs/decisions/*.md")
             if "template" not in p.name and not p.name.startswith("adr-0000")]
    if found:
        return ok()
    return bad("нет ни одного ADR помимо шаблона",
               "/doc-new adr — формат заводится до первого спора")


def pr_stack_model(c: Ctx) -> V:
    """Данные, версия модели и тот, кто судит числа.

    Найдено вторым кругом: на ML-продукте слова «модель» не было ни в одном
    из 79 вопросов банка, кроме В6.7. Словарь при этом полгода называл
    version модели идентификатором прогона, схлопывая три разные сущности —
    данные, код, модель — в одно число, и нашёл это исполнитель задачи, а не
    гейт."""
    return c.frames("docs/tech-stack.md", "Данные и модель")


# Э5 ------------------------------------------------------------------------
MANIFESTS = ["pyproject.toml", "package.json", "go.mod", "Cargo.toml",
             "requirements.txt", "Gemfile", "composer.json"]
LOCKS = ["uv.lock", "poetry.lock", "package-lock.json", "pnpm-lock.yaml",
         "yarn.lock", "go.sum", "Cargo.lock", "Gemfile.lock", "composer.lock",
         "requirements.lock"]


def pr_env_lock(c: Ctx) -> V:
    manifest = [m for m in MANIFESTS if c.exists(m)]
    if not manifest:
        return bad("нет манифеста зависимостей", "объявить зависимости проекта")
    lock = [l for l in LOCKS if c.exists(l)]
    if not lock:
        return bad(f"есть {manifest[0]}, но нет lock-файла",
                   "установка без lock-файла невоспроизводима")
    return ok()


def run_recipes(c: Ctx) -> list[Path]:
    return [p for p in c.glob(".claude/skills/run-*/SKILL.md")]


def pr_env_recipe(c: Ctx) -> V:
    if run_recipes(c):
        return ok()
    return bad("рецепт запуска не записан",
               "`.claude/skills/run-<имя>/SKILL.md`: команды установки и старта, "
               "порт, признак готовности. Проверь их на чистом окружении, прежде "
               "чем записывать")


def pr_env_logs(c: Ctx) -> V:
    haystack = c.rules_text() + "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in run_recipes(c))
    haystack += c.read("docs/workflow.md") or ""
    # Раздел «## Логи» — самая частая форма ответа, а заголовки meaningful()
    # отбрасывает. И слово бывает латиницей: путь вида app.log.
    for i, line in enumerate(lines := haystack.splitlines()):
        if not re.search(r"\b(лог|log)", line, re.I):
            continue
        if meaningful(line):
            return ok()
        if HEADING.match(line) and meaningful("\n".join(lines[i + 1:i + 6])):
            return ok()  # заголовок про логи, под ним что-то есть
    return bad("нигде не записано, где логи приложения",
               "в рецепте запуска или своде правил: куда пишутся и как прочитать")


def pr_env_seed(c: Ctx) -> V:
    haystack = c.rules_text() + "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in run_recipes(c))
    haystack += (c.read("docs/infrastructure.md") or "") + (c.read("Makefile") or "")
    if re.search(r"\b(seed|fixture|фикстур|сид|migrate|миграц)", haystack, re.I):
        return ok()
    return bad("не объявлена команда наката тестовых данных",
               "проверка на случайных данных даёт случайный ответ")


def pr_env_secrets(c: Ctx) -> V:
    example = c.read(".env.example")
    if example is None:
        return bad("нет .env.example", "перечислить переменные без значений")
    if not [l for l in example.splitlines() if re.match(r"^\s*[A-Z_][A-Z0-9_]*\s*=", l)]:
        return bad(".env.example пуст", "перечислить переменные, без которых не стартует")
    wt = c.read(".worktreeinclude") or ""
    if ".env" not in wt:
        return bad(".env не попадёт в свежее рабочее дерево",
                   ".worktreeinclude: строка .env")
    return ok()


def pr_env_browser_cfg(c: Ctx) -> V:
    mcp = c.json(".mcp.json") or {}
    servers = mcp.get("mcpServers") or {}
    found = {k: v for k, v in servers.items()
             if "playwright" in k.lower() or "playwright" in json.dumps(v).lower()}
    if not found:
        return bad("Playwright MCP не объявлен", ".mcp.json: сервер playwright")
    # Объявление, которое не запустится, браузера не даёт. Круг 2 закрыл эту
    # пробу строкой в файле, ни разу не подняв сервер. Поднять его отсюда мы
    # не можем — это дорого и интерактивно, — но убедиться, что за строкой
    # стоит исполнимая команда или адрес, можем и обязаны.
    for name, spec in found.items():
        if not isinstance(spec, dict):
            return bad(f"сервер {name} объявлен не объектом", ".mcp.json")
        if spec.get("url") or spec.get("type") in ("http", "sse"):
            return ok(f"{name}: по адресу")
        cmd = spec.get("command")
        if not cmd:
            return bad(f"у сервера {name} нет ни команды, ни адреса", ".mcp.json")
        if shutil.which(cmd):
            return ok(f"{name}: {cmd}")
        return bad(f"команда сервера {name} не найдена: {cmd}",
                   f".mcp.json → {name}: поставить {cmd} или объявить другой запуск")
    return bad("Playwright MCP не объявлен", ".mcp.json: сервер playwright")


# Э6 ------------------------------------------------------------------------
def pr_check_exists(c: Ctx) -> V:
    p = c.p(".claude/check.sh")
    if not p.exists():
        return bad("нет .claude/check.sh", "единая команда проверки")
    if not os.access(p, os.X_OK):
        return bad(".claude/check.sh не исполняем", "chmod +x .claude/check.sh")
    return ok()


LEVEL_HINTS = {
    "линт": r"\b(lint|ruff|eslint|flake8|golangci|clippy)\b",
    "типы": r"\b(mypy|pyright|tsc|typecheck)\b",
    "тесты": r"\b(pytest|test|jest|vitest|go test|cargo test)\b",
}


def pr_check_levels(c: Ctx) -> V:
    # Без среза комментариев проверка из одних объяснений, почему тесты пока
    # не запускаются, засчитывалась как настроенная: пробы искали слова в
    # сыром тексте. Круг 2 прошёл так четыре пробы Э6 из семи.
    text = strip_sh_comments(c.read(".claude/check.sh"))
    if "проверка кода ещё не настроена" in text:
        return bad("check.sh всё ещё угадывает, а не вызывает объявленные уровни",
                   ".claude/check.sh: заменить автоопределение явными командами")
    found = [name for name, rx in LEVEL_HINTS.items() if re.search(rx, text, re.I)]
    if not found:
        return bad("в check.sh не видно ни одного уровня проверки",
                   ".claude/check.sh: линт, типы, тесты — что решили на З6.1")
    return ok("уровни: " + ", ".join(found))


def pr_check_e2e(c: Ctx) -> V:
    text = strip_sh_comments(c.read(".claude/check.sh"))
    if re.search(r"\b(e2e|playwright|cypress|browser)\b", text, re.I):
        return ok()
    return bad("браузерные сценарии не вызываются из check.sh",
               "закомментированный вызов не вызов: способность открыть "
               "страницу без критерия ничего не гарантирует")


def pr_check_green(c: Ctx) -> V:
    p = c.p(".claude/check.sh")
    if not p.exists():
        return bad("нет .claude/check.sh")
    try:
        r = subprocess.run(["bash", str(p)], cwd=c.root, capture_output=True,
                           text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return bad("check.sh не уложился в 600 секунд",
                   "проверку такой длины перестанут запускать")
    except (OSError, subprocess.SubprocessError) as e:
        return bad(f"check.sh не запустился: {e}")
    if r.returncode == 0:
        return ok()
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    return bad(f"check.sh вышел с кодом {r.returncode}: " + " / ".join(tail),
               "прогнать ./.claude/check.sh и прочитать вывод целиком")


def yaml_run_commands(text: str) -> str:
    """Команды из шагов `run:` файла сборки.

    Полного разбора YAML здесь нет и быть не может — зависимости базы это
    bash, git и python3, — но упоминание в комментарии или в названии шага
    командой не считается. Ровно на этом круг 2 получил зелёную пробу при
    красном арбитре."""
    out: list[str] = []
    block: int | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if block is not None:
            if stripped and indent <= block:
                block = None
            else:
                if stripped and not stripped.startswith("#"):
                    out.append(stripped)
                continue
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"-?\s*run:\s*(\|[-+]?|>[-+]?)?\s*(.*)$", stripped)
        if m:
            if m.group(2):
                out.append(m.group(2))
            if m.group(1):
                block = indent
    return "\n".join(out)


def ci_triggers(text: str) -> dict | None:
    """Триггеры сборки: событие → список веток или None, если без ограничения.

    Нужен не общий список веток, а по событию: у `push` в `branches:` стоят
    ветки, КУДА пушат, у `pull_request` — ветки, В КОТОРЫЕ открыт PR. Слитые
    в одну кучу, они давали ложное красное: фича-ветка, уходящая PR-ом в
    develop, проверялась CI, а проба сравнивала её с именами баз. Нашёл
    проект, ведущий на базе живую разработку.
    """
    m = re.search(r"^on:[ \t]*(.*)$", text, re.M)
    if not m:
        return None
    tail = m.group(1).split("#")[0].strip()
    if tail:                              # `on: push` либо `on: [push, pull_request]`
        return {e.strip(): None for e in tail.strip("[]").split(",") if e.strip()}
    body = text[m.end():]
    nxt = re.search(r"^\S", body, re.M)
    if nxt:
        body = body[: nxt.start()]
    lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return None
    indent = min(len(l) - len(l.lstrip()) for l in lines)
    out: dict = {}
    event = None
    in_list = False
    for l in lines:
        lead = len(l) - len(l.lstrip())
        st = l.split("#")[0].strip()
        if lead == indent:
            event = st.lstrip("-").strip().rstrip(":").strip()
            out[event] = None
            in_list = False
            continue
        if event is None:
            continue
        mb = re.match(r"branches:\s*(.*)$", st)
        if mb:
            inline = mb.group(1).strip()
            out[event] = [b.strip().strip("'\"") for b in inline.strip("[]").split(",")
                          if b.strip()] if inline else []
            in_list = not inline
            continue
        if in_list and st.startswith("-"):
            out[event].append(st.lstrip("-").strip().strip("'\""))
            continue
        in_list = False
    return out


def ci_branch_matches(c: Ctx, name: str, text: str) -> V:
    """Арбитр, который слушает не ту ветку, не арбитр.

    Второй круг: проект восемь этапов прожил на `master`, пока файл сборки
    ждал `main`. Гейт был зелёным всё это время — вызов на месте, просто
    никогда не срабатывал."""
    trig = ci_triggers(text)
    if not trig:
        return ok(name)
    rc, branch = c.git("rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0 or not branch or branch == "HEAD":
        # На ветке без коммитов rev-parse молчит, а имя уже есть — и именно
        # тогда несовпадение дешевле всего исправить.
        rc, branch = c.git("symbolic-ref", "--short", "HEAD")
    if rc != 0 or not branch:
        return ok(name)

    def hit(pats: list[str], b: str) -> bool:
        return any(fnmatch.fnmatchcase(b, p.replace("**", "*")) for p in pats)

    push = [e for e in trig if e == "push"]
    if push and (trig["push"] is None or hit(trig["push"], branch)):
        return ok(f"{name}: push в {branch}")
    prs = [e for e in trig if e in ("pull_request", "pull_request_target")]
    if any(trig[e] is None for e in prs):
        return ok(f"{name}: есть триггер без ограничения по веткам")
    # PR-триггер с `branches:` слушает базы. Работа в любой другой ветке
    # проверяется, если хоть одна из баз существует: в неё и уйдёт PR. Нет ни
    # одной — тот самый master при ci на main.
    bases = [b for e in prs for b in trig[e]]
    _, refs = c.git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    _, remotes = c.git("remote")
    rset = set(remotes.split())
    have = set(refs.split())
    have |= {r.split("/", 1)[1] for r in refs.split()
             if "/" in r and r.split("/", 1)[0] in rset}
    live = [b for b in bases if b != branch and (b in have or "*" in b)]
    if live:
        return ok(f"{name}: PR из {branch} в {', '.join(live)}")
    listed = sorted(set(bases) | set(trig.get("push") or []))
    return bad(f"{name} слушает {', '.join(listed) or '—'}, а работа идёт в {branch}",
               "привести имя ветки и триггер сборки в соответствие — иначе "
               "арбитр не запускается ни разу, а гейт зелёный")


def pr_check_ci(c: Ctx) -> V:
    files = c.glob(".github/workflows/*.yml") + c.glob(".github/workflows/*.yaml")
    if not files:
        return bad("нет файла сборки",
                   "арбитр обязан гонять ту же команду, иначе они разойдутся")
    mentioned = None
    for wf in files:
        text = wf.read_text(encoding="utf-8", errors="replace")
        if "check.sh" in yaml_run_commands(text):
            return ci_branch_matches(c, wf.name, text)
        if "check.sh" in text:
            mentioned = wf.name
    if mentioned:
        return bad(f"в {mentioned} check.sh упомянут, но не запускается",
                   "поставить вызов в шаг run: — в комментарии или в названии "
                   "шага он арбитром не становится")
    return bad("CI не вызывает check.sh",
               "арбитр обязан гонять ту же команду, иначе они разойдутся")


# Хостинг, который умеет запускать рабочие процессы. Локальный bare-репозиторий
# их не запускает, и требовать от него зелёный прогон — повторить ошибку,
# которую только что чинили у защиты ветки: гейт, недостижимый для целого
# класса проектов, закрывают враньём.
CI_HOST = re.compile(r"github\.com|gitlab\.|bitbucket\.org|dev\.azure\.com|@[\w.-]+:")


def ci_possible(c: Ctx) -> bool:
    if not (c.glob(".github/workflows/*.yml") or c.glob(".github/workflows/*.yaml")
            or c.exists(".gitlab-ci.yml")):
        return False
    code, out = c.git("remote", "-v")
    return code == 0 and bool(CI_HOST.search(out))


def pr_check_ladder(c: Ctx) -> V:
    return c.frames("docs/workflow.md", "Жёсткость гейта")


# Э7 ------------------------------------------------------------------------
def pr_enforce_permissions(c: Ctx) -> V:
    deny = ((c.settings().get("permissions") or {}).get("deny")) or []
    if deny:
        return ok(f"{len(deny)} запретов")
    return bad("список deny пуст", ".claude/settings.json → permissions.deny")


def pr_enforce_attribution(c: Ctx) -> V:
    """Подписывается ли агент соавтором — решено явно, а не по умолчанию.

    Claude Code по умолчанию ставит `Co-Authored-By` в коммит и строку в PR.
    Многие этого не хотят, и узнают о подписи, когда она уже в истории.
    Ответ «да, подписывать» законен — проба ловит только отсутствие решения.
    Решение бывает проектным (`settings.json`) и личным (`settings.local.json`).
    """
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        cfg = c.json(rel) or {}
        attr = cfg.get("attribution")
        if isinstance(attr, dict) and isinstance(attr.get("commit"), str) \
                and isinstance(attr.get("pr"), str):
            off = attr["commit"] == "" and attr["pr"] == ""
            return ok(f"{rel}: " + ("агент соавтором не подписывается" if off
                                    else "подпись агента задана явно"))
        if isinstance(cfg.get("includeCoAuthoredBy"), bool):
            return ok(f"{rel}: includeCoAuthoredBy (устаревший ключ; новый — attribution)")
    return bad("не решено, подписывается ли агент соавтором",
               ".claude/settings.json → attribution: {\"commit\": \"\", \"pr\": \"\"} — "
               "спросить человека; личное решение — в settings.local.json")


def protected_patterns_of(c: Ctx) -> list[str]:
    """Действующие запреты. Исключения (`!`) сюда не попадают: это разрешение."""
    return [p.lstrip("+") for p in protected_patterns(c) if not p.startswith("!")]


def protected_patterns(c: Ctx) -> list[str]:
    out = []
    for line in (c.read(".claude/protected-paths.txt") or "").splitlines():
        line = line.split("#")[0].replace(" ", "")
        if line:
            out.append(line)
    return out


def pr_enforce_protected(c: Ctx) -> V:
    if protected_patterns(c):
        return ok()
    return bad("нет .claude/protected-paths.txt или он пуст",
               "перечислить файлы, которые правит только человек")


def pr_enforce_invariants(c: Ctx) -> V:
    text = c.read(".claude/invariants.md")
    if not meaningful(text):
        return bad(".claude/invariants.md пуст",
                   "то, потеря чего ломает работу после сжатия контекста")
    # Три строки приносит каркас, и они верны для любого проекта. Проба,
    # довольная ими, не говорит о проекте ничего — а слот в конце заготовки
    # прямо просит дописать своё.
    if SLOT.search(FENCE.sub("", COMMENT.sub("", text))):
        return bad("в инвариантах остался слот — проектного ничего не дописано",
                   ".claude/invariants.md: 3–7 строк, без которых агент "
                   "начнёт делать неправильно немедленно")
    return ok()


def pr_enforce_paths_work(c: Ctx) -> V:
    pats = [p.lstrip("+") for p in protected_patterns(c)]
    if not pats:
        return bad("нечего проверять: список защищённых путей пуст")
    target = c.root / pats[0].lstrip("/")
    # Голый вызов: только абсолютный путь к файлу, без подсказок про проект.
    code = call_hook("protect-paths.sh", {"tool_input": {"file_path": str(target)}},
                     c.root, bare=True)
    if code == 2:
        return ok()
    return bad(f"запрет на правку не сработал (код {code}, ждали 2)",
               "хук должен определять проект по самому файлу; проверь, что "
               "hooks.json подключён и скрипт исполняется")


def pr_enforce_bash_works(c: Ctx) -> V:
    # Строка собирается из кусков намеренно: целиком она есть шаблон, на
    # который реагирует сам guard-bash, и файл нельзя было бы даже записать.
    danger = "rm -rf " + chr(47)
    code = call_hook("guard-bash.sh", {"tool_input": {"command": danger},
                                       "cwd": str(c.root)}, c.root)
    if code == 2:
        return ok()
    return bad(f"запрет на команду не сработал (код {code}, ждали 2)",
               "проверь подключение хука PreToolUse: Bash")


def pr_enforce_gate_works(c: Ctx) -> V:
    """Гейт проверяется на заведомо красном — во временном каталоге, не в проекте."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / ".claude").mkdir()
        red = d / ".claude" / "check.sh"
        red.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
        red.chmod(0o755)
        code = call_hook("gate-check.sh", {"cwd": str(d)}, d, timeout=30)
    if code == 2:
        return ok()
    return bad(f"гейт пропустил красную проверку (код {code}, ждали 2)",
               "Stop-хук не подключён либо gate-check.sh не находит check.sh")


# Э8 ------------------------------------------------------------------------
EDIT_TOOLS = ("Edit", "Write", "NotebookEdit", "MultiEdit")


def agent_file(c: Ctx, name: str) -> Path | None:
    for base in (c.root / ".claude" / "agents", HERE.parent / "agents"):
        p = base / f"{name}.md"
        if p.exists():
            return p
    return None


# Кто делает и кто проверяет — объявляет проект, а не привозит база. Раньше
# обе пробы разрешали имена implementer/reviewer через каталог агентов самого
# плагина и потому были зелены всегда: они описывали базу, а не проект. Свойство
# «исполнение и оценка разведены» при этом не проверялось, а утверждалось.
# ADR-0011.
ROLE_AGENT, ROLE_CMD, ROLE_HUMAN = "агент", "команда", "человек"
ROLE_KINDS = (ROLE_AGENT, ROLE_CMD, ROLE_HUMAN)
ROLE_MARK = " | ".join(f"← {k}" for k in ROLE_KINDS)


def role_decl(c: Ctx, label: str) -> tuple[str, str]:
    """(кто, чем является) из docs/workflow.md → «Кто делает»."""
    body = section(c.read("docs/workflow.md") or "", "Кто делает")
    if not meaningful(body):
        return ("", "")
    m = re.search(rf"^\s*[-*]\s*\*\*{label}:?\*\*:?\s*(.+)$", body, re.M)
    if not m:
        return ("", "")
    raw = m.group(1).strip()
    kind = next((k for k in ROLE_KINDS if re.search(rf"←\s*{k}", raw)), "")
    return (re.sub(r"←.*$", "", raw).strip().strip("`*"), kind)


def pr_roles_defined(c: Ctx) -> V:
    if not meaningful(section(c.read("docs/workflow.md") or "", "Кто делает")):
        return bad("не объявлено, кто делает работу и кто её проверяет",
                   f"docs/workflow.md, раздел «Кто делает»: две строки с маркером {ROLE_MARK}")
    seen, out = {}, []
    for label in ("Исполнитель", "Проверяющий"):
        who, kind = role_decl(c, label)
        if not who:
            out.append(f"нет строки «{label}:»")
            continue
        if not kind:
            out.append(f"у «{label}» нет маркера {ROLE_MARK}")
            continue
        if kind == ROLE_AGENT and agent_file(c, who) is None:
            out.append(f"{label} назван агентом «{who}», а такой роли нет "
                       "ни в .claude/agents/, ни в плагинах")
        seen[label] = (who, kind)
    if out:
        return bad("; ".join(out), "docs/workflow.md, раздел «Кто делает»")
    if len(seen) == 2 and seen["Исполнитель"] == seen["Проверяющий"]:
        return bad(f"исполнитель и проверяющий — одно и то же ({seen['Исполнитель'][0]})",
                   "писавший код оценивает свой замысел, а не результат; "
                   "нужны разные")
    return ok(", ".join(f"{k.lower()}: {v[0]} ({v[1]})" for k, v in seen.items()))


def pr_roles_split(c: Ctx) -> V:
    who, kind = role_decl(c, "Проверяющий")
    if not kind:
        return bad("не объявлено, кем проверяется работа",
                   f"docs/workflow.md → «Кто делает»: **Проверяющий:** <кто> {ROLE_MARK}")
    if kind != ROLE_AGENT:
        # Честная ветка. У человека права правки есть по определению, у чужой
        # команды их не прочитать — требовать обратного значит учить закрывать
        # пробу враньём. Выбор записан и виден, это и есть его цена.
        return ok(f"проверяет {kind} «{who}» — машинной гарантии нет")
    p = agent_file(c, who)
    if p is None:
        return bad(f"роли «{who}» нет", "docs/workflow.md → «Кто делает»")
    head = p.read_text(encoding="utf-8", errors="replace")
    fm = head.split("---")[1] if head.startswith("---") and head.count("---") >= 2 else ""
    m = re.search(r"^tools:\s*(.+)$", fm, re.M)
    if not m:
        return bad(f"у проверяющего «{who}» не ограничен набор инструментов",
                   "frontmatter роли: tools: Read, Grep, Glob, Bash")
    tools = {t.strip() for t in m.group(1).split(",")}
    leaked = sorted(tools & set(EDIT_TOOLS))
    if leaked:
        return bad(f"проверяющий «{who}» умеет править: " + ", ".join(leaked),
                   "он начнёт чинить найденное вместо того, чтобы доложить, "
                   "и находка не дойдёт до человека")
    return ok(f"{who}: только чтение")


def pr_roles_isolation(c: Ctx) -> V:
    if meaningful(c.read(".worktreeinclude")):
        return ok()
    return bad(".worktreeinclude пуст",
               "свежее дерево получает чистый checkout — что нужно, перечисляется явно")


def pr_roles_board(c: Ctx) -> V:
    if not c.p("specs").is_dir():
        return bad("нет каталога задач specs/", "общее состояние задачи — единственный канал координации")
    if not meaningful(c.read("specs/README.md")):
        return bad("формат задач не объявлен", "specs/README.md: что за файлы и как они работают")
    # Доска отвечает, что взято. Отдельно нужно, что делать при пересечении:
    # бесконфликтный случай устраивается сам, а вот двое в одном файле — нет.
    if not meaningful(section(c.read("docs/workflow.md") or "", "Когда двое трогают одно")):
        return bad("не записано, что делать, когда двое трогают один файл",
                   "docs/workflow.md, раздел «Когда двое трогают одно»")
    return pr_roles_tasks_home(c)


# Проверяем свойство, а не инструмент: правило переживёт и смену трекера, и
# уход любого из сегодняшних решений, а проба на конкретный плагин — нет.
# ADR-0008.
TASKS_OUTSIDE = "вне дерева"
TASKS_INSIDE = "в дереве, один агент за раз"


def pr_roles_tasks_home(c: Ctx) -> V:
    body = section(c.read("docs/workflow.md") or "", "Где живут задачи")
    if not meaningful(body):
        return bad("не записано, где живёт общее состояние задач",
                   "docs/workflow.md, раздел «Где живут задачи»")
    m = re.search(r"Хранилище:\s*(.+)", body)
    if not m:
        return bad("в разделе «Где живут задачи» нет строки «Хранилище:»",
                   "закончить раздел маркером: Хранилище: <что> ← "
                   f"{TASKS_OUTSIDE} | {TASKS_INSIDE}")
    line = m.group(1)
    if TASKS_INSIDE in line:
        # Честный однопоточный режим. Ничего не проверяем сверх того, что
        # выбор сделан осознанно: файл в репозитории для одного агента
        # работает, и запрещать его незачем.
        return ok("состояние в дереве, работа однопоточная")
    if TASKS_OUTSIDE not in line:
        return bad("у строки «Хранилище:» нет маркера",
                   f"дописать ← {TASKS_OUTSIDE} или ← {TASKS_INSIDE}")
    # Заявлено «вне дерева». Если названа не встроенная механика, а сервер —
    # он должен быть объявлен: круг 2 закрыл соседнюю пробу строкой в файле,
    # ни разу не подняв сервер, и повторять это здесь не будем.
    if re.search(r"\bMCP\b", line, re.I):
        servers = (c.json(".mcp.json") or {}).get("mcpServers") or {}
        if not servers:
            return bad("состояние задач заявлено в MCP, но серверов в .mcp.json нет",
                       ".mcp.json: объявить сервер трекера — см. Э5")
        return ok(f"вне дерева, серверов в .mcp.json: {len(servers)}")
    return ok("вне дерева")


# Э9 ------------------------------------------------------------------------
def pr_cycle_intake(c: Ctx) -> V:
    return c.frames("docs/workflow.md", "Откуда берётся задача")


# Конвейер фич выбирает проект: свой, Spec Kit, OpenSpec, BMAD. База его не
# несёт и не навязывает — она объявляет **интерфейс** к нему. Пять полей
# ниже — всё, что нужно, чтобы машинная проверка стала возможна при любом
# выборе: без них гейту нечего читать, а имя конвейера в toolchain.md ему
# ничего не говорит. ADR-0007: проверяем свойство, а не инструмент.
#
# Проба ничего не запускает намеренно. Названную проверку исполняет
# `.claude/check.sh`, а её зелёность держит check.green: гейт, который сам
# бегает по объявленным командам, — вторая точка запуска и второй источник
# правды о том, что считается пройденным.
SPEC_FIELDS = (
    ("Артефакты", "где лежат файлы фичи и как зовётся файл спеки"),
    ("Готова к коду", "по какому признаку видно, что спеку можно брать в работу"),
    ("Задача → требование", "как задача ссылается на требование"),
    ("Готовность ставит", "кто и когда переводит спеку в готовую"),
    ("Проверка формы", "команда, и она обязана вызываться из проверки проекта"),
)

# Команда узнаётся по имени файла с расширением или по пути со слэшем. Проза
# («машинной нет», «держится ревью») таких токенов не содержит — и это ровно
# тот ответ, который проба обязана не принять.
SPEC_CMD = re.compile(r"[\w.\-/]*[\w\-]+\.(?:py|sh|js|mjs|ts|rb|pl|php|go|exe)\b"
                      r"|[\w.\-]+/[\w.\-/]+")
# Цель сборщика — такая же исполнимая проверка, как скрипт: `npm run
# check:specs` ловится по имени цели, которое лежит в package.json.
SPEC_TASK = re.compile(r"\b(?:npm|pnpm|yarn|bun|deno)\s+run\s+([\w:.\-]+)"
                       r"|\b(?:make|just|task|nox|tox|cargo)\s+(?:-s\s+)?([\w:.\-]+)")


def spec_commands(declared: str) -> list[str]:
    """Что в объявлении похоже на исполнимую проверку. Пусто — это проза."""
    out = SPEC_CMD.findall(declared)
    out += [g for pair in SPEC_TASK.findall(declared) for g in pair if g]
    return out

# Где команда может вызываться. Список закрыт: check.sh — контракт Э6, но он
# часто делегирует, и требовать имя скрипта именно в нём значит краснеть на
# проекте, который всё сделал правильно через make (ADR-0011, правило 1).
CHECK_HOMES = (".claude/check.sh", "Makefile", "justfile", "package.json",
               "pyproject.toml", "Taskfile.yml", "noxfile.py")
# Имя самого контейнера проверкой не считается: «вызывается из check.sh» без
# скрипта иначе находило бы себя в тексте check.sh и зеленело впустую.
CHECK_OWN = {Path(h).name for h in CHECK_HOMES}


def spec_field(text: str, name: str) -> str:
    """Значение поля как написано. Пустым считается незаполненный слот.

    Возвращается **сырая** строка, а не результат meaningful(): тот прячет
    код-спаны под заглушку, и объявленная в обратных кавычках команда
    исчезала ровно там, где её надо прочитать."""
    m = re.search(rf"^\s*[-*]\s*\*\*{re.escape(name)}:?\*\*:?\s*(.+)$", text, re.M)
    if not m:
        return ""
    raw = m.group(1).strip()
    return raw if meaningful(raw) else ""


def check_homes(c: Ctx) -> list[tuple[str, str]]:
    out = [(rel, c.read(rel) or "") for rel in CHECK_HOMES if c.exists(rel)]
    out += [(p.relative_to(c.root).as_posix(),
             p.read_text(encoding="utf-8", errors="replace"))
            for p in c.glob(".github/workflows/*.yml")]
    return out


def pr_cycle_specs(c: Ctx) -> V:
    text = c.read("specs/README.md")
    if not meaningful(text):
        return bad("конвейер фич не объявлен",
                   "specs/README.md, раздел «Конвейер фич»: пять строк — "
                   + "; ".join(n for n, _ in SPEC_FIELDS))
    missing = [n for n, _ in SPEC_FIELDS if not spec_field(text, n)]
    if missing:
        return bad("не объявлено: " + ", ".join(missing),
                   "; ".join(f"**{n}:** {hint}" for n, hint in SPEC_FIELDS
                             if n in missing))

    # Форма, которую ничего не проверяет, не держится даже у того, кто её
    # придумал: три прогона обкатки завели три разные формы и ни одной
    # проверки. Поэтому поле обязано называть команду, а команда — где-то
    # вызываться. Какую форму она проверяет — не наше дело (ADR-0010).
    declared = spec_field(text, "Проверка формы")
    tokens = [x for x in spec_commands(declared) if Path(x).name not in CHECK_OWN]
    if not tokens:
        return bad(f"«Проверка формы» не называет команду: {short(declared, 60)}",
                   "назвать исполнимую проверку — скрипт или путь к нему. "
                   "Договорённость без исполнимой проверки — не гейт (Э6)")
    for rel, body in check_homes(c):
        for tok in tokens:
            if tok in body:
                return ok(f"{tok} вызывается из {rel}")
    return bad(f"проверка формы объявлена ({tokens[0]}), но нигде не вызывается",
               "вызвать её из .claude/check.sh — той единственной команды, "
               "которую гоняют гейт и CI. Проверка, которую никто не "
               "запускает, ничего не ловит")


def pr_cycle_goal(c: Ctx) -> V:
    v = c.frames("docs/workflow.md", "Условие завершения")
    if v.verdict != OK:
        return v
    body = meaningful(section(c.read("docs/workflow.md") or "", "Условие завершения"))
    if not re.search(r"\b(ход|шаг|итерац)", body, re.I):
        return bad("в шаблоне условия нет границы по ходам",
                   "условие без границы это цикл: «или остановись после N ходов»")
    return ok()


def pr_cycle_verify(c: Ctx) -> V:
    """Подтверждение на живом приложении.

    Раньше проба искала `.claude/skills/verify/SKILL.md` — артефакт команды
    `/verify`, которой в Claude Code может не быть вовсе. Строить гейт вокруг
    команды, существование которой не проверено, — то же самое, что строить
    его вокруг обещания. Проверяется то, что делает проект: записанный рецепт
    запуска и сказанное вслух, чем подтверждается работа на живом приложении.
    """
    if c.exists(".claude/skills/verify/SKILL.md"):
        return ok()
    if not run_recipes(c):
        return bad("нечем поднять приложение для проверки вживую",
                   "рецепт `.claude/skills/run-<имя>/SKILL.md`")
    body = meaningful(section(c.read("docs/workflow.md") or "", "Кто проверяет"))
    if not re.search(r"жив|вручную|браузер|прогон приложени", body, re.I):
        return bad("не сказано, чем подтверждается работа на живом приложении",
                   "docs/workflow.md → «Кто проверяет»: тесты зелёные ≠ фича работает")
    return ok()


def pr_cycle_review(c: Ctx) -> V:
    return c.frames("docs/workflow.md", "Кто проверяет")


def pr_cycle_branching(c: Ctx) -> V:
    return c.frames("docs/workflow.md", "Ветки и мерж")


def pr_cycle_rollback(c: Ctx) -> V:
    return c.frames("docs/workflow.md", "Откат")


def pr_cycle_release(c: Ctx) -> V:
    """Как выходит версия. «Релизов нет» — законный ответ, если назван."""
    return c.frames("docs/workflow.md", "Релизы")


# Э10 -----------------------------------------------------------------------
def main_checkout(c: Ctx) -> Path | None:
    """Основной checkout, если мы в рабочем дереве. Иначе None."""
    rc1, common = c.git("rev-parse", "--git-common-dir")
    rc2, gitdir = c.git("rev-parse", "--git-dir")
    if rc1 or rc2 or not common or common.strip() == gitdir.strip():
        return None
    q = Path(common.strip())
    if not q.is_absolute():
        q = (c.root / common.strip()).resolve()
    return q.parent


def agents_ran(q: Path) -> bool:
    """В журнале есть запуск сабагента.

    Непустоты мало: с 0.16.2 туда же пишутся закрытия ходов, красный гейт и
    запреты хуков, и журнал непуст, даже если ни один агент не запускался.
    """
    try:
        with open(q, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"SubagentStart"' in line or '"SubagentStop"' in line:
                    return True
    except OSError:
        pass
    return False


def pr_observe_log(c: Ctx) -> V:
    p = c.p(".claude/logs/agents.jsonl")
    if agents_ran(p):
        return ok()
    # log-agent.sh намеренно пишет в каталог сессии, а не в дерево, где
    # оказался сабагент: агент принадлежит запустившей его сессии. Если
    # сессия открыта не в проекте — из worktree, из соседнего каталога, со
    # стенда, — журнал непуст, но лежит не здесь. Требовать его здесь значит
    # требовать невозможного: три прогона обкатки подряд не смогли закрыть
    # Э10 именно так и правильно отказались подложить файл руками.
    sess = os.environ.get("CLAUDE_PROJECT_DIR")
    if sess:
        q = Path(sess) / ".claude" / "logs" / "agents.jsonl"
        if q.resolve() != p.resolve() and agents_ran(q):
            return ok(f"журнал ведётся в каталоге сессии: {q}")
    # Пробы гоняют и в рабочем дереве — например, чтобы понять, что там
    # покраснело. `.claude/logs/` в игноре и в дерево не копируется, поэтому
    # журнала там нет никогда. Спрашиваем основной checkout: журнал ведётся
    # в проекте сессии, а дерево — лишь её временный checkout.
    main = main_checkout(c)
    if main:
        q = main / ".claude" / "logs" / "agents.jsonl"
        if agents_ran(q):
            return ok(f"журнал в основном checkout: {q}")
    return bad("в журнале нет ни одного запуска агента",
               "он непуст только если агенты уже работали — закроется на Э11")


def pr_observe_journal(c: Ctx) -> V:
    """Журнал сессии включён и не роняет систему документации.

    Хук журнала молчит, если нет docs/journal/, — и молчит незаметно. Проект
    narta, настроенный до появления журнала, провёл так ночной автономный
    прогон: сжатие вернуло бы агенту только инварианты.
    """
    if not c.p("docs/journal").is_dir():
        return bad("журнал сессии выключен: нет docs/journal/",
                   "завести docs/journal/README.md из каркаса — без каталога хук "
                   "молчит, и после сжатия контекста агенту вернутся только инварианты")
    cfg = c.doc_config()
    if cfg:
        excl = [str(x) for x in cfg.get("exclude") or []]
        sample = "docs/journal/2026-01-01.md"
        if not any(fnmatch.fnmatchcase(sample, p) for p in excl):
            return bad("система документации проверяет записи журнала — у них нет frontmatter",
                       ".claude/doc-config.json → exclude: добавить \"docs/journal/**\"")
    return ok()


def pr_observe_rule(c: Ctx) -> V:
    text = c.read("docs/lessons.md")
    if len(table_rows(text)) < 3:
        return bad("таблица «наблюдение → во что превращается» не заполнена",
                   "docs/lessons.md")
    # Таблицу триггеров приносит каркас, поэтому сама по себе она зелёная с
    # первой минуты и ничего про проект не говорит. Проектное здесь одно:
    # кто и когда разбирает накопленное.
    if not meaningful(section(text or "", "Разбор")):
        return bad("не сказано, кто и как часто разбирает накопленное",
                   "docs/lessons.md, раздел «Разбор»")
    return ok()


def pr_observe_lessons(c: Ctx) -> V:
    if c.exists("docs/lessons.md"):
        return ok()
    return bad("нет docs/lessons.md", "место, куда складывается выученное")


# Э11 -----------------------------------------------------------------------
FRAMES_DOCS = ("docs/constitution.md", "docs/tech-stack.md", "docs/structure.md",
               "docs/definition-of-done.md", "docs/workflow.md")


def strip_sh_comments(text: str | None) -> str:
    """Скрипт без строк-комментариев. Проба, ищущая флаг подстрокой, иначе
    находит его в объяснении, почему флаг снят."""
    return "\n".join(l for l in (text or "").splitlines()
                     if not l.lstrip().startswith("#"))


def pr_dry_strict(c: Ctx) -> V:
    if "--soft" in strip_sh_comments(c.read(".claude/check.sh")):
        return bad("в check.sh остался --soft",
                   "послабление на время настройки снимается, когда рамки дописаны")
    # Защита документов рамок — такое же послабление наоборот: пока они
    # заполняются, запрет мешает, после — обязателен.
    guarded = set(protected_patterns_of(c))
    missing = [d for d in FRAMES_DOCS if d not in guarded]
    if missing:
        return bad("документы рамок не защищены: " + ", ".join(missing),
                   ".claude/protected-paths.txt: раскомментировать строки рамок")
    return ok()


def pr_dry_frames(c: Ctx) -> V:
    script = c.p(".claude/check-frames.py")
    if not script.exists():
        return bad("нет .claude/check-frames.py")
    try:
        r = subprocess.run([sys.executable, str(script)], cwd=c.root,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return bad(f"check-frames.py не запустился: {e}")
    if r.returncode == 0:
        return ok()
    tail = (r.stdout + r.stderr).strip().splitlines()
    return bad("; ".join(tail[:3]) or "в документах рамок остались слоты",
               "прогнать python3 .claude/check-frames.py")


def pr_dry_baseline(c: Ctx) -> V:
    rc, out = c.git("status", "--porcelain")
    if rc != 0:
        return bad("git недоступен")
    if out:
        return bad("дерево не чисто — база не зафиксирована", "закоммитить прогон")
    return ok()


# --------------------------------------------------------------------------
# Реестр
# --------------------------------------------------------------------------
M = "docs/product/mission.md"
PROBES = [
    Probe("git.repo", "Э0", "это git-репозиторий", run=pr_git_repo),
    Probe("git.ignore", "Э0", "агентские записи в .gitignore",
          fills=(".gitignore", None), run=pr_git_ignore),
    Probe("git.commit", "Э0", "есть база, от которой считается диф", run=pr_git_commit),
    Probe("git.protected", "Э0", "основная ветка защищена", kind=HUMAN, needs="remote",
          fills=("правило защиты ветки на хостинге", None)),

    Probe("entry.files", "Э1", "свод правил существует",
          fills=("решение З1.1 — AGENTS.md либо CLAUDE.md", None), run=pr_entry_files),
    Probe("entry.import", "Э1", "источник истины один", run=pr_entry_import),
    Probe("entry.size", "Э1", "свод не разросся", run=pr_entry_size),
    Probe("entry.plugins", "Э1", "инструменты конвейера объявлены", run=pr_entry_plugins),
    Probe("entry.docsys", "Э1", "система документации развёрнута", run=pr_entry_docsys),
    Probe("entry.sources", "Э1", "принесённые материалы оформлены",
          fills=("docs/sources/<slug>.md", None), run=pr_entry_sources),

    Probe("product.docs", "Э2", "документы заведены", run=pr_product_docs),
    Probe("product.meta", "Э2", "метаданные допустимы", run=pr_product_meta),
    Probe("product.antigoals", "Э2", "граница объёма задана",
          fills=(M, "Чего продукт НЕ делает"), run=pr_product_antigoals),
    Probe("product.glossary", "Э2", "словарь не пуст",
          fills=("docs/product/glossary.md", "таблица терминов"), run=pr_product_glossary),
    # Словарь намеренно вне watch: он пополняется на каждой фиче — термины и
    # ключи ответов заводят раньше кода. Держать его здесь значит протухать
    # подтверждение «это мой текст» восемь раз за восемь фич, а подтверждение,
    # которое переспрашивают без повода, начинают закрывать не глядя.
    # Качество самого словаря держит product.glossary и аудит документации.
    Probe("product.audit", "Э2", "заполнено осмысленно", kind=HUMAN,
          watch=PRODUCT_INTENT),
    Probe("product.owned", "Э2", "документ свой, а не конспект чужого", kind=HUMAN,
          watch=PRODUCT_INTENT, applies=lambda c: any(
              re.search(r"^sources:\s*\S", c.read(d) or "", re.M) for d in PRODUCT_DOCS)),

    Probe("const.exists", "Э3", "конституция заведена", run=pr_const_exists),
    Probe("const.count", "Э3", "принципов 5–9",
          fills=("docs/constitution.md", "Принципы"), run=pr_const_count),
    Probe("const.markers", "Э3", "у каждого принципа способ исполнения",
          fills=("docs/constitution.md", "строка Исполнение: у каждого принципа"),
          run=pr_const_markers),
    Probe("const.governance", "Э3", "порядок изменения записан",
          fills=("docs/constitution.md", "Изменение конституции"), run=pr_const_governance),
    Probe("dod.exists", "Э3", "«готово» определено и исполнимо",
          fills=("docs/definition-of-done.md", "пункт «проектные пункты»"), run=pr_dod_exists),
    Probe("const.enforced", "Э3", "обещания «машинно» подтверждены", kind=HUMAN,
          watch=["docs/constitution.md", ".claude/settings.json"],
          fills=("подтверждение const.enforced", None), confirm_at="Э7"),
    Probe("const.audit", "Э3", "принципы обоснованы, ограничения измеримы", kind=HUMAN,
          watch=["docs/constitution.md", "docs/definition-of-done.md"]),

    Probe("stack.exists", "Э4", "стек зафиксирован",
          fills=("docs/tech-stack.md", "таблица стека"), run=pr_stack_exists),
    Probe("stack.forbidden", "Э4", "список запрещённого непуст",
          fills=("docs/tech-stack.md", "Запрещено тянуть"), run=pr_stack_forbidden),
    Probe("stack.model", "Э4", "данные и модель описаны", needs="model",
          fills=("docs/tech-stack.md", "Данные и модель"), run=pr_stack_model),
    Probe("structure.exists", "Э4", "раскладка описана", run=pr_structure_exists),
    Probe("structure.principle", "Э4", "записан признак размещения",
          fills=("docs/structure.md", "Принцип"), run=pr_structure_principle),
    Probe("adr.first", "Э4", "формат решений заведён",
          fills=("docs/decisions/adr-NNN-*.md", None), run=pr_adr_first),

    Probe("stack.audit", "Э4", "выбор обоснован, раскладка применима", kind=HUMAN,
          watch=["docs/tech-stack.md", "docs/structure.md"]),

    Probe("env.lock", "Э5", "зависимости воспроизводимы", run=pr_env_lock),
    Probe("env.recipe", "Э5", "запуск записан, а не угадывается",
          fills=("рецепт .claude/skills/run-<имя>/SKILL.md", None), run=pr_env_recipe),
    Probe("env.logs", "Э5", "агент видит ошибки приложения",
          fills=("рецепт запуска либо свод правил", "раздел «Команды»"), run=pr_env_logs),
    Probe("env.seed", "Э5", "состояние воспроизводимо", needs="storage",
          fills=("команда наката и сброса данных", None), run=pr_env_seed),
    Probe("env.secrets", "Э5", "стартует у пришедшего впервые",
          fills=(".env.example", None), run=pr_env_secrets),
    Probe("env.boots", "Э5", "приложение действительно поднимается", kind=HUMAN,
          watch=[".claude/skills"]),
    Probe("env.browser-cfg", "Э5", "браузер подключён", needs="ui", run=pr_env_browser_cfg),
    Probe("env.browser-works", "Э5", "браузер доходит до приложения", kind=HUMAN,
          needs="ui", watch=[".mcp.json"]),

    Probe("check.exists", "Э6", "единая команда есть", run=pr_check_exists),
    Probe("check.levels", "Э6", "уровни решены, а не подразумеваются",
          fills=(".claude/check.sh", None), run=pr_check_levels),
    Probe("check.e2e", "Э6", "браузерные сценарии в контракте", needs="ui",
          fills=(".claude/check.sh", "вызов e2e"), run=pr_check_e2e),
    Probe("check.green", "Э6", "проверка проходит", cost=EXPENSIVE, run=pr_check_green),
    Probe("check.ci", "Э6", "арбитр вызывает ту же команду",
          fills=("workflow CI", None), run=pr_check_ci),
    Probe("check.ladder", "Э6", "жёсткость гейта выбрана",
          fills=("docs/workflow.md", "Жёсткость гейта"), run=pr_check_ladder),
    Probe("check.ci-ran", "Э6", "беспристрастный прогон хоть раз состоялся",
          kind=HUMAN, needs="remote", watch=[".claude/check.sh"],
          applies=ci_possible,
          fills=("подтверждение зелёного прогона CI", None)),
    Probe("check.red", "Э6", "проверка краснеет на сломанном", kind=HUMAN,
          watch=[".claude/check.sh"]),

    Probe("enforce.permissions", "Э7", "опасное закрыто правами",
          fills=(".claude/settings.json", "deny"), run=pr_enforce_permissions),
    Probe("enforce.protected", "Э7", "защищённые пути объявлены",
          fills=(".claude/protected-paths.txt", None), run=pr_enforce_protected),
    Probe("enforce.invariants", "Э7", "критичное переживёт компакцию",
          fills=(".claude/invariants.md", None), run=pr_enforce_invariants),
    Probe("enforce.attribution", "Э7", "соавторство агента решено явно",
          fills=(".claude/settings.json", "attribution"), run=pr_enforce_attribution),
    Probe("enforce.paths-work", "Э7", "запрет на правку срабатывает", run=pr_enforce_paths_work),
    Probe("enforce.bash-works", "Э7", "запрет на команду срабатывает", run=pr_enforce_bash_works),
    Probe("enforce.gate-works", "Э7", "красная проверка держит ход", run=pr_enforce_gate_works),

    Probe("roles.defined", "Э8", "названо, кто делает и кто проверяет",
          fills=("docs/workflow.md", "Кто делает"), run=pr_roles_defined),
    Probe("roles.split", "Э8", "исполнение и оценка разведены",
          fills=("docs/workflow.md", "Кто делает"), run=pr_roles_split),
    Probe("roles.isolation", "Э8", "свежее дерево заведётся",
          fills=(".worktreeinclude", None), run=pr_roles_isolation),
    Probe("roles.board", "Э8", "общее состояние задачи есть",
          fills=("каталог задач с объявленным форматом", None), run=pr_roles_board),
    Probe("roles.parallel", "Э8", "два агента не столкнулись", kind=HUMAN,
          watch=[".worktreeinclude"]),

    Probe("cycle.specs", "Э9", "конвейер фич объявлен так, что его можно проверить",
          fills=("конвейер фич: specs/README.md", None), run=pr_cycle_specs),
    Probe("cycle.intake", "Э9", "путь задачи записан",
          fills=("docs/workflow.md", "Откуда берётся задача"), run=pr_cycle_intake),
    Probe("cycle.goal", "Э9", "шаблон условия готов",
          fills=("docs/workflow.md", "Условие завершения"), run=pr_cycle_goal),
    Probe("cycle.verify", "Э9", "подтверждение на живом приложении", needs="ui",
          run=pr_cycle_verify),
    Probe("cycle.review", "Э9", "независимая проверка в конвейере",
          fills=("docs/workflow.md", "Кто проверяет"), run=pr_cycle_review),
    Probe("cycle.branching", "Э9", "путь до основной ветки",
          fills=("docs/workflow.md", "Ветки и мерж"), run=pr_cycle_branching),
    Probe("cycle.rollback", "Э9", "порядок отката записан",
          fills=("docs/workflow.md", "Откат"), run=pr_cycle_rollback),
    Probe("cycle.release", "Э9", "порядок выпуска записан",
          fills=("docs/workflow.md", "Релизы"), run=pr_cycle_release),

    Probe("observe.log", "Э10", "видно, кто что делал",
          fills=("формат .claude/logs/agents.jsonl", None), run=pr_observe_log),
    Probe("observe.journal", "Э10", "журнал сессии переживёт сжатие",
          fills=("docs/journal/", None), run=pr_observe_journal),
    Probe("observe.rule", "Э10", "обратная связь формализована", run=pr_observe_rule),
    Probe("observe.lessons", "Э10", "есть куда складывать выученное", run=pr_observe_lessons),
    Probe("observe.plugins", "Э10", "набор плагинов пересмотрен", kind=HUMAN,
          watch=["docs/toolchain.md"], fills=("docs/toolchain.md", "Установлено в этом проекте")),

    Probe("dry.strict", "Э11", "послабления сняты",
          fills=("снятие --soft и временных исключений", None), run=pr_dry_strict),
    Probe("dry.frames", "Э11", "документы дозаполнены", run=pr_dry_frames),
    Probe("dry.passed", "Э11", "задача прошла весь путь", kind=HUMAN,
          watch=[".claude/check.sh"], fills=("выбор задачи для прогона", None)),
    Probe("dry.baseline", "Э11", "база зафиксирована", run=pr_dry_baseline),
]
BY_ID = {p.id: p for p in PROBES}


# --------------------------------------------------------------------------
# Файл состояния
# --------------------------------------------------------------------------
STATE_REL = ".claude/setup.json"
STATE_VERSION = 1


class StateError(Exception):
    pass


class State:
    def __init__(self, traits=None, confirmed=None):
        self.traits = dict(traits or {})
        self.confirmed = dict(confirmed or {})

    @classmethod
    def load(cls, ctx: Ctx) -> "State":
        path = ctx.p(STATE_REL)
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            raise StateError(f"{STATE_REL} не разбирается: {e}. Файл не тронут.") from e
        if not isinstance(data, dict):
            raise StateError(f"{STATE_REL}: ожидался объект. Файл не тронут.")
        return cls(data.get("traits"), data.get("confirmed"))

    def save(self, ctx: Ctx) -> None:
        try:
            if ctx.root.resolve() == Path.home().resolve():
                raise StateError(
                    "корнем проекта определён домашний каталог — писать туда "
                    "нельзя. Запусти из каталога проекта или заведи git.")
        except (OSError, RuntimeError):
            pass
        path = ctx.p(STATE_REL)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"version": STATE_VERSION, "traits": self.traits, "confirmed": self.confirmed}
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fingerprint(ctx: Ctx, watch) -> dict:
    """Отпечаток наблюдаемых файлов. Каталог сворачивается в список имён:
    важно не содержимое рецепта, а то, что он есть и не подменён."""
    out = {}
    for rel in watch:
        p = ctx.p(rel)
        if p.is_dir():
            names = sorted(x.name for x in p.iterdir())
            out[rel] = hashlib.sha256("\n".join(names).encode()).hexdigest()[:8]
        elif p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:8]
        else:
            out[rel] = None
    return out


def check_confirmation(probe: Probe, ctx: Ctx, state: State) -> V:
    rec = state.confirmed.get(probe.id)
    if not rec:
        return V(FAIL, "требует подтверждения",
                 f"выполни и подтверди: setup_state.py confirm {probe.id}")
    now = fingerprint(ctx, probe.watch)
    was = rec.get("fingerprint") or {}
    # Сверяем по нынешнему списку наблюдаемых, а не по объединению с
    # записанным. Иначе файл, снятый из наблюдения, числится изменённым
    # навсегда: сужение списка не действует, пока не переподпишут. Так и
    # вышло, когда словарь убрали из watch у product.*.
    #
    # Файл, попавший в наблюдение уже после подписи, считается изменённым —
    # под ним человек не подписывался, и это безопасная сторона ошибки.
    changed = [k for k in now if k not in was or was[k] != now[k]]
    if changed:
        return V(FAIL,
                 f"подтверждение от {rec.get('at', '?')} устарело: изменилось "
                 + ", ".join(sorted(changed)),
                 f"подтвердить заново: setup_state.py confirm {probe.id}")
    note = rec.get("note") or ""
    return V(OK, f"подтверждено {rec.get('at', '?')}" + (f": {note}" if note else ""))


# --------------------------------------------------------------------------
# Прогон
# --------------------------------------------------------------------------
class Options:
    def __init__(self, full=False, fast=False, only_stage=None):
        self.full, self.fast, self.only_stage = full, fast, only_stage


def run_probe(probe: Probe, ctx: Ctx) -> V:
    """Ни один отказ не роняет прогон: картина с одной дырой полезнее её отсутствия."""
    try:
        return probe.run(ctx)
    except Exception as e:  # noqa: BLE001 — сюда падает всё, что не предусмотрели
        return V(FAIL, f"проба упала: {type(e).__name__}: {e}",
                 "это дефект пробы, а не проекта — сообщи в базу")


def evaluate(ctx: Ctx, state: State, opts: Options) -> dict:
    """Вердикты по всем пробам. Дорогие откладываются до момента, когда нужны."""
    verdicts: dict[str, V] = {}
    deferred: list[Probe] = []

    for probe in PROBES:
        if opts.only_stage and opts.only_stage not in (probe.stage, blocking_stage(probe)):
            continue
        if probe.needs:
            declared = state.traits.get(probe.needs)
            if declared is None:
                verdicts[probe.id] = V(UNKNOWN, f"признак «{probe.needs}» не объявлен",
                                       f"setup_state.py trait {probe.needs}=true|false")
                continue
            if not declared:
                verdicts[probe.id] = V(SKIP, f"признак «{probe.needs}» выключен")
                continue
        if probe.applies is not None and not probe.applies(ctx):
            verdicts[probe.id] = V(SKIP, "предмета проверки нет")
            continue
        if probe.kind == HUMAN:
            verdicts[probe.id] = check_confirmation(probe, ctx, state)
            continue
        if probe.cost == EXPENSIVE and not (opts.full or opts.only_stage):
            if opts.fast:
                verdicts[probe.id] = V(NOTRUN, "пропущена по --fast")
            else:
                deferred.append(probe)
                verdicts[probe.id] = V(NOTRUN, "не проверялась")
            continue
        verdicts[probe.id] = run_probe(probe, ctx)

    # Дорогие пробы прогоняются только для этапа, до которого дошли: пока
    # предыдущий не закрыт, полный прогон проверки всё равно ничего не решает.
    for stage in STAGE_ORDER:
        if stage_closed(stage, verdicts, opts):
            continue
        for probe in deferred:
            if probe.stage == stage:
                verdicts[probe.id] = run_probe(probe, ctx)
        break
    return verdicts


def blocking_stage(p: Probe) -> str:
    """Этап, который проба держит. Обычно свой; у отложенных — тот, на котором
    её вообще можно подтвердить."""
    return p.confirm_at or p.stage


def stage_probes(stage: str, verdicts: dict) -> list[Probe]:
    return [p for p in PROBES if blocking_stage(p) == stage and p.id in verdicts]


def stage_closed(stage: str, verdicts: dict, opts: Options) -> bool:
    blocking = set(BLOCKING) if opts.fast else set(BLOCKING) | {NOTRUN}
    probes = stage_probes(stage, verdicts)
    if not probes:
        return True
    return not any(verdicts[p.id].verdict in blocking for p in probes)


def next_stage(verdicts: dict, opts: Options) -> str | None:
    for stage in STAGE_ORDER:
        if not stage_closed(stage, verdicts, opts):
            return stage
    return None


def open_stages(verdicts: dict, opts: Options) -> list[str]:
    return [s for s in STAGE_ORDER if not stage_closed(s, verdicts, opts)]


def frontier(verdicts: dict, opts: Options) -> str | None:
    """Где работа идёт на самом деле: следующий после последнего закрытого.

    Отличается от next_stage, когда ранний этап остался незакрытым, а работа
    ушла вперёд. Тогда «продолжить с Э0» на проекте, доведённом до Э5, —
    формально правда, а по существу ложь: человек читает это как «всё
    потеряно». Обкатка поймала ровно этот случай."""
    closed = [i for i, s in enumerate(STAGE_ORDER) if stage_closed(s, verdicts, opts)]
    if not closed:
        return STAGE_ORDER[0]
    nxt = max(closed) + 1
    return STAGE_ORDER[nxt] if nxt < len(STAGE_ORDER) else None


def orphans(state: State) -> list[str]:
    return sorted(k for k in state.confirmed if k not in BY_ID)


def undeclared(state: State, verdicts: dict) -> list[str]:
    need = {p.needs for p in PROBES if p.needs and p.id in verdicts}
    return sorted(t for t in need if state.traits.get(t) is None)


# --------------------------------------------------------------------------
# Вывод
# --------------------------------------------------------------------------
def render_human(ctx: Ctx, state: State, verdicts: dict, opts: Options) -> str:
    out = []
    nxt = next_stage(verdicts, opts)
    for stage, title in STAGES:
        probes = stage_probes(stage, verdicts)
        if not probes:
            continue
        results = [verdicts[p.id].verdict for p in probes]
        counted = [r for r in results if r != SKIP]
        good = sum(1 for r in counted if r == OK)
        if any(r == FAIL for r in results):
            mark, tail = MARK[FAIL], f"{good}/{len(counted)}"
        elif any(r == UNKNOWN for r in results):
            mark, tail = MARK[UNKNOWN], f"{good}/{len(counted)}"
        elif any(r == NOTRUN for r in results) and not opts.fast:
            mark, tail = MARK[NOTRUN], "не проверялся (дорогая проба)"
        else:
            mark, tail = MARK[OK], f"{good}/{len(counted)}"
        out.append(f"{stage:<4}{title:<36}{mark}  {tail}")
        for p in probes:
            v = verdicts[p.id]
            if v.verdict in (OK, SKIP):
                continue
            sign = "⏳" if (v.verdict == FAIL and p.kind == HUMAN) else MARK[v.verdict]
            origin = f" (обещано на {p.stage})" if blocking_stage(p) != p.stage else ""
            out.append(f"      {sign} {p.id:<20} {v.detail}{origin}")
            if v.fix:
                out.append(f"          → {v.fix}")
    out.append("")
    if opts.only_stage:
        closed = stage_closed(opts.only_stage, verdicts, opts)
        out.append(f"Этап {opts.only_stage} "
                   + ("закрыт." if closed else "не закрыт.")
                   + " Проверялся только он — про остальные этот прогон не говорит.")
        return "\n".join(out)
    if nxt is None:
        out.append("Все этапы закрыты. Настройка закончена.")
    else:
        probes = stage_probes(nxt, verdicts)
        failed = sum(1 for p in probes if verdicts[p.id].verdict == FAIL and p.kind == MACHINE)
        waiting = sum(1 for p in probes if verdicts[p.id].verdict == FAIL and p.kind == HUMAN)
        unk = sum(1 for p in probes if verdicts[p.id].verdict == UNKNOWN)
        bits = []
        if failed:
            bits.append(f"не пройдено: {failed}")
        if waiting:
            bits.append(f"ждут подтверждения: {waiting}")
        if unk:
            bits.append(f"без ответа: {unk}")
        out.append(f"Продолжить с {nxt} «{STAGE_TITLE[nxt]}»" + (": " + ", ".join(bits) if bits else ""))
        front = frontier(verdicts, opts)
        if front != nxt:
            where = ("все последующие этапы закрыты" if front is None
                     else f"работа дошла до {front}")
            behind = [s for s in open_stages(verdicts, opts)
                      if front is None or STAGE_ORDER.index(s) < STAGE_ORDER.index(front)]
            out.append(f"    Это незакрытый этап позади, а не потеря: {where}. "
                       f"Осталось закрыть: {', '.join(behind)}.")
    und = undeclared(state, verdicts)
    if und:
        out.append("Не объявлены признаки: " + ", ".join(f"{t} ({TRAITS[t]})" for t in und))
    orph = orphans(state)
    if orph:
        out.append("Осиротевшие подтверждения: " + ", ".join(orph)
                   + " — снять командой unconfirm")
    return "\n".join(out)


def render_json(ctx: Ctx, state: State, verdicts: dict, opts: Options) -> str:
    stages = []
    for stage, title in STAGES:
        probes = stage_probes(stage, verdicts)
        if not probes:
            continue
        stages.append({
            "id": stage, "title": title,
            "closed": stage_closed(stage, verdicts, opts),
            "probes": [{"id": p.id, "kind": p.kind, "verdict": verdicts[p.id].verdict,
                        "detail": verdicts[p.id].detail, "fix": verdicts[p.id].fix,
                        "declared_at": p.stage}
                       for p in probes],
        })
    return json.dumps({
        "next_stage": next_stage(verdicts, opts),
        # Первый незакрытый и «где идёт работа» — разные вещи, и агент,
        # ведущий по конвейеру, должен различать их, а не гнать человека
        # в начало из-за одного неподтверждённого гейта на Э0.
        "frontier": frontier(verdicts, opts),
        "open_stages": open_stages(verdicts, opts),
        "stages": stages,
        "traits": state.traits,
        "undeclared_traits": undeclared(state, verdicts),
        "orphan_confirmations": orphans(state),
    }, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# Сверка базы с самой собой
# --------------------------------------------------------------------------
def repo_root() -> Path | None:
    """Корень репозитория базы, если скрипт запущен из него, а не из плагина."""
    for parent in HERE.parents:
        if (parent / "docs" / "gates.md").exists() and (parent / "plugins").is_dir():
            return parent
    return None


def cmd_check_spec() -> int:
    root = repo_root()
    if root is None:
        print("--check-spec доступен только в репозитории базы: нужен docs/gates.md")
        return 2
    text = (root / "docs" / "gates.md").read_text(encoding="utf-8")
    spec = set(re.findall(r"^\| `([a-z0-9.\-]+)` \|", text.split("## Сводка")[0], re.M))
    code = {p.id for p in PROBES}
    only_spec, only_code = sorted(spec - code), sorted(code - spec)
    for i in only_spec:
        print(f"в gates.md есть, в коде нет: {i}")
    for i in only_code:
        print(f"в коде есть, в gates.md нет: {i}")
    if only_spec or only_code:
        return 1
    print(f"пробы совпадают с docs/gates.md: {len(code)}")
    return 0


def question_targets() -> dict[str, list[str]]:
    """Цели из «Заполняет:» банка вопросов: нормализованная цель → вопросы."""
    out: dict[str, list[str]] = {}
    qdir = HERE.parent / "questions"
    for f in sorted(qdir.glob("[0-9]*.md")) if qdir.is_dir() else []:
        qid = None
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^### (В[\d.]+)", line)
            if m:
                qid = m.group(1)
            m = re.match(r"^\*\*Заполняет:\*\* (.+)$", line)
            if m and qid:
                for part in m.group(1).split(";"):
                    out.setdefault(norm_target(part), []).append(qid)
    return out


def norm_target(s: str) -> str:
    s = s.replace("→", " ").replace("|", " ")
    return norm(s)


def template_sections() -> list[tuple[str, str]]:
    """Разделы заготовок каркаса: (документ, заголовок). Пусто вне репозитория базы."""
    root = repo_root()
    out = []
    if root is None:
        return out
    for doc in sorted((root / "template" / "docs").rglob("*.md")):
        rel = doc.relative_to(root / "template").as_posix()
        if Path(rel).name in ("INDEX.md", "TAGS.md") or "decisions" in rel:
            continue
        lines = doc.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            m = re.match(r"^##\s+(.+?)\s*$", line)
            if not m:
                continue
            # Раздел может честно объявить, что вопроса под него нет: он
            # копится по ходу работы, дублирует другой документ или лежит за
            # пределами конвейера. Причина обязательна — иначе это способ
            # спрятать дыру.
            if any("no-question:" in l for l in lines[i + 1:i + 4]):
                continue
            out.append((rel, m.group(1)))
    return out


def covered(target: str, targets: dict) -> bool:
    return any(target == t or target in t or t in target for t in targets)


def cmd_check_questions() -> int:
    qdir = HERE.parent / "questions"
    if not qdir.is_dir():
        print("нет каталога questions/ рядом со скриптом")
        return 2
    targets = question_targets()
    probe_fills = {norm_target(f"{d} {s or ''}"): p.id
                   for p in PROBES if p.fills for d, s in [p.fills]}

    holes = []
    for p in PROBES:
        if p.kind != MACHINE or not p.fills:
            continue
        doc, sec = p.fills
        if not covered(norm_target(f"{doc} {sec or ''}"), targets):
            holes.append((p.id, doc, sec))
    for pid, doc, sec in holes:
        print(f"проба без вопроса: {pid} → {doc}" + (f" → «{sec}»" if sec else ""))

    # Третья сверка, из первой обкатки: раздел заготовки, который не закрыт
    # ни вопросом, ни пробой. «Порядок работы» в конституции был именно таким
    # — человек упирался в пустой раздел, и спросить про него было некому.
    orphans = []
    for rel, head in template_sections():
        t = norm_target(f"{rel} {head}")
        if not covered(t, targets) and not covered(t, probe_fills):
            orphans.append((rel, head))
    for rel, head in orphans:
        print(f"раздел без вопроса и без пробы: {rel} → «{head}»")

    print(f"вопросов: {sum(len(v) for v in targets.values())}, "
          f"машинных проб с целью: {sum(1 for p in PROBES if p.kind == MACHINE and p.fills)}, "
          f"проб без вопроса: {len(holes)}, разделов без спроса: {len(orphans)}")
    return 1 if (holes or orphans) else 0


# --------------------------------------------------------------------------
# Команды записи
# --------------------------------------------------------------------------
def today() -> str:
    import datetime
    return datetime.date.today().isoformat()


def cmd_confirm(ctx: Ctx, state: State, probe_id: str, note: str) -> int:
    probe = BY_ID.get(probe_id)
    if probe is None:
        print(f"нет такой пробы: {probe_id}")
        return 2
    if probe.kind == MACHINE:
        print(f"{probe_id} — машинная проба, её нельзя закрыть словом. "
              f"Она пересчитывается при каждом запуске.")
        return 2
    state.confirmed[probe_id] = {"at": today(), "note": note,
                                 "fingerprint": fingerprint(ctx, probe.watch)}
    state.save(ctx)
    print(f"подтверждено: {probe_id} ({probe.title})")
    if probe.watch:
        print("протухнет при изменении: " + ", ".join(probe.watch))
    return 0


def cmd_unconfirm(ctx: Ctx, state: State, probe_id: str) -> int:
    if probe_id not in state.confirmed:
        print(f"подтверждения {probe_id} и так нет")
        return 0
    del state.confirmed[probe_id]
    state.save(ctx)
    print(f"снято: {probe_id}")
    return 0


def cmd_trait(ctx: Ctx, state: State, expr: str) -> int:
    if "=" not in expr:
        print("формат: trait <имя>=<true|false>")
        return 2
    name, _, raw = expr.partition("=")
    name, raw = name.strip(), raw.strip().lower()
    if name not in TRAITS:
        print(f"неизвестный признак: {name}. Известны: " + ", ".join(TRAITS))
        return 2
    if raw not in ("true", "false", "да", "нет", "1", "0"):
        print("значение: true либо false")
        return 2
    state.traits[name] = raw in ("true", "да", "1")
    state.save(ctx)
    # Пояснение сформулировано утвердительно, поэтому при false его надо
    # отрицать: «remote = False (есть удалённый репозиторий)» читается как
    # утверждение, которому противоречит само значение.
    verdict = "да" if state.traits[name] else "нет"
    print(f"{name} = {verdict}: {TRAITS[name]}"
          if state.traits[name] else f"{name} = нет: НЕ {TRAITS[name]}")
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Где остановилась настройка проекта.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=["confirm", "unconfirm", "trait"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--note", default="")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--stage", help="только один этап, дорогие пробы включены")
    ap.add_argument("--full", action="store_true", help="прогнать всё, включая дорогое")
    ap.add_argument("--fast", action="store_true", help="пропустить дорогое")
    ap.add_argument("--check-spec", action="store_true")
    ap.add_argument("--check-questions", action="store_true")
    a = ap.parse_args(argv)

    if a.check_spec:
        return cmd_check_spec()
    if a.check_questions:
        return cmd_check_questions()

    root = find_root(Path.cwd())
    if root is None:
        # До Э0 корня ещё нет: ни .git, ни .claude/. Это не ошибка, а самое
        # начало — то состояние, ради которого база и сделана («ставится на
        # любой проект без подготовки»). Единственная точка входа конвейера
        # обязана отвечать и здесь: раньше она падала с exit 2 и прозой в
        # stdout, хотя просили --json, и первый шаг скила был невыполним на
        # честно новом проекте. Найдено вторым кругом обкатки.
        #
        # Корнем берём текущий каталог, а не результат подъёма вверх: подъём
        # доезжал до дома и объявлял корнем его (см. find_root). Дом корнем не
        # становится и здесь — там конфиг Claude Code, а не проект.
        cwd = Path.cwd()
        try:
            at_home = cwd.resolve() == Path.home().resolve()
        except (OSError, RuntimeError):
            at_home = False
        if at_home:
            print("домашний каталог проектом не считается: "
                  "перейди в каталог проекта и запусти настройку там")
            return 2
        root = cwd
    ctx = Ctx(root)
    try:
        state = State.load(ctx)
    except StateError as e:
        print(e)
        return 2

    if a.command == "confirm":
        return cmd_confirm(ctx, state, a.arg or "", a.note)
    if a.command == "unconfirm":
        return cmd_unconfirm(ctx, state, a.arg or "")
    if a.command == "trait":
        return cmd_trait(ctx, state, a.arg or "")

    if a.stage and a.stage not in STAGE_TITLE:
        print(f"нет такого этапа: {a.stage}. Известны: " + ", ".join(STAGE_ORDER))
        return 2
    opts = Options(full=a.full, fast=a.fast, only_stage=a.stage)
    verdicts = evaluate(ctx, state, opts)
    print(render_json(ctx, state, verdicts, opts) if a.as_json
          else render_human(ctx, state, verdicts, opts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
