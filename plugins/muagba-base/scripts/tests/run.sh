#!/usr/bin/env bash
# Прогон проверок хуков. Вызывается из CI и руками.
# Без него файлы случаев — декорация: лежат, но ничего не ловят.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$(dirname "$HERE")"
FAILED=0

# Хуки пишут журнал в проект сессии, а без CLAUDE_PROJECT_DIR им становится
# текущий каталог — корень базы, где .claude/logs/ заведён. Прогон писал бы в
# настоящий журнал. По умолчанию — пустая песочница без .claude/logs/.
SANDBOX=$(mktemp -d)
export CLAUDE_PROJECT_DIR="$SANDBOX"

fail() { printf 'СБОЙ  %s\n      %s\n' "$1" "$2"; FAILED=1; }

detail() {  # <корень> <id пробы> → detail пробы
  (cd "$1" && python3 "$SCRIPTS/setup_state.py" --json 2>/dev/null) | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(next((p.get('detail','') for s in d['stages'] for p in s['probes'] if p['id']=='$2'), 'НЕТ'))"
}

verdict() {  # <корень> <id пробы> → verdict пробы
  (cd "$1" && python3 "$SCRIPTS/setup_state.py" --json 2>/dev/null) | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(next((p['verdict'] for s in d['stages'] for p in s['probes'] if p['id']=='$2'), 'НЕТ'))"
}

# --- guard-bash: разбор rm ---------------------------------------------------
# rm_danger.py печатает опасную цель и выходит с 1; молчит и 0 — команда чиста.
while IFS=$'\t' read -r verdict command; do
  [ -z "${verdict:-}" ] && continue
  out=$(printf '%s' "$command" | python3 "$SCRIPTS/rm_danger.py"); code=$?
  case "$verdict" in
    BLOCK) [ "$code" -eq 1 ] || fail "rm: ждали блокировку" "$command" ;;
    OK)    [ "$code" -eq 0 ] || fail "rm: ложное срабатывание на '$out'" "$command" ;;
    *)     fail "rm: неизвестный вердикт '$verdict'" "$command" ;;
  esac
done < "$HERE/rm_cases.tsv"

# --- write_targets: во что пишет команда -------------------------------------
# «-» в первой колонке значит «целей быть не должно».
while IFS=$'\t' read -r want command; do
  [ -z "${want:-}" ] && continue
  got=$(printf '%s' "$command" | python3 "$SCRIPTS/write_targets.py" | tr '\n' ' ')
  if [ "$want" = "-" ]; then
    [ -z "${got// /}" ] || fail "write_targets: ждали пусто, получили '$got'" "$command"
  else
    case " $got " in *" $want "*) ;; *) fail "write_targets: нет '$want' в '$got'" "$command" ;; esac
  fi
done < "$HERE/write_cases.tsv"

# --- cmd_danger: разрушительные команды по argv, а не по упоминанию ---------
while IFS=$'\t' read -r want command; do
  [ -z "${want:-}" ] && continue
  printf '{"tool_input":{"command":%s},"cwd":"."}' \
    "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$command")" \
    | bash "$SCRIPTS/guard-bash.sh" >/dev/null 2>&1
  code=$?
  got=OK; [ "$code" -eq 2 ] && got=BLOCK
  [ "$got" = "$want" ] || fail "cmd_danger: ждали $want, вышло $got" "$command"
done < "$HERE/cmd_cases.tsv"

# --- protect-paths: защищённые и записываемые один раз пути ------------------
PROJ=$(mktemp -d)
trap 'rm -rf "$PROJ"' EXIT
mkdir -p "$PROJ/.claude"
# Список берём из шаблона: проверяем ровно то, что получит новый проект.
cp "$SCRIPTS/../../../template/.claude/protected-paths.txt" "$PROJ/.claude/"

while IFS=$'\t' read -r verdict state rel; do
  [ -z "${verdict:-}" ] && continue
  target="$PROJ/$rel"
  mkdir -p "$(dirname "$target")"
  rm -f "$target"
  [ "$state" = "exists" ] && : > "$target"
  printf '{"tool_input":{"file_path":"%s"},"cwd":"%s"}' "$target" "$PROJ" \
    | CLAUDE_PROJECT_DIR="$PROJ" bash "$SCRIPTS/protect-paths.sh" >/dev/null 2>&1
  code=$?
  case "$verdict" in
    BLOCK) [ "$code" -eq 2 ] || fail "protect: ждали запрет, код $code" "$state $rel" ;;
    ALLOW) [ "$code" -eq 0 ] || fail "protect: ждали проход, код $code" "$state $rel" ;;
    *)     fail "protect: неизвестный вердикт '$verdict'" "$rel" ;;
  esac
done < "$HERE/protect_cases.tsv"

# --- protect-paths: файл в соседнем проекте ---------------------------------
# Сессия в одном каталоге, файл в другом. Раскладка не надуманная: скил
# настройки умеет принимать путь к проекту, а оркестратор держит несколько
# репозиториев из одной сессии. Раньше применялись правила проекта сессии.
SESS=$(mktemp -d); TGT=$(mktemp -d)
mkdir -p "$SESS/.claude" "$TGT/.claude" "$TGT/docs"
cp "$SCRIPTS/../../../template/.claude/protected-paths.txt" "$TGT/.claude/" 2>/dev/null
: > "$TGT/.env"; : > "$TGT/.env.example"; : > "$TGT/uv.lock"; : > "$TGT/docs/readme.md"
cross() {
  printf '{"tool_input":{"file_path":"%s"},"cwd":"%s"}' "$1" "$SESS" \
    | CLAUDE_PROJECT_DIR="$SESS" bash "$SCRIPTS/protect-paths.sh" >/dev/null 2>&1
  local code=$?
  [ "$code" -eq "$2" ] || fail "protect-paths через каталоги: код $code, ждали $2" "$1"
}
cross "$TGT/.env"          2
cross "$TGT/.env.example"  0
cross "$TGT/uv.lock"       2
cross "$TGT/docs/readme.md" 0
rm -rf "$SESS" "$TGT"

# --- setup_state: прогон по чистому каркасу ---------------------------------
# Ловит пробу, которая падает с исключением. Для этого и нужен свежий каркас:
# в нём почти всё красное, то есть задействованы все ветки разбора.
TEMPLATE="$SCRIPTS/../../../template"
if [ -d "$TEMPLATE" ]; then
  FRESH=$(mktemp -d)
  cp -r "$TEMPLATE/." "$FRESH/"
  git -C "$FRESH" init -q
  OUT=$(cd "$FRESH" && python3 "$SCRIPTS/setup_state.py" --fast 2>&1); CODE=$?
  rm -rf "$FRESH"
  [ "$CODE" -eq 0 ] || fail "setup_state: код $CODE на чистом каркасе" "$OUT"
  printf '%s' "$OUT" | grep -q 'проба упала' \
    && fail "setup_state: проба упала с исключением" \
            "$(printf '%s' "$OUT" | grep 'проба упала')"
  printf '%s' "$OUT" | grep -q 'Продолжить с Э0' \
    || fail "setup_state: чистый каркас должен начинаться с Э0" "$(printf '%s' "$OUT" | tail -3)"
fi

# --- copy_template: каркас в непустой проект не затирает ---------------------
# Э0 когда-то копировал обычным cp -a, поверх, и стирал написанный человеком
# CLAUDE.md молча, без вопроса и без копии — в свежем git init восстановить
# его было неоткуда.
if [ -d "$TEMPLATE" ]; then
  DEST=$(mktemp -d)
  mkdir -p "$DEST/.claude/logs"
  printf '# Мой свод правил\n' > "$DEST/CLAUDE.md"
  printf 'node_modules/\n' > "$DEST/.gitignore"
  printf '{}\n' > "$DEST/.claude/logs/agents.jsonl"

  OUT=$(cd "$DEST" && python3 "$SCRIPTS/copy_template.py" --dry-run 2>&1); CODE=$?
  [ "$CODE" -eq 0 ] || fail "copy_template --dry-run: код $CODE" "$OUT"
  [ "$(find "$DEST" -type f | wc -l)" -eq 3 ] \
    || fail "copy_template --dry-run скопировал файлы" "$OUT"
  printf '%s' "$OUT" | grep -q '^  CLAUDE.md$' \
    || fail "copy_template: совпадение по CLAUDE.md не названо" "$OUT"

  OUT=$(cd "$DEST" && python3 "$SCRIPTS/copy_template.py" 2>&1)
  grep -q 'Мой свод правил' "$DEST/CLAUDE.md" \
    || fail "copy_template затёр CLAUDE.md проекта" "$OUT"
  grep -q 'node_modules' "$DEST/.gitignore" \
    || fail "copy_template затёр .gitignore проекта" "$OUT"
  [ -s "$DEST/.claude/logs/agents.jsonl" ] \
    || fail "copy_template затёр журнал агентов" "$OUT"
  [ -f "$DEST/.claude/settings.json" ] \
    || fail "copy_template не слил каталог .claude/" "$OUT"

  # Разбор совпадения освобождает имя: каркасный файл обязан встать вторым
  # проходом, сам он туда не попадёт.
  mv "$DEST/CLAUDE.md" "$DEST/AGENTS.md"
  OUT=$(cd "$DEST" && python3 "$SCRIPTS/copy_template.py" 2>&1)
  grep -q '@AGENTS.md' "$DEST/CLAUDE.md" 2>/dev/null \
    || fail "copy_template: второй проход не занял освободившееся имя" "$OUT"
  rm -rf "$DEST"
fi

# --- check_specs: форма артефактов фичи --------------------------------------
# Форму, которую ничего не проверяет, не держит даже её автор: проект, заведший
# такую проверку, нашёл ею 23 расхождения в собственных спеках.
SP=$(mktemp -d)
mkdir -p "$SP/docs"
printf '### I. Раз\nт\n### II. Два\nт\n' > "$SP/docs/constitution.md"
OUT=$(cd "$SP" && python3 "$SCRIPTS/check_specs.py" 2>&1); CODE=$?
[ "$CODE" -eq 0 ] || fail "check_specs: проект без specs/ не находка, код $CODE" "$OUT"

mkdir -p "$SP/specs/001-x"
printf -- '- **status:** active\n\n- R1. КОГДА а СИСТЕМА ДОЛЖНА б\n  Проверка: тест\n' > "$SP/specs/001-x/spec.md"
printf -- '## Сверка с конституцией\n\n| Принцип | Как |\n|---|---|\n| I | ок |\n' > "$SP/specs/001-x/plan.md"
printf -- '- [ ] T001 сделать → результат\n' > "$SP/specs/001-x/tasks.md"
OUT=$(cd "$SP" && python3 "$SCRIPTS/check_specs.py" 2>&1); CODE=$?
[ "$CODE" -eq 1 ] || fail "check_specs: сломанная спека должна давать код 1, дала $CODE" "$OUT"
for want in 'нет принципа II' 'не ссылается на требование' 'нет строки «Файлы:»' 'требования без задачи'; do
  printf '%s' "$OUT" | grep -q "$want" || fail "check_specs: не поймано «$want»" "$OUT"
done

# Принципы читаются из конституции проекта, а не из константы: убрали принцип —
# сверять по нему перестали.
printf '### I. Раз\nт\n' > "$SP/docs/constitution.md"
OUT=$(cd "$SP" && python3 "$SCRIPTS/check_specs.py" 2>&1)
printf '%s' "$OUT" | grep -q 'нет принципа II' \
  && fail "check_specs: список принципов зашит, а не читается из конституции" "$OUT"

printf -- '- [ ] T001 сделать → результат [R1]\n  Файлы: a.py\n' > "$SP/specs/001-x/tasks.md"
OUT=$(cd "$SP" && python3 "$SCRIPTS/check_specs.py" 2>&1); CODE=$?
[ "$CODE" -eq 0 ] || fail "check_specs: правильная спека должна проходить" "$OUT"

# Находки проекта narta на форме базы. Требования — только в своём разделе:
# `- R1.` в нумерации решений иначе становилась требованием без проверки.
spec() { printf -- '- **status:** %s\n\n## Требования\n\n- R1. КОГДА а СИСТЕМА ДОЛЖНА б\n  Проверка: тест\n\n%s\n' "$1" "$2" \
  > "$SP/specs/001-x/spec.md"; (cd "$SP" && python3 "$SCRIPTS/check_specs.py" 2>&1); }
OUT=$(spec active '## Решения по умолчанию

- R2. взяли uuid
  Почему: так проще')
printf '%s' "$OUT" | grep -q 'R2' && fail "check_specs: R в решениях принята за требование" "$OUT"
# Открытые вопросы при active — находка; «нет» — пусто.
OUT=$(spec active '## Открытые вопросы

- Кто владелец схемы?')
printf '%s' "$OUT" | grep -q '«Открытые вопросы» не пуст' \
  || fail "check_specs: active при открытых вопросах пропущен" "$OUT"
OUT=$(spec active '## Открытые вопросы

нет')
printf '%s' "$OUT" | grep -q 'Открытые вопросы' && fail "check_specs: «нет» принято за вопрос" "$OUT"
OUT=$(spec draft '## Открытые вопросы

- Кто владелец схемы?')
printf '%s' "$OUT" | grep -q 'Открытые вопросы' && fail "check_specs: draft с вопросами — не находка" "$OUT"
# Решение, которое человек должен увидеть, не даёт поставить active.
OUT=$(spec active '## Решения по умолчанию

- Д1. роли БД — app и migrator
  Почему: стандартно
  Альтернатива: одна роль
  Спросить: да')
printf '%s' "$OUT" | grep -q '«Спросить: да»' \
  || fail "check_specs: active при «Спросить: да» пропущен" "$OUT"
# «Проверка:» отдельным пунктом — не проверка требования.
printf -- '- **status:** draft\n\n## Требования\n\n- R1. КОГДА а СИСТЕМА ДОЛЖНА б\n- Проверка: тест\n' > "$SP/specs/001-x/spec.md"
OUT=$(cd "$SP" && python3 "$SCRIPTS/check_specs.py" 2>&1)
printf '%s' "$OUT" | grep -q 'у R1 нет «Проверка:»' \
  || fail "check_specs: «Проверка:» отдельным пунктом засчитана" "$OUT"
rm -rf "$SP"

# --- setup_state: честно пустая папка ---------------------------------------
# Состояние «до Э0»: ни .git, ни .claude/. Это первая команда конвейера на
# самом обычном новом проекте, и она обязана отвечать JSON'ом, а не падать.
EMPTY=$(mktemp -d)
OUT=$(cd "$EMPTY" && python3 "$SCRIPTS/setup_state.py" --json 2>&1); CODE=$?
rm -rf "$EMPTY"
[ "$CODE" -eq 0 ] || fail "setup_state: код $CODE на пустой папке" "$OUT"
printf '%s' "$OUT" | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("next_stage")=="Э0" else 1)' 2>/dev/null \
  || fail "setup_state: на пустой папке ждали JSON с next_stage Э0" "$(printf '%s' "$OUT" | head -3)"

# Дом проектом не считается: подъём вверх когда-то объявлял корнем его и писал
# в глобальный ~/.claude/setup.json.
OUT=$(cd "$HOME" && python3 "$SCRIPTS/setup_state.py" --json 2>&1); CODE=$?
[ "$CODE" -eq 2 ] || fail "setup_state: в домашнем каталоге ждали отказ, код $CODE" "$OUT"

# --- check.ci: PR-триггер запускает сборку с любой ветки ---------------------
# Каркас несёт ci.yml с `push: branches: [main]` и голым `pull_request:`.
# Проба смотрела только push.branches и краснела на каждой ветке фичи — то
# есть ругалась на файл, который база сама и кладёт.
CB=$(mktemp -d); mkdir -p "$CB/.github/workflows" "$CB/.claude"
cp "$HERE/../../../../template/.github/workflows/ci.yml" "$CB/.github/workflows/ci.yml" 2>/dev/null \
  || printf 'on:\n  push:\n    branches: [main]\n  pull_request:\n\njobs:\n  c:\n    steps:\n      - run: ./.claude/check.sh\n' > "$CB/.github/workflows/ci.yml"
printf 'echo ok\n' > "$CB/.claude/check.sh"
( cd "$CB" && git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm x \
  && git checkout -qb feat/008-something )
[ "$(verdict "$CB" check.ci)" = "ok" ] \
  || fail "check.ci: PR-триггер без ограничения по веткам не признан" "$(detail "$CB" check.ci)"

# `pull_request: branches:` — это базы PR, а не ветки работы. Фича-ветка,
# уходящая PR-ом в существующую базу, CI проходит. Прежде этот случай
# считался красным — тест закреплял ошибку пробы. Нашёл проект narta:
# `pull_request: branches: [develop, main]`, работа в setup/e7-confirm.
ci_yml() {  # <тело on:> → ci.yml
  printf 'on:\n%s\njobs:\n  c:\n    steps:\n      - run: ./.claude/check.sh\n' "$1" \
    > "$CB/.github/workflows/ci.yml"
}
( cd "$CB" && git branch -q -f develop )
ci_yml '  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]'
detail "$CB" check.ci | grep -q 'PR из feat/008-something в develop' \
  || fail "check.ci: PR в существующую базу не признан" "$(detail "$CB" check.ci)"
# Список веток столбиком — та же семантика.
ci_yml '  pull_request:
    branches:
      - develop'
detail "$CB" check.ci | grep -q 'PR из feat/008-something в develop' \
  || fail "check.ci: база PR списком не прочитана" "$(detail "$CB" check.ci)"
# Базы нет ни одной — тот самый master при ci на main: краснеть по делу.
ci_yml '  push:
    branches: [trunk]
  pull_request:
    branches: [trunk]'
detail "$CB" check.ci | grep -q 'а работа идёт в feat/008-something' \
  || fail "check.ci: несуществующая база принята" "$(detail "$CB" check.ci)"
# Работа прямо в базе, а push на неё не настроен: PR в себя не бывает.
( cd "$CB" && git checkout -q develop )
ci_yml '  pull_request:
    branches: [develop]'
detail "$CB" check.ci | grep -q 'а работа идёт в develop' \
  || fail "check.ci: работа в единственной базе без push принята" "$(detail "$CB" check.ci)"
# push по шаблону.
( cd "$CB" && git checkout -qb release/1.2 )
ci_yml '  push:
    branches: ["release/**"]'
detail "$CB" check.ci | grep -q 'push в release/1.2' \
  || fail "check.ci: шаблон release/** не сработал" "$(detail "$CB" check.ci)"
rm -rf "$CB"

# --- observe.log: пробы гоняют и в рабочем дереве ----------------------------
# .claude/logs/ в игноре и в дерево не копируется, поэтому журнала там нет
# никогда. Журнал ведётся в проекте сессии, дерево — её временный checkout.
WT=$(mktemp -d); mkdir -p "$WT/main/.claude/logs"
( cd "$WT/main" && git init -q && printf 'x\n' > a.txt && git add -A \
  && git -c user.email=t@t -c user.name=t commit -qm x \
  && git worktree add -q ../tree -b wt 2>/dev/null )
printf '{"event": "SubagentStart", "agent_type": "x"}\n' > "$WT/main/.claude/logs/agents.jsonl"
if [ -d "$WT/tree" ]; then
  [ "$(verdict "$WT/tree" observe.log)" = "ok" ] \
    || fail "observe.log: в рабочем дереве не найден журнал основного checkout" \
            "$(detail "$WT/tree" observe.log)"
fi
rm -rf "$WT"

# --- product.audit не протухает от пополнения словаря ------------------------
# Словарь пополняют агенты на каждой фиче. Держать его в watch значит
# переспрашивать «это мой текст» восемь раз за восемь фич.
PA=$(mktemp -d); mkdir -p "$PA/docs/product"
for f in mission roadmap glossary; do printf 'Текст %s.\n' "$f" > "$PA/docs/product/$f.md"; done
( cd "$PA" && python3 "$SCRIPTS/setup_state.py" confirm product.audit --note t >/dev/null 2>&1 )
[ "$(verdict "$PA" product.audit)" = "ok" ] \
  || fail "product.audit: подтверждение не записалось" "$(detail "$PA" product.audit)"
printf 'Текст glossary.\nНовый термин.\n' > "$PA/docs/product/glossary.md"
[ "$(verdict "$PA" product.audit)" = "ok" ] \
  || fail "product.audit: протухло от правки словаря" "$(detail "$PA" product.audit)"
printf 'Переписанный замысел.\n' > "$PA/docs/product/mission.md"
[ "$(verdict "$PA" product.audit)" = "ok" ] \
  && fail "product.audit: правка замысла обязана ронять подтверждение" "$(detail "$PA" product.audit)"

# Подпись, сделанная ДО сужения списка, несёт лишний файл. Сверка по
# объединению старого и нового списков числила снятый файл изменённым
# навсегда: сужение не действовало, пока не переподпишут.
printf 'Текст mission.\n' > "$PA/docs/product/mission.md"
( cd "$PA" && python3 "$SCRIPTS/setup_state.py" confirm product.audit --note t >/dev/null 2>&1 )
python3 - "$PA" <<'EOPY'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1]) / ".claude" / "setup.json"
d = json.loads(p.read_text(encoding="utf-8"))
d["confirmed"]["product.audit"]["fingerprint"]["docs/product/glossary.md"] = "deadbeef"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
EOPY
[ "$(verdict "$PA" product.audit)" = "ok" ] \
  || fail "product.audit: файл, снятый из наблюдения, числится изменённым" "$(detail "$PA" product.audit)"

# А файл, попавший в наблюдение после подписи, обязан ронять: под ним
# человек не подписывался.
python3 - "$PA" <<'EOPY'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1]) / ".claude" / "setup.json"
d = json.loads(p.read_text(encoding="utf-8"))
d["confirmed"]["product.audit"]["fingerprint"].pop("docs/product/roadmap.md", None)
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
EOPY
[ "$(verdict "$PA" product.audit)" = "ok" ] \
  && fail "product.audit: неподписанный файл в наблюдении принят за подтверждённый" "$(detail "$PA" product.audit)"
rm -rf "$PA"

# --- check.ci-ran: гейт не требует невозможного -------------------------------
# Рабочий процесс, который ни разу не запускался, — обещание, а не арбитр. Но
# локальный bare-репозиторий процессов не запускает, и требовать от него
# зелёный прогон значило бы повторить ошибку, которую чинили у защиты ветки.
CI=$(mktemp -d); mkdir -p "$CI/.github/workflows" "$CI/.claude"
printf 'on: push\njobs:\n  t:\n    steps:\n      - run: ./.claude/check.sh\n' > "$CI/.github/workflows/ci.yml"
printf 'echo ok\n' > "$CI/.claude/check.sh"
( cd "$CI" && git init -q && git remote add origin /tmp/whatever.git )
( cd "$CI" && python3 "$SCRIPTS/setup_state.py" trait remote=true >/dev/null 2>&1 )
[ "$(verdict "$CI" check.ci-ran)" = "skip" ] \
  || fail "check.ci-ran: локальный remote процессов не запускает, проба обязана пропускаться" \
          "$(detail "$CI" check.ci-ran)"

( cd "$CI" && git remote set-url origin https://github.com/x/y.git )
[ "$(verdict "$CI" check.ci-ran)" = "skip" ] \
  && fail "check.ci-ran: на хостинге с процессами проба обязана спрашивать" \
          "$(detail "$CI" check.ci-ran)"
rm -rf "$CI"

# --- guard-bash: запись по вычисленному пути ---------------------------------
# Статический разбор вычисленный путь не видит. Дыру нашли на себе: правка
# защищённого docs/workflow.md через heredoc, где путь собирался как
# Path(name)/"docs"/"workflow.md", прошла мимо хука.
GB=$(mktemp -d); mkdir -p "$GB/.claude"
printf '.env\n!.env.example\n.git/\ndocs/workflow.md\n+docs/sources/\n' > "$GB/.claude/protected-paths.txt"
guard() {  # <код python> → OK|BLOCK
  printf '{"tool_input":{"command":%s},"cwd":"%s"}' \
    "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1")" "$GB" \
    | bash "$SCRIPTS/guard-bash.sh" >/dev/null 2>&1
  [ $? -eq 2 ] && echo BLOCK || echo OK
}
[ "$(guard 'python3 - <<PY
import pathlib
for n in ("a","b"):
    (pathlib.Path(n)/"docs"/"workflow.md").write_text("x")
PY')" = "BLOCK" ] || fail "guard-bash: вычисленный путь к защищённому файлу пропущен" ""

[ "$(guard 'python3 -c "import pathlib; pathlib.Path(\"report.md\").write_text(\"x\")"')" = "OK" ] \
  || fail "guard-bash: безобидная запись заблокирована" ""

# Запись в литеральную цель плюс упоминание защищённого пути в данных — не
# запись в защищённый путь. Строковый s.replace(a, b) принимался за
# Path.replace и объявлял цель вычисленной. Нашёл narta на Э11: скрипт
# правки спеки с «grep … .env» в тексте блокировался как запись в .env.
[ "$(guard "python3 - <<'EOF'
s = open('spec.md').read()
s = s.replace('старое', 'Проверка: grep ^PORT .env')
open('spec.md','w').write(s)
EOF")" = "OK" ] || fail "guard-bash: литеральная запись с .env в данных заблокирована" ""
# А цель-переменная и replace с одним аргументом — по-прежнему вычисленная.
[ "$(guard "python3 - <<'EOF'
p = '.e' + 'nv'  # .env
open(p,'w').write('x')
EOF")" = "BLOCK" ] || fail "guard-bash: open(переменная) с упоминанием .env пропущен" ""
[ "$(guard "python3 - <<'EOF'
import pathlib
pathlib.Path('tmp').replace(target)  # target = .env
EOF")" = "BLOCK" ] || fail "guard-bash: Path.replace(цель) с упоминанием .env пропущен" ""
# Литеральная цель переименования — сама цель: раньше её ловил маркер на всё.
[ "$(guard "python3 -c \"from pathlib import Path; Path('x').replace('.env')\"")" = "BLOCK" ] \
  || fail "guard-bash: Path.replace('.env') пропущен" ""

# Составные конструкции оболочки. Разбор резал только по ; && || |, и
# команда внутри if/цикла/группы начиналась с then, do, { — `cp` в ней не
# узнавался. Защищённый .env так записали на Э5 проекта narta.
while IFS= read -r c; do
  [ "$(guard "$c")" = "BLOCK" ] || fail "guard-bash: запись в .env внутри конструкции пропущена" "$c"
done <<'CASES'
if [ ! -f .env ]; then cp .env.example .env; fi
while false; do cp a .env; done
for f in a; do cp $f .env; done
{ cp .env.example .env; }
( cp .env.example .env )
echo $(cp .env.example .env)
case x in x) cp .env.example .env;; esac
CASES
# Перевод строки — разделитель. Прежде вторая строка считалась аргументами
# первой: `echo hi` и `cp … .env` проходили как один безобидный echo.
[ "$(guard 'echo hi
cp .env.example .env')" = "BLOCK" ] || fail "guard-bash: вторая строка команды не разобрана" ""
# `<<` внутри кавычек — не heredoc: иначе следующие строки проглатывались бы
# как его тело вместе с командами.
[ "$(guard 'echo "<<X"
cp .env.example .env
X')" = "BLOCK" ] || fail "guard-bash: heredoc из кавычек проглотил команду" ""
# А тело настоящего heredoc — данные: слова в нём командами не считаются.
[ "$(guard 'cat <<EOF > notes.md
then cp .env.example .env
EOF')" = "OK" ] || fail "guard-bash: текст heredoc принят за команду" ""

# Чтение защищённого файла без записи блокировать не за что.
[ "$(guard 'python3 -c "import pathlib; print(pathlib.Path(\"docs/workflow.md\").read_text())"')" = "OK" ] \
  || fail "guard-bash: чтение защищённого файла принято за запись" ""

# Исключение должно переживать проверку по упоминанию: .env.example не .env.
[ "$(guard 'python3 - <<PY
import pathlib
p = pathlib.Path(".env.example")
p.write_text("KEY=")
PY')" = "OK" ] || fail "guard-bash: .env.example заблокирован шаблоном .env" ""

# Шаблон обязан стоять на границе пути, а не просто входить подстрокой.
# `.env` попадало внутрь `os.environ`, и любой heredoc, читающий переменные
# окружения, отвергался: исполнители теряли по два прогона, пока не
# догадывались перейти на Edit. Нашёл сосед, доводивший проект на базе.
[ "$(guard 'python3 - <<PY
import os, pathlib
pathlib.Path("notes.md").write_text(os.environ["API_KEY"])
PY')" = "OK" ] || fail "guard-bash: os.environ принят за защищённый .env" ""

# Обратная сторона: граница не должна открыть то, что было закрыто. У
# шаблона, кончающегося слэшем, проверка справа не применяется — иначе
# '.git/' перестал бы ловить '.git/config'.
[ "$(guard 'echo x > .git/config')" = "BLOCK" ] \
  || fail "guard-bash: запись в .git/config прошла" ""
[ "$(guard 'python3 -c "import os; os.environ.clear()"')" = "OK" ] \
  || fail "guard-bash: команда без записи заблокирована" ""
rm -rf "$GB"

# --- rm_targets: что команда удаляет ----------------------------------------
rmt() { printf '%s' "$1" | python3 "$SCRIPTS/rm_targets.py" | tr '\n' ' '; }
[ "$(rmt 'rm -rf build dist')" = "build dist " ] \
  || fail "rm_targets: операнды rm разобраны неверно" "$(rmt 'rm -rf build dist')"
[ -z "$(rmt 'echo rm -rf /etc')" ] \
  || fail "rm_targets: упоминание rm принято за удаление" ""
[ "$(rmt 'cd sub && rm data.db')" = "sub/data.db " ] \
  || fail "rm_targets: cd в той же команде не учтён" "$(rmt 'cd sub && rm data.db')"
[ "$(rmt 'rm -- -weird-name')" = "-weird-name " ] \
  || fail "rm_targets: операнд после -- принят за ключ" "$(rmt 'rm -- -weird-name')"

# --- guard-bash: удаление ----------------------------------------------------
# Защита путей смотрела только на запись, и `rm docs/constitution.md` проходил
# насквозь: запрет на правку стоял, а на снос — нет. Отдельно — удаление
# того, чего нет в гите и что не пересобирается: вернуть неоткуда, поэтому
# хук не запрещает, а спрашивает человека. Живой случай: агент одной цепочкой
# `проверил && rm -f` снёс базу с данными заказчика, успев напечатать,
# сколько в ней записей.
RMP=$(mktemp -d)
( cd "$RMP" && git init -q . )
mkdir -p "$RMP/.claude" "$RMP/docs" "$RMP/node_modules/pkg"
cp "$SCRIPTS/../../../template/.claude/protected-paths.txt" "$RMP/.claude/"
printf 'docs/workflow.md\n' >> "$RMP/.claude/protected-paths.txt"
printf 'study.db\nnode_modules/\n*.log\n' > "$RMP/.gitignore"
: > "$RMP/docs/workflow.md"; : > "$RMP/.env"; : > "$RMP/.env.example"
: > "$RMP/docs/tracked.md"; : > "$RMP/node_modules/pkg/index.js"; : > "$RMP/run.log"
echo data > "$RMP/study.db"
( cd "$RMP" && git add -A >/dev/null 2>&1 \
  && git -c user.email=t@t -c user.name=t commit -qm init >/dev/null 2>&1 )

gbv() {  # <команда> → OK|BLOCK|ASK
  local out code
  out=$(printf '{"tool_input":{"command":%s},"cwd":"%s"}' \
    "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1")" "$RMP" \
    | bash "$SCRIPTS/guard-bash.sh" 2>/dev/null); code=$?
  if [ "$code" -eq 2 ]; then echo BLOCK
  elif printf '%s' "$out" | grep -q '"permissionDecision": *"ask"'; then echo ASK
  else echo OK; fi
}
while IFS=$'\t' read -r want command; do
  [ -z "${want:-}" ] && continue
  got=$(gbv "$command")
  [ "$got" = "$want" ] || fail "guard-bash удаление: ждали $want, вышло $got" "$command"
done <<'CASES'
BLOCK	rm docs/workflow.md
BLOCK	rm -f .env
OK	rm .env.example
OK	rm docs/tracked.md
ASK	rm -f study.db
OK	rm -rf node_modules
OK	rm -f run.log
OK	rm -f нет-такого-файла.db
BLOCK	rm -f study.db && git reset --hard
CASES

# Вопрос уходит в Claude Code структурой, а не текстом: сломанный JSON
# хук превращает в no-op, и защита остаётся только на бумаге.
printf '{"tool_input":{"command":"rm -f study.db"},"cwd":"%s"}' "$RMP" \
  | bash "$SCRIPTS/guard-bash.sh" 2>/dev/null \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)["hookSpecificOutput"]
assert d["hookEventName"] == "PreToolUse", d
assert d["permissionDecision"] == "ask", d
assert d["permissionDecisionReason"].strip(), d
' || fail "guard-bash: вопрос о невосстановимом удалении отдан не по схеме хука" ""
rm -rf "$RMP"

# --- cycle.specs: конвейер фич объявлен полями, а не именем ------------------
# База конвейер фич не несёт. Проба читает пять полей и обязана краснеть, пока
# хоть одно не объявлено: имя конвейера гейту ничего не говорит, а прежняя
# версия этой пробы запускала наш скрипт по нашей форме и отвергала
# безупречную чужую работу по написанию.

CS=$(mktemp -d)
mkdir -p "$CS/specs" "$CS/.claude"
printf 'Артефакты фич.\n' > "$CS/specs/README.md"
[ "$(verdict "$CS" cycle.specs)" = "fail" ] \
  || fail "cycle.specs: без полей должна краснеть" "$(cat "$CS/specs/README.md")"

# Четыре из пяти — всё ещё красная: недообъявленный конвейер не проверяем.
{ printf -- '- **Артефакты:** specs/<NNN>/spec.md\n'
  printf -- '- **Готова к коду:** status active\n'
  printf -- '- **Задача → требование:** ссылка [R1]\n'
  printf -- '- **Готовность ставит:** человек\n'; } >> "$CS/specs/README.md"
[ "$(verdict "$CS" cycle.specs)" = "fail" ] \
  || fail "cycle.specs: без «Проверка формы» должна краснеть" "$(cat "$CS/specs/README.md")"

# Проза вместо команды — не ответ: договорённость без исполнимой проверки не
# гейт. Три прогона обкатки завели три формы и ни одной проверки.
CS_FIVE=$(cat "$CS/specs/README.md")
printf '%s\n- **Проверка формы:** держится ревью\n' "$CS_FIVE" > "$CS/specs/README.md"
[ "$(verdict "$CS" cycle.specs)" = "fail" ] \
  || fail "cycle.specs: «держится ревью» принято за проверку" "$(cat "$CS/specs/README.md")"
detail "$CS" cycle.specs | grep -q 'не называет команду' \
  || fail "cycle.specs: проза отвергнута не по той причине" "$(detail "$CS" cycle.specs)"

# И самоссылка не годится: «вызывается из check.sh» без скрипта находила бы
# себя в тексте самого check.sh.
printf '# контракт check.sh\npytest\n' > "$CS/.claude/check.sh"
printf '%s\n- **Проверка формы:** вызывается из check.sh\n' "$CS_FIVE" > "$CS/specs/README.md"
[ "$(verdict "$CS" cycle.specs)" = "fail" ] \
  || fail "cycle.specs: самоссылка на check.sh принята за проверку" "$(cat "$CS/.claude/check.sh")"
detail "$CS" cycle.specs | grep -q 'не называет команду' \
  || fail "cycle.specs: самоссылка отвергнута не по той причине" "$(detail "$CS" cycle.specs)"

# Команда названа, но нигде не вызывается — проверка, которую никто не
# запускает, ничего не ловит.
printf '%s\n- **Проверка формы:** `python3 tools/spec_lint.py`\n' "$CS_FIVE" > "$CS/specs/README.md"
[ "$(verdict "$CS" cycle.specs)" = "fail" ] \
  || fail "cycle.specs: невызываемая проверка принята" "$(cat "$CS/.claude/check.sh")"

printf 'python3 tools/spec_lint.py\npytest\n' > "$CS/.claude/check.sh"
[ "$(verdict "$CS" cycle.specs)" = "ok" ] \
  || fail "cycle.specs: вызываемая проверка должна закрывать пробу" "$(cat "$CS/.claude/check.sh")"

# check.sh часто делегирует: требовать имя скрипта именно в нём значит
# краснеть на проекте, который всё сделал правильно через make.
printf 'make check\n' > "$CS/.claude/check.sh"
printf 'check-specs:\n\tpython3 tools/spec_lint.py\n' > "$CS/Makefile"
printf '%s\n- **Проверка формы:** `make check-specs`\n' "$CS_FIVE" > "$CS/specs/README.md"
[ "$(verdict "$CS" cycle.specs)" = "ok" ] \
  || fail "cycle.specs: цель make не признана проверкой" "$(cat "$CS/Makefile")"

# Чужая форма закрывает пробу так же: проверяется свойство, не наш файл.
{ printf 'Конвейер фич\n\n'
  printf -- '- **Артефакты:** specs/<NNN>-<slug>/spec.md, Spec Kit\n'
  printf -- '- **Готова к коду:** пройден checklists/requirements.md\n'
  printf -- '- **Задача → требование:** [US1] и FR-NNN\n'
  printf -- '- **Готовность ставит:** человек после /speckit-clarify\n'
  printf -- '- **Проверка формы:** `make check-specs`\n'; } > "$CS/specs/README.md"
[ "$(verdict "$CS" cycle.specs)" = "ok" ] \
  || fail "cycle.specs: чужой конвейер отвергнут — проба меряет инструмент" "$(cat "$CS/specs/README.md")"
rm -rf "$CS"

# --- roles: кто делает и кто проверяет объявляет проект ----------------------
# Раньше обе пробы разрешали имена через каталог агентов самого плагина и были
# зелены всегда: описывали базу, а не проект.
RL=$(mktemp -d); mkdir -p "$RL/docs" "$RL/.claude/agents"
printf '# Цикл\n' > "$RL/docs/workflow.md"
[ "$(verdict "$RL" roles.defined)" = "fail" ] \
  || fail "roles.defined: без раздела «Кто делает» должна краснеть" "$(cat "$RL/docs/workflow.md")"

# Имя без маркера — не ответ: неизвестно, агент это, команда или человек.
printf '## Кто делает\n\n- **Исполнитель:** implementer\n- **Проверяющий:** reviewer\n' \
  >> "$RL/docs/workflow.md"
[ "$(verdict "$RL" roles.defined)" = "fail" ] \
  || fail "roles.defined: имя без маркера принято" "$(cat "$RL/docs/workflow.md")"

# Назван агент, которого нет, — конвейер бы молча не позвал никого.
printf '# Цикл\n\n## Кто делает\n\n- **Исполнитель:** codewriter ← агент\n- **Проверяющий:** reviewer ← агент\n' \
  > "$RL/docs/workflow.md"
[ "$(verdict "$RL" roles.defined)" = "fail" ] \
  || fail "roles.defined: несуществующий агент принят" "$(detail "$RL" roles.defined)"
detail "$RL" roles.defined | grep -q 'такой роли нет' \
  || fail "roles.defined: несуществующий агент отвергнут не по той причине" "$(detail "$RL" roles.defined)"

# Один и тот же и пишет, и проверяет — та самая ошибка, ради которой роли разведены.
printf '# Цикл\n\n## Кто делает\n\n- **Исполнитель:** reviewer ← агент\n- **Проверяющий:** reviewer ← агент\n' \
  > "$RL/docs/workflow.md"
detail "$RL" roles.defined | grep -q 'одно и то же' \
  || fail "roles.defined: исполнитель и проверяющий совпали, проба молчит" "$(detail "$RL" roles.defined)"

# Роли базы: обе пробы закрываются.
printf '# Цикл\n\n## Кто делает\n\n- **Исполнитель:** implementer ← агент\n- **Проверяющий:** reviewer ← агент\n' \
  > "$RL/docs/workflow.md"
[ "$(verdict "$RL" roles.defined)" = "ok" ] && [ "$(verdict "$RL" roles.split)" = "ok" ] \
  || fail "roles: роли базы должны закрывать обе пробы" "$(detail "$RL" roles.split)"

# Проект переопределил проверяющего и дал ему правку — вот это и надо ловить.
printf -- '---\nname: reviewer\ntools: Read, Grep, Edit\n---\nтело\n' > "$RL/.claude/agents/reviewer.md"
detail "$RL" roles.split | grep -q 'умеет править' \
  || fail "roles.split: проверяющий с правкой пропущен" "$(detail "$RL" roles.split)"
rm -f "$RL/.claude/agents/reviewer.md"

# Проверяет человек — честный режим, машине сказать нечего.
printf '# Цикл\n\n## Кто делает\n\n- **Исполнитель:** implementer ← агент\n- **Проверяющий:** тимлид ← человек\n' \
  > "$RL/docs/workflow.md"
[ "$(verdict "$RL" roles.split)" = "ok" ] \
  || fail "roles.split: человеческое ревью объявлено провалом" "$(detail "$RL" roles.split)"
detail "$RL" roles.split | grep -q 'машинной гарантии нет' \
  || fail "roles.split: честный режим закрыт молча, без оговорки" "$(detail "$RL" roles.split)"
rm -rf "$RL"

# --- конституция ищется, а не задаётся адресом -------------------------------
# Spec Kit держит её в .specify/memory/. Проба на наш путь красит проект,
# который всё сделал правильно, просто другим инструментом.
CP=$(mktemp -d)
mkdir -p "$CP/.specify/memory"
printf '# Конституция\n\n## Core Principles\n\n### I. Раз\nТело. Исполнение: машинно\n' \
  > "$CP/.specify/memory/constitution.md"
[ "$(verdict "$CP" const.exists)" = "ok" ] \
  || fail "const.exists: конституция в .specify/memory не найдена" "$(cd "$CP" && python3 "$SCRIPTS/setup_state.py" --json | head -c 400)"
rm -rf "$CP"

# --- gate-check: гейт хода, остановка ради вопроса, исполнитель -------------
GT=$(mktemp -d); mkdir -p "$GT/.claude"
printf '#!/usr/bin/env bash\necho КРАСНО\nexit 1\n' > "$GT/.claude/check.sh"; chmod +x "$GT/.claude/check.sh"
gate() {  # <событие> <agent_type> <последнее сообщение> → "код|stdout"
  local out code
  out=$(python3 -c 'import json,sys;print(json.dumps({"hook_event_name":sys.argv[1],"agent_type":sys.argv[2],"last_assistant_message":sys.argv[3],"cwd":sys.argv[4]}))' \
    "$1" "$2" "$3" "$GT" | bash "$SCRIPTS/gate-check.sh" 2>/dev/null); code=$?
  printf '%s|%s' "$code" "$out"
}
[ "$(gate Stop '' 'Готово, всё сделал.')" = "2|" ] \
  || fail "gate-check: доклад при красной проверке отпущен" "$(gate Stop '' 'Готово, всё сделал.')"
# Остановка ради вопроса отпускается, но человек видит красноту — проверяем
# именно предупреждение, а не только код: код 0 дал бы и сломанный запуск.
gate Stop '' 'Сделал схему. Какой тип взять для id — **uuid или bigint?**' \
  | grep -q '^0|.*systemMessage.*check.sh красный' \
  || fail "gate-check: вопрос при красной проверке не отпущен с предупреждением" \
          "$(gate Stop '' 'Какой тип взять?')"
# Вопрос в середине, а в конце доклад — это доклад.
[ "$(gate Stop '' 'Взять uuid? Взял uuid. Готово.' | cut -d'|' -f1)" = "2" ] \
  || fail "gate-check: вопрос не в конце принят за остановку ради вопроса" ""
# Исполнитель держится гейтом и на SubagentStop; остальные роли — нет.
[ "$(gate SubagentStop muagba-base:implementer 'Готово.' | cut -d'|' -f1)" = "2" ] \
  || fail "gate-check: исполнитель ушёл с красной проверкой" ""
[ "$(gate SubagentStop implementer 'Готово.' | cut -d'|' -f1)" = "2" ] \
  || fail "gate-check: проектный implementer не держится гейтом" ""
[ "$(gate SubagentStop muagba-base:reviewer 'Нельзя сливать.' | cut -d'|' -f1)" = "0" ] \
  || fail "gate-check: проверяющего держит гейт кода" ""
# Служебные вызовы Claude Code приходят с пустым agent_type — у narta это 151
# из 190 SubagentStop. Гонять на них check.sh значит платить проверкой за
# каждый вызов классификатора.
[ "$(gate SubagentStop '' 'x' | cut -d'|' -f1)" = "0" ] \
  || fail "gate-check: служебный вызов с пустым agent_type держит гейт" ""
printf '#!/usr/bin/env bash\nexit 0\n' > "$GT/.claude/check.sh"
[ "$(gate Stop '' 'Готово.')" = "0|" ] || fail "gate-check: зелёная проверка держит ход" ""
rm -rf "$GT"

# --- gate-check: уже проверенное зелёным не проверяется заново -------------
# У narta за этап 1.4 гейт гонял check.sh 131 раз (651 мин), 130 зелёных, и в
# сотне ходов код перед этим не менялся. Счётчик прогонов — вне дерева.
GC=$(mktemp -d); GO=$(mktemp -d); mkdir -p "$GC/.claude/logs"; git -C "$GC" init -q
cat > "$GC/.claude/check.sh" <<SH
#!/usr/bin/env bash
echo run >> "$GO/count"
[ -f bad.txt ] && exit 1
# «Форматтер»: чинит файл и выходит зелёным.
grep -q unformatted f.txt 2>/dev/null && echo formatted > f.txt
exit 0
SH
chmod +x "$GC/.claude/check.sh"; echo a > "$GC/f.txt"
git -C "$GC" add -A; git -C "$GC" -c user.name=t -c user.email=t@t commit -qm init
gc() {  # [env] → код гейта Stop в дереве GC
  printf '{"hook_event_name":"Stop","last_assistant_message":"Готово.","cwd":"%s","session_id":"s"}' "$GC" \
    | env CLAUDE_PROJECT_DIR="$GC" "$@" bash "$SCRIPTS/gate-check.sh" >/dev/null 2>&1; echo $?
}
runs() { wc -l < "$GO/count" | tr -d ' '; }
gc >/dev/null; [ "$(runs)" = 1 ] || fail "gate-check: первый ход не проверен" "$(runs)"
gc >/dev/null; [ "$(runs)" = 1 ] || fail "gate-check: неизменное дерево проверено заново" "$(runs)"
grep -q '"decision": "cached"' "$GC/.claude/logs/agents.jsonl" \
  || fail "gate-check: пропуск по отпечатку не записан в журнал" "$(cat "$GC/.claude/logs/agents.jsonl")"
# Журнал в .claude/logs/ не в .gitignore этого проекта — и всё равно не
# меняет отпечаток; а сам отпечаток в рабочее дерево не ложится.
[ -z "$(git -C "$GC" status --porcelain -- . ':(exclude).claude/logs')" ] \
  || fail "gate-check: отпечаток лёг в рабочее дерево" "$(git -C "$GC" status --porcelain)"
echo b > "$GC/f.txt"; gc >/dev/null
[ "$(runs)" = 2 ] || fail "gate-check: правка отслеживаемого файла не проверена" "$(runs)"
echo n > "$GC/new.txt"; gc >/dev/null
[ "$(runs)" = 3 ] || fail "gate-check: новый файл не проверен" "$(runs)"
echo n2 > "$GC/new.txt"; gc >/dev/null
[ "$(runs)" = 4 ] || fail "gate-check: правка неотслеживаемого файла не проверена" "$(runs)"
gc MUAGBA_GATE_ALWAYS=1 >/dev/null
[ "$(runs)" = 5 ] || fail "gate-check: MUAGBA_GATE_ALWAYS не заставил проверить" "$(runs)"
# Красный стирает запомненное: вернулись к проверенному зелёным дереву —
# проверяется заново, а не отпускается по старому отпечатку.
touch "$GC/bad.txt"; [ "$(gc)" = 2 ] || fail "gate-check: красный отпущен" ""
rm "$GC/bad.txt"; gc >/dev/null
[ "$(runs)" = 7 ] || fail "gate-check: после красного дерево не проверено заново" "$(runs)"
# Предел, названный в описании: изменение вне git отпечаток не видит.
touch "$GO/outside"; gc >/dev/null
[ "$(runs)" = 7 ] || fail "gate-check: изменение вне дерева вдруг заметно — описание врёт" "$(runs)"
# Проверка, сама поправившая дерево, исходное состояние зелёным не отмечает:
# она прошла на том, что починила. Агент откатил починку — проверять заново.
echo unformatted > "$GC/f.txt"; gc >/dev/null
[ "$(cat "$GC/f.txt")" = formatted ] || fail "gate-check: тестовый форматтер не сработал" ""
echo unformatted > "$GC/f.txt"; gc >/dev/null
[ "$(runs)" = 9 ] || fail "gate-check: состояние до починки проверкой принято за проверенное" "$(runs)"
# Проверка знает, кто её вызвал, и отпечаток у каждого события свой:
# быстрое зелёное хода координатора не засчитывается сдаче исполнителя.
rm -f "$GC/f.txt.bak"; cat > "$GC/.claude/check.sh" <<SH
#!/usr/bin/env bash
echo run >> "$GO/count"
echo "\${MUAGBA_GATE_EVENT:-нет}" >> "$GO/events"
exit 0
SH
git -C "$GC" add -A; git -C "$GC" -c user.name=t -c user.email=t@t commit -qm c2
gc >/dev/null; gc >/dev/null
[ "$(tail -1 "$GO/events")" = Stop ] || fail "gate-check: проверка не знает, что её вызвал ход" "$(cat "$GO/events")"
[ "$(wc -l < "$GO/events" | tr -d ' ')" = 1 ] || fail "gate-check: ход координатора на том же дереве проверен дважды" "$(cat "$GO/events")"
printf '{"hook_event_name":"SubagentStop","agent_type":"implementer","last_assistant_message":"Готово.","cwd":"%s","session_id":"s"}' "$GC" \
  | CLAUDE_PROJECT_DIR="$GC" bash "$SCRIPTS/gate-check.sh" >/dev/null 2>&1
[ "$(tail -1 "$GO/events")" = SubagentStop ] \
  || fail "gate-check: сдача исполнителя засчитана по зелёному ходу координатора" "$(cat "$GO/events")"
rm -rf "$GC" "$GO"

# --- gate-check: проверка, не уложившаяся во время ------------------------
# Хук, оборванный Claude Code по тайм-ауту, агента молча отпускает: у narta
# check.sh шёл 13–17 мин при тайм-ауте 600 с, и гейт исполнителя не работал.
# Гейт отсекает сам, раньше хука, и говорит об этом человеку.
GS=$(mktemp -d); GSO=$(mktemp -d); mkdir -p "$GS/.claude/logs"
printf '#!/usr/bin/env bash\nsleep 3\ntouch "%s/finished"\nexit 1\n' "$GSO" > "$GS/.claude/check.sh"; chmod +x "$GS/.claude/check.sh"
OUT=$(printf '{"hook_event_name":"Stop","last_assistant_message":"Готово.","cwd":"%s","session_id":"s"}' "$GS" \
  | CLAUDE_PROJECT_DIR="$GS" MUAGBA_GATE_TIMEOUT=1 bash "$SCRIPTS/gate-check.sh" 2>/dev/null); CODE=$?
[ "$CODE" = 0 ] || fail "gate-check: проверка сверх времени держит ход" "код $CODE"
printf '%s' "$OUT" | grep -q 'systemMessage.*не уложился в 1 с' \
  || fail "gate-check: превышение времени прошло молча" "$OUT"
grep -q '"decision": "timeout"' "$GS/.claude/logs/agents.jsonl" \
  || fail "gate-check: превышение времени не записано в журнал" "$(cat "$GS/.claude/logs/agents.jsonl")"
sleep 4
[ -e "$GSO/finished" ] && fail "gate-check: проверка сверх времени не убита — работает дальше" ""
python3 - "$SCRIPTS/../hooks/hooks.json" <<'PY' || fail "hooks.json: тайм-аут хука гейта не больше отсечки гейта (1500 с)" ""
import json, sys
d = json.load(open(sys.argv[1]))
ts = [h["timeout"] for gs in d["hooks"].values() for g in gs for h in g["hooks"] if "gate-check" in h["command"]]
assert ts and all(t > 1500 for t in ts), ts
PY
rm -rf "$GS" "$GSO"

# --- журнал: ходы, красный гейт, запреты хуков ------------------------------
# Пишется только в проект, который завёл .claude/logs/; текста команды в нём
# нет — только класс и шаблон пути.
LG=$(mktemp -d); mkdir -p "$LG/.claude"; git -C "$LG" init -q
printf '.env\n' > "$LG/.claude/protected-paths.txt"
printf '#!/usr/bin/env bash\necho "==> lint"\necho "==> tests"\necho "E   assert 1 == 2"\nexit 1\n' > "$LG/.claude/check.sh"
chmod +x "$LG/.claude/check.sh"
hook() {  # <скрипт> <json> — хук в проекте LG
  printf '%s' "$2" | CLAUDE_PROJECT_DIR="$LG" bash "$SCRIPTS/$1" >/dev/null 2>&1
}
hook gate-check.sh "{\"hook_event_name\":\"Stop\",\"session_id\":\"s\",\"last_assistant_message\":\"Готово.\",\"cwd\":\"$LG\"}"
[ ! -e "$LG/.claude/logs" ] || fail "журнал: хук завёл .claude/logs/ в неподготовленном проекте" ""
mkdir -p "$LG/.claude/logs"
hook gate-check.sh "{\"hook_event_name\":\"Stop\",\"session_id\":\"s\",\"last_assistant_message\":\"Готово.\",\"cwd\":\"$LG\"}"
hook gate-check.sh "{\"hook_event_name\":\"Stop\",\"session_id\":\"s\",\"last_assistant_message\":\"Взять uuid?\",\"cwd\":\"$LG\"}"
hook guard-bash.sh "{\"tool_input\":{\"command\":\"echo SECRETTEXT > .env\"},\"cwd\":\"$LG\"}"
hook protect-paths.sh "{\"tool_input\":{\"file_path\":\"$LG/.env\"},\"cwd\":\"$LG\"}"
J="$LG/.claude/logs/agents.jsonl"
jl() { python3 -c 'import json,sys
rows=[json.loads(l) for l in open(sys.argv[1])]
want=dict(kv.split("=",1) for kv in sys.argv[2:])
sys.exit(0 if any(all(str(r.get(k))==v for k,v in want.items()) for r in rows) else 1)' "$J" "$@"; }
[ "$(grep -c '"event": "turn"' "$J" 2>/dev/null)" = "2" ] \
  || fail "журнал: закрытие хода записано не на каждом Stop" "$(cat "$J" 2>/dev/null)"
jl event=gate decision=block "failed_at===> tests" branch=master \
  || jl event=gate decision=block "failed_at===> tests" branch=main \
  || fail "журнал: красный гейт без места падения или ветки" "$(cat "$J")"
jl event=gate decision=released_on_question \
  || fail "журнал: отпуск на вопросе не записан" "$(cat "$J")"
jl event=guard hook=guard-bash decision=deny class=write-protected target=.env \
  || fail "журнал: запрет guard-bash не записан" "$(cat "$J")"
jl event=guard hook=protect-paths decision=deny class=write-protected target=.env \
  || fail "журнал: запрет protect-paths не записан" "$(cat "$J")"
grep -q SECRETTEXT "$J" && fail "журнал: в него попал текст команды" ""
# Ходы и запреты — ещё не «агенты работали»: observe.log ждёт запуска сабагента.
[ "$(verdict "$LG" observe.log)" = "fail" ] \
  || fail "observe.log: журнал без запусков агентов принят" "$(detail "$LG" observe.log)"
printf '{"event": "SubagentStop", "agent_type": "x"}\n' >> "$J"
[ "$(verdict "$LG" observe.log)" = "ok" ] \
  || fail "observe.log: запуск агента в журнале не найден" "$(detail "$LG" observe.log)"
rm -rf "$LG"

# --- check.split: быстрый гейт хода — полная проверка перед слиянием ---------
# ADR-0015: поделил гейт — CI на PR обязан гонять check.sh полностью.
CS=$(mktemp -d); mkdir -p "$CS/.claude" "$CS/.github/workflows"; git -C "$CS" init -q
printf '#!/usr/bin/env bash\nmake check\n' > "$CS/.claude/check.sh"
detail "$CS" check.split | grep -q 'полную проверку' \
  || fail "check.split: неподелённый гейт не принят" "$(detail "$CS" check.split)"
printf '#!/usr/bin/env bash\n# пример: MUAGBA_GATE_EVENT=Stop\nmake check\n' > "$CS/.claude/check.sh"
detail "$CS" check.split | grep -q 'полную проверку' \
  || fail "check.split: пример в комментарии принят за деление" "$(detail "$CS" check.split)"
printf '#!/usr/bin/env bash\n[ -n "${MUAGBA_GATE_EVENT:-}" ] && { make lint; exit 0; }\nmake check\n' > "$CS/.claude/check.sh"
detail "$CS" check.split | grep -q 'CI не вызывает' \
  || fail "check.split: быстрый гейт без CI принят" "$(detail "$CS" check.split)"
printf 'on:\n  push:\n    branches: [main]\njobs:\n  c:\n    steps:\n      - run: ./.claude/check.sh\n' > "$CS/.github/workflows/ci.yml"
detail "$CS" check.split | grep -q 'без триггера pull_request' \
  || fail "check.split: CI только на push принят за проверку перед слиянием" "$(detail "$CS" check.split)"
printf 'on:\n  pull_request:\njobs:\n  c:\n    steps:\n      - run: ./.claude/check.sh\n        env:\n          MUAGBA_GATE_EVENT: Stop\n' > "$CS/.github/workflows/ci.yml"
detail "$CS" check.split | grep -q 'задаёт MUAGBA_GATE_EVENT' \
  || fail "check.split: CI с быстрой частью принят" "$(detail "$CS" check.split)"
printf 'on:\n  push:\n    branches: [main]\n  pull_request:\njobs:\n  c:\n    steps:\n      - run: ./.claude/check.sh\n' > "$CS/.github/workflows/ci.yml"
[ "$(verdict "$CS" check.split)" = ok ] || fail "check.split: CI на PR не засчитан" "$(detail "$CS" check.split)"
rm -rf "$CS"

# Каркас check.sh: гейт гоняет быструю цель, если она есть; иначе — полную.
TC=$(mktemp -d); mkdir -p "$TC/.claude"
cp "$SCRIPTS/../../../template/.claude/check.sh" "$SCRIPTS/../../../template/.claude/check-frames.py" "$TC/.claude/"
printf 'check:\n\t@echo FULL\ncheck-quick:\n\t@echo QUICK\n' > "$TC/Makefile"
OUT=$(cd "$TC" && MUAGBA_GATE_EVENT=Stop bash .claude/check.sh 2>&1)
printf '%s' "$OUT" | grep -q QUICK && ! printf '%s' "$OUT" | grep -q FULL \
  || fail "каркас check.sh: гейт не пошёл по быстрой части" "$OUT"
OUT=$(cd "$TC" && bash .claude/check.sh 2>&1)
printf '%s' "$OUT" | grep -q FULL || fail "каркас check.sh: без события не полная проверка" "$OUT"
printf 'check:\n\t@echo FULL\n' > "$TC/Makefile"
OUT=$(cd "$TC" && MUAGBA_GATE_EVENT=Stop bash .claude/check.sh 2>&1)
printf '%s' "$OUT" | grep -q FULL || fail "каркас check.sh: без быстрой цели гейт ничего не проверил" "$OUT"
rm -rf "$TC"

# --- enforce.attribution: подпись агента — решение человека -----------------
# Умолчание Claude Code — подписываться. Проба ловит отсутствие решения, а не
# сам ответ: «подписывать» и «не подписывать» оба законны.
AT=$(mktemp -d); mkdir -p "$AT/.claude"; git -C "$AT" init -q
echo '{"permissions":{"deny":["Bash(x)"]}}' > "$AT/.claude/settings.json"
detail "$AT" enforce.attribution | grep -q 'не решено' \
  || fail "enforce.attribution: молчание принято за решение" "$(detail "$AT" enforce.attribution)"
echo '{"attribution":{"commit":"","pr":""}}' > "$AT/.claude/settings.json"
detail "$AT" enforce.attribution | grep -q 'не подписывается' \
  || fail "enforce.attribution: отказ от подписи не распознан" "$(detail "$AT" enforce.attribution)"
echo '{"attribution":{"commit":"Co-Authored-By: X <x@y>","pr":"by X"}}' > "$AT/.claude/settings.json"
detail "$AT" enforce.attribution | grep -q 'задана явно' \
  || fail "enforce.attribution: явная подпись не засчитана" "$(detail "$AT" enforce.attribution)"
# Половина решения — не решение: pr остался на умолчании.
echo '{"attribution":{"commit":""}}' > "$AT/.claude/settings.json"
# Проверяем причину, а не вердикт: упавшая с исключением проба тоже «fail».
detail "$AT" enforce.attribution | grep -q 'не решено' \
  || fail "enforce.attribution: решение только про коммиты засчитано целиком" "$(detail "$AT" enforce.attribution)"
# Личное решение живёт в settings.local.json — оно тоже решение.
echo '{}' > "$AT/.claude/settings.json"
echo '{"attribution":{"commit":"","pr":""}}' > "$AT/.claude/settings.local.json"
detail "$AT" enforce.attribution | grep -q 'settings.local.json' \
  || fail "enforce.attribution: личное решение не найдено" "$(detail "$AT" enforce.attribution)"
rm -rf "$AT"

# --- log-agent: сводка стенограммы сабагента на SubagentStop ---------------
# Модель, effort и токены запуска — в журнал: стенограммы живут 30 дней, а
# выбирать модель под класс задачи можно только по накопленным данным.
LA=$(mktemp -d); mkdir -p "$LA/p/.claude/logs"
cat > "$LA/t.jsonl" <<'JL'
{"type":"user","timestamp":"2026-09-30T10:00:00Z","message":{"role":"user","content":"задача"}}
{"type":"assistant","timestamp":"2026-09-30T10:00:05Z","requestId":"r1","effort":"medium","message":{"model":"claude-sonnet-5-5","usage":{"input_tokens":10,"cache_read_input_tokens":1000,"cache_creation_input_tokens":200,"output_tokens":50}}}
{"type":"assistant","timestamp":"2026-09-30T10:00:06Z","requestId":"r1","effort":"medium","message":{"model":"claude-sonnet-5-5","usage":{"input_tokens":10,"cache_read_input_tokens":1000,"cache_creation_input_tokens":200,"output_tokens":50}}}
{"type":"assistant","timestamp":"2026-09-30T10:07:00Z","requestId":"r2","effort":"medium","message":{"model":"claude-sonnet-5-5","usage":{"input_tokens":5,"cache_read_input_tokens":3000,"cache_creation_input_tokens":0,"output_tokens":70}}}
JL
la() {  # <событие> [лишние поля] → запуск хука
  printf '{"hook_event_name":"%s","agent_id":"a1","agent_type":"muagba-base:implementer","session_id":"s","cwd":"%s"%s}' \
    "$1" "$LA/p" "${2:-}" | CLAUDE_PROJECT_DIR="$LA/p" bash "$SCRIPTS/log-agent.sh"
}
la SubagentStop ",\"agent_transcript_path\":\"$LA/t.jsonl\""
python3 - "$LA/p/.claude/logs/agents.jsonl" <<'PY' || fail "log-agent: сводка стенограммы неверна" "$(cat "$LA/p/.claude/logs/agents.jsonl")"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
# r1 записан дважды — один запрос; токены не удвоены
assert (r["model"], r["effort"], r["requests"]) == ("claude-sonnet-5-5", "medium", 2), r
assert (r["tok_in"], r["tok_cache_read"], r["tok_cache_write"], r["tok_out"]) == (15, 4000, 200, 120), r
assert r["first_ts"] == "2026-09-30T10:00:00Z" and r["last_ts"] == "2026-09-30T10:07:00Z", r
PY
# Без стенограммы и на SubagentStart — запись о запуске всё равно есть, без сводки.
la SubagentStop ",\"agent_transcript_path\":\"$LA/нет.jsonl\""
la SubagentStart
python3 - "$LA/p/.claude/logs/agents.jsonl" <<'PY' || fail "log-agent: без стенограммы запись потеряна или со сводкой" "$(cat "$LA/p/.claude/logs/agents.jsonl")"
import json, sys
rs = [json.loads(l) for l in open(sys.argv[1])]
assert len(rs) == 3 and "model" not in rs[1] and "model" not in rs[2], rs
PY
rm -rf "$LA"

# --- pipeline_queues: очереди конвейера по стенограмме координатора --------
# Исполнитель готов → координатор поручил ревью → правки → слияние. Уведомление
# о готовности, пока координатор занят, лежит в очереди: «готово» — постановка.
PQ=$(mktemp -d)
python3 - "$PQ/s.jsonl" <<'PY'
import json, sys
L = []
def at(m): return f"2026-10-01T10:{m:02d}:00Z"
def use(m, uid, name, inp): L.append({"type": "assistant", "timestamp": at(m), "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}})
def res(m, uid, extra=None, content=""): L.append({"type": "user", "timestamp": at(m), "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": content}]}, **({"toolUseResult": extra} if extra else {})})
def note(aid): return f"<task-notification>\n<task-id>{aid}</task-id>\n<status>completed</status>\n</task-notification>"
use(0, "u1", "Agent", {"description": "T001 исполнитель", "prompt": "задача", "subagent_type": "muagba-base:implementer"})
res(0, "u1", {"agentId": "A1", "isAsync": True, "status": "async_launched"})
L.append({"type": "queue-operation", "operation": "enqueue", "timestamp": at(10), "content": note("A1")})
L.append({"type": "attachment", "timestamp": at(12), "attachment": {"type": "queued_command", "prompt": note("A1")}})
use(13, "q1", "AskUserQuestion", {"questions": []})
use(15, "u2", "Agent", {"description": "Ревью T001", "prompt": "проверь", "subagent_type": "muagba-base:reviewer"})
res(15, "u2", {"agentId": "A2", "isAsync": True, "status": "async_launched"})
L.append({"type": "user", "timestamp": at(20), "message": {"content": note("A2")}})
use(25, "s1", "SendMessage", {"to": "A1", "message": "поправь"})
L.append({"type": "queue-operation", "operation": "enqueue", "timestamp": at(30), "content": note("A1")})
use(31, "b1", "Bash", {"command": 'gh pr create --base develop --title "T001: схема"'})
res(31, "b1", content="https://github.com/o/r/pull/7")
use(40, "b2", "Bash", {"command": "gh pr merge 7 --merge"})
open(sys.argv[1], "w").write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in L))
PY
OUT=$(python3 "$SCRIPTS/pipeline_queues.py" --transcripts "$PQ" --csv "$PQ/out" 2>&1)
python3 - "$PQ/out" <<'PY' || fail "pipeline_queues: цепочка задачи посчитана неверно" "$OUT"
import csv, sys
w = [(r["role_or_after"], float(r["min"])) for r in csv.DictReader(open(sys.argv[1] + "/pipeline-work.csv"))]
q = [(r["role_or_after"], r["next"], float(r["min"])) for r in csv.DictReader(open(sys.argv[1] + "/pipeline-queue.csv"))]
assert w == [("muagba-base:implementer", 10.0), ("muagba-base:reviewer", 5.0), ("muagba-base:implementer", 5.0)], w
assert q == [("muagba-base:implementer", "muagba-base:reviewer", 5.0),
             ("muagba-base:reviewer", "правки: muagba-base:implementer", 5.0),
             ("muagba-base:implementer", "слияние", 10.0)], q
PY
printf '%s' "$OUT" | grep -q 'AskUserQuestion ×1' || fail "pipeline_queues: вопрос владельцу в очереди не показан" "$OUT"
printf '%s' "$OUT" | grep -q '| T001 | muagba-base:implementer | muagba-base:reviewer | 5.0 | 2.0 |' \
  || fail "pipeline_queues: ожидание доставки уведомления не посчитано" "$OUT"
rm -rf "$PQ"

# --- ночной режим (ADR-0016): хук, лаунчер, проба, утренний отчёт ----------
# Ночью вопрос человеку висел до утра. Хук отвечает отказом с причиной и
# пишет нужное в утренний список; лаунчер не стартует ночь без подготовки.
NM=$(mktemp -d); mkdir -p "$NM/p/.claude/logs"
nm() {  # <json> → stdout хука в ночном режиме
  printf '%s' "$1" | CLAUDE_PROJECT_DIR="$NM/p" MUAGBA_MODE=night bash "$SCRIPTS/log-wait.sh"
}
OUT=$(nm '{"hook_event_name":"PermissionRequest","tool_name":"AskUserQuestion","session_id":"s","cwd":"'"$NM/p"'","tool_input":{"questions":[{"question":"Какой тип id?","options":[{"label":"uuid"},{"label":"bigint"}]}]}}')
printf '%s' "$OUT" | grep -q '"behavior": "deny"' || fail "ночь: вопрос человеку не отклонён" "$OUT"
grep -q 'Какой тип id?.*uuid; bigint' "$NM/p/.claude/logs/morning.md" \
  || fail "ночь: вопрос не записан в утренний список" "$(cat "$NM/p/.claude/logs/morning.md" 2>/dev/null)"
OUT=$(nm '{"hook_event_name":"PermissionRequest","tool_name":"Bash","session_id":"s","cwd":"'"$NM/p"'","agent_type":"implementer","tool_input":{"command":"rm SECRETTEXT","description":"Удалить старый снимок"}}')
printf '%s' "$OUT" | grep -q '"behavior": "deny"' || fail "ночь: действие не отклонено" "$OUT"
grep -q 'implementer · нужно разрешение: Bash — Удалить старый снимок' "$NM/p/.claude/logs/morning.md" \
  || fail "ночь: действие не записано в утренний список" "$(cat "$NM/p/.claude/logs/morning.md")"
grep -q SECRETTEXT "$NM/p/.claude/logs/morning.md" "$NM/p/.claude/logs/agents.jsonl" && fail "ночь: текст команды попал в записи" ""
grep -q '"event": "night_deferred"' "$NM/p/.claude/logs/agents.jsonl" || fail "ночь: отложенное не в журнале" ""
grep -q '"event": "wait"' "$NM/p/.claude/logs/agents.jsonl" && fail "ночь: отказ записан как ожидание" ""
# Днём — по-прежнему вопрос человеку: хук решения не возвращает.
OUT=$(printf '{"hook_event_name":"PermissionRequest","tool_name":"Bash","session_id":"s","tool_input":{"command":"rm x"}}' \
  | CLAUDE_PROJECT_DIR="$NM/p" bash "$SCRIPTS/log-wait.sh")
[ -z "$OUT" ] || fail "день: хук ожидания вернул решение" "$OUT"

# Лаунчер: без подготовки сначала подготовка, ночь — после «y».
TPL="$SCRIPTS/../../../template/.claude"
mkdir -p "$NM/l/.claude/night"; cp "$TPL/claude-night" "$NM/l/.claude/"; cp "$TPL/night/settings.json" "$NM/l/.claude/night/"
cat > "$NM/fake" <<SH
#!/usr/bin/env bash
echo "\$MUAGBA_MODE|\$*" >> "$NM/calls"
pwd >> "$NM/dirs"
if [ "\$1" = /muagba-base:night-prep ] && [ -f "$NM/prep-writes" ]; then
  printf '{"date":"%s","allow_rules":["Удаление build/ в T019"],"allow_commands":["Bash(make clean)"],"dangerous":["миграция тестовой базы"]}' "\$(date +%F)" > "\$MUAGBA_NIGHT_APPROVED"
fi
for a in "\$@"; do case "\$prev" in --settings) cp "\$a" "$NM/merged.json";; esac; prev="\$a"; done
SH
chmod +x "$NM/fake"
(cd "$NM/l" && echo y | CLAUDE_BIN="$NM/fake" bash .claude/claude-night >/dev/null 2>&1); CODE=$?
[ "$CODE" = 1 ] && grep -q '^|/muagba-base:night-prep' "$NM/calls" && ! grep -q '^night|' "$NM/calls" \
  || fail "лаунчер: ночь без утверждённых разрешений" "$(cat "$NM/calls")"
: > "$NM/calls"; touch "$NM/prep-writes"
# --resume: ночь — в каталоге сессии, а не там, где лежит лаунчер (у narta
# лаунчер в дереве координатора, сессия — в основном checkout).
mkdir -p "$NM/home/.claude/projects/x" "$NM/sess"; : > "$NM/dirs"
printf '{"type":"mode"}\n{"cwd":"%s","type":"user"}\n' "$NM/sess" > "$NM/home/.claude/projects/x/abc.jsonl"
OUT=$(cd "$NM/l" && echo y | HOME="$NM/home" CLAUDE_BIN="$NM/fake" bash .claude/claude-night --resume abc 2>&1)
grep -q '^|/muagba-base:night-prep' "$NM/calls" || fail "лаунчер: подготовка не запущена" "$(cat "$NM/calls")"
[ "$(sort -u "$NM/dirs")" = "$NM/sess" ] || fail "лаунчер: подготовка или ночь не в каталоге сессии" "$(cat "$NM/dirs")"
grep -q '^night|--permission-mode auto --settings .* --resume abc' "$NM/calls" \
  || fail "лаунчер: ночь не в режиме auto с правилами" "$(cat "$NM/calls")"
printf '%s' "$OUT" | grep -q 'ОПАСНОЕ, утверждено явно: миграция тестовой базы' || fail "лаунчер: опасное не показано" "$OUT"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert 'Удаление build/ в T019' in d['autoMode']['allow'] and 'Bash(make clean)' in d['permissions']['allow'] and d['autoMode']['hard_deny']" "$NM/merged.json" \
  || fail "лаунчер: утверждённое не попало в правила ночи" "$(cat "$NM/merged.json")"
: > "$NM/calls"; (cd "$NM/l" && echo n | CLAUDE_BIN="$NM/fake" bash .claude/claude-night >/dev/null 2>&1)
[ ! -s "$NM/calls" ] || fail "лаунчер: ночь стартовала без «y» или подготовка повторилась" "$(cat "$NM/calls")"
(cd "$NM/l" && echo y | HOME="$NM/home" CLAUDE_BIN="$NM/fake" bash .claude/claude-night --resume нетакой >/dev/null 2>&1); CODE=$?
[ "$CODE" = 1 ] && [ ! -s "$NM/calls" ] || fail "лаунчер: несуществующая сессия не остановила запуск" "$(cat "$NM/calls")"

# Из сессии (/muagba-base:night): --yes --bg — без терминала, ночь в фоне.
: > "$NM/calls"; mv "$NM/l/.claude/night/approved.json" "$NM/appr.bak"
(cd "$NM/l" && HOME="$NM/home" CLAUDE_BIN="$NM/fake" bash .claude/claude-night --yes --bg --resume abc </dev/null >/dev/null 2>&1); CODE=$?
[ "$CODE" = 1 ] && [ ! -s "$NM/calls" ] || fail "лаунчер --yes: ночь без подготовки" "$(cat "$NM/calls")"
mv "$NM/appr.bak" "$NM/l/.claude/night/approved.json"
OUT=$(cd "$NM/l" && HOME="$NM/home" CLAUDE_BIN="$NM/fake" bash .claude/claude-night --yes --bg --resume abc </dev/null 2>&1); CODE=$?
[ "$CODE" = 0 ] && grep -q '^night|--bg --permission-mode auto --settings .* --resume abc Ночь началась' "$NM/calls" \
  || fail "лаунчер --bg: ночь не в фоне или без поручения" "$(cat "$NM/calls"; echo; echo "$OUT")"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['env']['MUAGBA_MODE']=='night'" "$NM/merged.json" \
  || fail "лаунчер: пометка ночи не в настройках сессии" "$(cat "$NM/merged.json")"
printf '%s' "$OUT" | grep -q 'закройте' || fail "лаунчер --bg: нет напоминания закрыть дневную сессию" "$OUT"

# Поиск лаунчера без привязки к каталогу: из основного checkout — в дереве.
mkdir -p "$NM/m"; git -C "$NM/m" init -q; git -C "$NM/m" -c user.name=t -c user.email=t@t commit -q --allow-empty -m i
git -C "$NM/m" worktree add -q "$NM/m/.claude/worktrees/coord" 2>/dev/null
[ "$(python3 "$SCRIPTS/night_locate.py" "$NM/m" | python3 -c 'import json,sys; print(json.load(sys.stdin)["launcher"])')" = None ] \
  || fail "night_locate: нашёл лаунчер там, где его нет" ""
mkdir -p "$NM/m/.claude/worktrees/coord/.claude/night"
cp "$TPL/claude-night" "$NM/m/.claude/worktrees/coord/.claude/"; cp "$TPL/night/settings.json" "$NM/m/.claude/worktrees/coord/.claude/night/"
printf '{"date":"%s"}' "$(date +%F)" > "$NM/m/.claude/worktrees/coord/.claude/night/approved.json"
python3 "$SCRIPTS/night_locate.py" "$NM/m" | grep -q '"launcher": "'"$NM"'/m/.claude/worktrees/coord/.claude/claude-night".*"approved_today": true' \
  || fail "night_locate: лаунчер в дереве координатора не найден из основного checkout" "$(python3 "$SCRIPTS/night_locate.py" "$NM/m")"

# Ночь в той же сессии: night_switch on/off правит настройки человека и
# ставит пометку сессии; хуки по пометке отказывают; off убирает ровно своё.
NH="$NM/nh"; mkdir -p "$NH/.claude" "$NM/np/.claude/night" "$NM/np/.claude/logs"; git -C "$NM/np" init -q
cp "$TPL/night/settings.json" "$TPL/claude-night" "$NM/np/.claude/" 2>/dev/null; mv "$NM/np/.claude/settings.json" "$NM/np/.claude/night/settings.json"
printf '{"permissions":{"allow":["Bash(ls)"]},"autoMode":{"environment":["своё"]},"theme":"dark"}\n' > "$NH/.claude/settings.json"
cp "$NH/.claude/settings.json" "$NM/user.before.json"
sw() { HOME="$NH" python3 "$SCRIPTS/night_switch.py" "$@" --cwd "$NM/np"; }
sw on --session S1 >/dev/null && fail "night_switch: ночь без утверждённого включилась" ""
printf '{"date":"%s","allow_rules":["Удаление build/ в T7"],"allow_commands":["Bash(make clean)"]}' "$(date +%F)" > "$NM/np/.claude/night/approved.json"
sw on --session S1 >/dev/null || fail "night_switch: ночь не включилась" "$(sw on --session S1)"
python3 - "$NH/.claude/settings.json" <<'PY' || fail "night_switch: правила ночи не дописаны" "$(cat "$NH/.claude/settings.json")"
import json, sys
d = json.load(open(sys.argv[1]))
assert "Удаление build/ в T7" in d["autoMode"]["allow"] and d["autoMode"]["hard_deny"], d
assert "Bash(make clean)" in d["permissions"]["allow"] and "Bash(ls)" in d["permissions"]["allow"], d
assert any("main" in x for x in d["permissions"]["deny"]) and d["theme"] == "dark", d
PY
sw on --session S1 >/dev/null && fail "night_switch: ночь включена дважды" ""
OUT=$(printf '{"hook_event_name":"PermissionRequest","tool_name":"Bash","session_id":"S1","tool_input":{"command":"rm x"}}' \
  | HOME="$NH" CLAUDE_PROJECT_DIR="$NM/np" bash "$SCRIPTS/log-wait.sh")
printf '%s' "$OUT" | grep -q '"behavior": "deny"' || fail "ночь по пометке: вопрос не отклонён" "$OUT"
OUT=$(printf '{"hook_event_name":"PermissionRequest","tool_name":"Bash","session_id":"S2","tool_input":{"command":"rm x"}}' \
  | HOME="$NH" CLAUDE_PROJECT_DIR="$NM/np" bash "$SCRIPTS/log-wait.sh")
[ -z "$OUT" ] || fail "ночь по пометке: чужая сессия получила отказ" "$OUT"
printf '{"cwd":"%s","session_id":"S1"}' "$NM/np" | HOME="$NH" python3 "$SCRIPTS/night_status.py" | grep -q 'Ночной режим (ADR-0016)' \
  || fail "night_status: ночная по пометке сессия без напоминания" ""
printf '{"cwd":"%s","session_id":"S2"}' "$NM/np" | HOME="$NH" python3 "$SCRIPTS/night_status.py" | grep -q 'включены ночные правила' \
  || fail "night_status: другая сессия не предупреждена о ночных правилах" ""
sw off >/dev/null
python3 -c "import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); assert a==b, (a,b)" \
  "$NH/.claude/settings.json" "$NM/user.before.json" || fail "night_switch off: настройки человека не вернулись к прежним" "$(cat "$NH/.claude/settings.json")"
[ ! -e "$NH/.claude/muagba-night/sessions/S1.json" ] || fail "night_switch off: пометка ночи осталась" ""

# Старт сессии: подготовка есть, а ночного режима нет — предупредить.
mkdir -p "$NM/s/.claude/night"; git -C "$NM/s" init -q
ns() { printf '{"cwd":"%s"}' "$NM/s" | env "$@" python3 "$SCRIPTS/night_status.py"; }
[ -z "$(ns MUAGBA_MODE=)" ] || fail "night_status: говорит без подготовки" "$(ns MUAGBA_MODE=)"
printf '{"date":"%s"}' "$(date +%F)" > "$NM/s/.claude/night/approved.json"
ns MUAGBA_MODE= | grep -q 'systemMessage.*НЕ действует' || fail "night_status: ночь без лаунчера не замечена" "$(ns MUAGBA_MODE=)"
ns MUAGBA_MODE=night | grep -q 'Ночной режим (ADR-0016)' || fail "night_status: ночная сессия без напоминания" "$(ns MUAGBA_MODE=night)"
printf '{"date":"2000-01-01"}' > "$NM/s/.claude/night/approved.json"
[ -z "$(ns MUAGBA_MODE=)" ] || fail "night_status: вчерашняя подготовка принята за сегодняшнюю" ""

# Проба cycle.night: каркас зелёный; без защиты или без лаунчера — красный.
mkdir -p "$NM/c/.claude/night"; git -C "$NM/c" init -q
cp "$TPL/night/settings.json" "$NM/c/.claude/night/"; cp "$TPL/claude-night" "$TPL/protected-paths.txt" "$NM/c/.claude/"
[ "$(verdict "$NM/c" cycle.night)" = ok ] || fail "cycle.night: каркас красный" "$(detail "$NM/c" cycle.night)"
grep -v 'claude-night' "$TPL/protected-paths.txt" > "$NM/c/.claude/protected-paths.txt"
detail "$NM/c" cycle.night | grep -q 'не под защитой: .claude/claude-night' \
  || fail "cycle.night: незащищённый лаунчер принят" "$(detail "$NM/c" cycle.night)"
cp "$TPL/protected-paths.txt" "$NM/c/.claude/"; chmod -x "$NM/c/.claude/claude-night"
detail "$NM/c" cycle.night | grep -q 'нет исполняемого' || fail "cycle.night: неисполняемый лаунчер принят" "$(detail "$NM/c" cycle.night)"
rm -rf "$NM/c/.claude/night"
detail "$NM/c" cycle.night | grep -q 'не настроен' || fail "cycle.night: без правил принят" "$(detail "$NM/c" cycle.night)"

# Утренний отчёт: отложенное, отказы контролёра, слияния.
mkdir -p "$NM/t/sess/subagents"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '{"type":"user","timestamp":"%s","message":{"content":[{"type":"tool_result","tool_use_id":"x","content":"Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Self-Modification]. ..."}]}}\n' "$NOW" > "$NM/t/sess/subagents/agent-a.jsonl"
printf '{"type":"assistant","timestamp":"%s","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"gh pr merge 5 --merge"}}]}}\n' "$NOW" > "$NM/t/main.jsonl"
OUT=$(python3 "$SCRIPTS/night_report.py" --cwd "$NM/p" --transcripts "$NM/t" 2>&1)
printf '%s' "$OUT" | grep -q 'Какой тип id?' || fail "night_report: отложенное не показано" "$OUT"
printf '%s' "$OUT" | grep -q 'Self-Modification — 1' || fail "night_report: отказ контролёра не найден" "$OUT"
printf '%s' "$OUT" | grep -q 'слияний PR: 1' || fail "night_report: слияние не посчитано" "$OUT"
printf '%s' "$OUT" | grep -q 'отложено до человека: 2' || fail "night_report: отложенное не посчитано" "$OUT"
rm -rf "$NM"

# --- каркас в репозитории базы — не проект -------------------------------
# template/.claude/protected-paths.txt — исходник для проектов; к самому
# каркасу в репозитории базы он не применяется. В проекте каталог с именем
# template — обычный, и его список действует.
TB=$(mktemp -d); mkdir -p "$TB/base/plugins/muagba-base/.claude-plugin" "$TB/base/template/.claude" "$TB/proj/template/.claude"
git -C "$TB/base" init -q; git -C "$TB/proj" init -q
printf '.claude/night/settings.json\n' > "$TB/base/template/.claude/protected-paths.txt"; cp "$TB/base/template/.claude/protected-paths.txt" "$TB/proj/template/.claude/"
tb() {  # <файл> → код хука защиты путей на правку
  printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"},"cwd":"%s"}' "$1" "$(dirname "$1")" \
    | bash "$SCRIPTS/protect-paths.sh" >/dev/null 2>&1; echo $?
}
[ "$(tb "$TB/base/template/.claude/night/settings.json")" = 0 ] || fail "каркас базы: правка template/ запрещена списком каркаса" ""
[ "$(tb "$TB/proj/template/.claude/night/settings.json")" = 2 ] || fail "проект: каталог template вышел из-под защиты" ""
rm -rf "$TB"

# --- observe.compact: окно автосжатия задаёт проект -------------------------
# Без явного окна его выбирает Claude Code: на модели с 1M сжатие шло на 150 000.
OC=$(mktemp -d); mkdir -p "$OC/.claude"; git -C "$OC" init -q
echo '{}' > "$OC/.claude/settings.json"
detail "$OC" observe.compact | grep -q 'не задано' \
  || fail "observe.compact: окно по умолчанию принято за решение" "$(detail "$OC" observe.compact)"
echo '{"autoCompactWindow": 300000}' > "$OC/.claude/settings.json"
detail "$OC" observe.compact | grep -q '300000 (.claude/settings.json → autoCompactWindow)' \
  || fail "observe.compact: окно из настроек не найдено" "$(detail "$OC" observe.compact)"
# Переменная сильнее настройки, личный файл сильнее общего — как в Claude Code.
echo '{"env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000"}}' > "$OC/.claude/settings.local.json"
detail "$OC" observe.compact | grep -q '200000 (.claude/settings.local.json → env' \
  || fail "observe.compact: переменная окружения не перебила настройку" "$(detail "$OC" observe.compact)"
# Журнал напоминает раз в 150 000 — окно 200 000 сожмёт раньше.
mkdir -p "$OC/docs/journal"
detail "$OC" observe.compact | grep -q 'раньше напоминания' \
  || fail "observe.compact: напоминание журнала позже сжатия не замечено" "$(detail "$OC" observe.compact)"
echo '{"env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000", "MUAGBA_JOURNAL_EVERY": "100000"}}' > "$OC/.claude/settings.local.json"
[ "$(verdict "$OC" observe.compact)" = "ok" ] \
  || fail "observe.compact: порог журнала вдвое ниже окна не принят" "$(detail "$OC" observe.compact)"
rm -rf "$OC"
# Каркас ставит окно сам: новый проект зеленеет без вопроса «где это задать».
python3 -c "import json,sys; assert json.load(open(sys.argv[1]))['autoCompactWindow'] == 300000" \
  "$SCRIPTS/../../../template/.claude/settings.json" || fail "каркас: нет autoCompactWindow 300000" ""

# --- cycle.release: порядок выпуска ------------------------------------------
# Слот каркаса — красный; «релизов нет» с причиной — законный ответ.
RR=$(mktemp -d); mkdir -p "$RR/.claude" "$RR/docs"; git -C "$RR" init -q
cp "$SCRIPTS/../../../template/docs/workflow.md" "$RR/docs/workflow.md"
detail "$RR" cycle.release | grep -q 'не заполнен' \
  || fail "cycle.release: слот каркаса принят за ответ" "$(detail "$RR" cycle.release)"
printf '# Цикл\n\n## Релизы\n\nРелизов нет: сервис разворачивается при мерже в main.\n' > "$RR/docs/workflow.md"
[ "$(verdict "$RR" cycle.release)" = "ok" ] \
  || fail "cycle.release: «релизов нет» с причиной отвергнут" "$(detail "$RR" cycle.release)"
rm -rf "$RR"

# --- уборка рабочих деревьев ------------------------------------------------
# Безопасная уборка разрешена правилами, опасная — запрет с причиной, не
# вопрос: у narta каждое удаление дерева ночью ждало человека до утра.
WD=$(mktemp -d); ( cd "$WD" && git init -q -b main && echo a > a && git add a \
  && git -c user.email=t@t -c user.name=t commit -qm a && git worktree add -q wt -b feat \
  && echo b > wt/b && git -C wt add b && git -C wt -c user.email=t@t -c user.name=t commit -qm b )
# `|| true`: разбор выходит с 1 на находке, а прогон идёт с pipefail — без
# этого `wd … | grep -q` падал бы и при найденном совпадении.
wd() { printf '%s' "$1" | python3 "$SCRIPTS/worktree_danger.py" "$WD" 2>&1 || true; }
[ -z "$(wd 'git worktree remove --force wt')" ] || fail "worktree: --force по чистому дереву запрещён" "$(wd 'git worktree remove --force wt')"
echo x > "$WD/wt/dirty"
wd 'git worktree remove --force wt' | grep -q 'незакоммиченной работой' \
  || fail "worktree: --force по грязному дереву пропущен" "$(wd 'git worktree remove --force wt')"
wd 'if true; then git worktree remove -f wt; fi' | grep -q 'незакоммиченной' \
  || fail "worktree: --force внутри if пропущен" ""
wd 'git branch -D feat' | grep -q 'нет ни в одной другой ветке' \
  || fail "worktree: -D неслитой ветки пропущен" "$(wd 'git branch -D feat')"
( cd "$WD" && git merge -q --ff-only feat )
[ -z "$(wd 'git branch -D feat')" ] || fail "worktree: -D слитой ветки запрещён" "$(wd 'git branch -D feat')"
wd 'rm -rf wt' | grep -q 'рабочему дереву' || fail "worktree: rm -rf по дереву пропущен" "$(wd 'rm -rf wt')"
[ -z "$(wd 'rm -rf build')" ] || fail "worktree: rm -rf обычного каталога принят за дерево" ""
[ -z "$(wd 'git worktree remove wt')" ] || fail "worktree: remove без --force запрещён — git сам откажет" ""
# Через guard-bash — запрет, а не вопрос.
printf '{"tool_input":{"command":"rm -rf wt"},"cwd":"%s"}' "$WD" \
  | CLAUDE_PROJECT_DIR="$WD" bash "$SCRIPTS/guard-bash.sh" >/dev/null 2>&1
[ $? -eq 2 ] || fail "guard-bash: rm -rf по дереву не запрещён" ""
rm -rf "$WD"

# --- version_check: загружена та версия, что выпущена -----------------------
VC=$(mktemp -d); mkdir -p "$VC/home" "$VC/cache/p/1.0.0/.claude-plugin" "$VC/mp/.claude-plugin" "$VC/mp/plugins/p/.claude-plugin"
echo '{"name":"p","version":"1.0.0"}' > "$VC/cache/p/1.0.0/.claude-plugin/plugin.json"
echo '{"plugins":[{"name":"p","source":"./plugins/p"}]}' > "$VC/mp/.claude-plugin/marketplace.json"
echo '{"name":"p","version":"1.0.0"}' > "$VC/mp/plugins/p/.claude-plugin/plugin.json"
( cd "$VC/mp" && git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm r && git tag p--v1.0.0 )
SHA=$(git -C "$VC/mp" rev-parse HEAD)
echo "{\"mp\":{\"installLocation\":\"$VC/mp\"}}" > "$VC/home/known_marketplaces.json"
inst() { echo "{\"plugins\":{\"p@mp\":[{\"scope\":\"project\",\"installPath\":\"$VC/cache/p/1.0.0\",\"version\":\"1.0.0\",\"gitCommitSha\":\"$1\"}]}}" > "$VC/home/installed_plugins.json"; }
vc() { CLAUDE_PLUGIN_ROOT="$VC/cache/p/1.0.0" MUAGBA_PLUGINS_HOME="$VC/home" python3 "$SCRIPTS/version_check.py"; }
inst "$SHA"
[ -z "$(vc)" ] || fail "version_check: выпущенная и свежая версия вызвала предупреждение" "$(vc)"
echo '{"name":"p","version":"1.1.0"}' > "$VC/mp/plugins/p/.claude-plugin/plugin.json"
vc | grep -q 'в маркетплейсе уже 1.1.0.*--scope project' \
  || fail "version_check: устаревшая версия не замечена" "$(vc)"
echo '{"name":"p","version":"1.0.0"}' > "$VC/mp/plugins/p/.claude-plugin/plugin.json"
inst "0000000000000000000000000000000000000000"
vc | grep -q 'собрана не из выпуска' || fail "version_check: сборка не из тега не замечена" "$(vc)"
git -C "$VC/mp" tag -d p--v1.0.0 >/dev/null
vc | grep -q 'нет среди выпусков' || fail "version_check: версия без тега не замечена" "$(vc)"
[ -z "$(MUAGBA_PLUGINS_HOME="$VC/home" python3 "$SCRIPTS/version_check.py")" ] \
  || fail "version_check: без CLAUDE_PLUGIN_ROOT не молчит" ""
rm -rf "$VC"

# --- ожидание подтверждения и долгие команды --------------------------------
# Ночью вызов, ждущий человека, висел до утра, и журнал этого не отмечал.
AW=$(mktemp -d); mkdir -p "$AW/.claude/logs"; git -C "$AW" init -q
aw() { printf '%s' "$1" | CLAUDE_PROJECT_DIR="$AW" bash "$SCRIPTS/log-wait.sh" >/dev/null 2>&1; }
aw "{\"hook_event_name\":\"PermissionRequest\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git push -u origin feat/x && gh pr create --title SECRETTEXT\"},\"cwd\":\"$AW\"}"
aw "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"sleep 1\"},\"duration_ms\":1000,\"cwd\":\"$AW\"}"
aw "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"uv run pytest\"},\"duration_ms\":90000,\"cwd\":\"$AW\"}"
J="$AW/.claude/logs/agents.jsonl"
grep -q '"event": "wait".*"class": "git push+gh pr"' "$J" \
  || fail "журнал: ожидание подтверждения без класса составной команды" "$(cat "$J" 2>/dev/null)"
grep -q SECRETTEXT "$J" && fail "журнал: в ожидание попал текст команды" ""
grep -q '"event": "slow".*"class": "uv run".*"duration_ms": "90000"' "$J" \
  || fail "журнал: долгая команда не записана" "$(cat "$J")"
[ "$(grep -c '"event": "slow"' "$J")" = "1" ] || fail "журнал: быстрая команда записана как долгая" "$(cat "$J")"
rm -rf "$AW"

# --- preflight: что упрётся в подтверждение ---------------------------------
PF=$(mktemp -d); PH=$(mktemp -d); mkdir -p "$PF/.claude/hooks" "$PF/.claude/logs"; git -C "$PF" init -q
printf '.env\n' > "$PF/.claude/protected-paths.txt"
cat > "$PF/.claude/hooks/allow_make.py" <<'PY'
import json, sys
c = json.load(sys.stdin)["tool_input"]["command"]
if c.startswith("make ") or c.startswith("git push"):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
        "permissionDecision": "allow", "permissionDecisionReason": "проект"}}))
PY
cat > "$PF/.claude/settings.json" <<JSON
{"permissions": {"allow": ["Bash(git status *)"], "ask": ["Bash(git push *)"], "deny": ["Bash(git reset --hard *)"]},
 "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 \"$PF/.claude/hooks/allow_make.py\""}]}]}}
JSON
cat > "$PF/cmds.txt" <<'TXT'
# комментарий не команда
git status --short
git status && rm notes.md
git reset --hard HEAD
cp .env.example .env
make build
git push origin feat/x
TXT
OUT=$(HOME="$PH" python3 "$SCRIPTS/preflight.py" "$PF/cmds.txt" --cwd "$PF" 2>&1); CODE=$?
pf() { printf '%s\n' "$OUT" | grep -q "^$1 *$2\$" || fail "preflight: «$2» — ждали $1" "$OUT"; }
pf 'пройдёт' 'git status --short'
pf 'СПРОСИТ' 'git status && rm notes.md'
pf 'ЗАПРЕТ' 'git reset --hard HEAD'
pf 'ЗАПРЕТ' 'cp .env.example .env'
pf 'пройдёт' 'make build'
# allow хука ask-правило не перебивает — ради этого проверка и нужна.
pf 'СПРОСИТ' 'git push origin feat/x'
[ "$CODE" -eq 1 ] || fail "preflight: при застревающих командах код 1, вышел $CODE" ""
printf '%s' "$OUT" | grep -q 'упрётся в человека 4' || fail "preflight: неверный итог" "$OUT"
[ -s "$PF/.claude/logs/agents.jsonl" ] && fail "preflight: синтетические вызовы писали журнал" "$(cat "$PF/.claude/logs/agents.jsonl")"
rm -rf "$PF" "$PH"

# --- preflight: вопросы к человеку в спеках ---------------------------------
# Этап, упирающийся в неотвеченное, ночью встаёт в первый час (ADR-0014, 4–5).
PQ=$(mktemp -d); PQH=$(mktemp -d); mkdir -p "$PQ/specs/001-a" "$PQ/specs/002-b" "$PQ/specs/003-c"
printf -- '- **status:** draft\n\n## Открытые вопросы\n\n- В1. Кто владелец?\n- В2. Какой срок?\n\n## Решения по умолчанию\n\n- Д1. x\n  Спросить: да\n- Д2. y\n  Спросить: нет\n' > "$PQ/specs/001-a/spec.md"
# Пояснение и «вопросов нет: решены» — не вопросы. Ложное срабатывание на
# спеке narta, где владелец всё уже ответил.
printf -- '- **status:** active\n\n## Открытые вопросы\n\nРешает владелец; пока пункты есть, спека draft.\n\nОткрытых вопросов нет: В1–В4 владелец решил 25.09.\n' > "$PQ/specs/002-b/spec.md"
printf -- '- **status:** draft\n\n- R1. КОГДА а [ТРЕБУЕТ УТОЧНЕНИЯ: что]\n' > "$PQ/specs/003-c/spec.md"
OUT=$(HOME="$PQH" python3 "$SCRIPTS/preflight.py" /nonexistent --cwd "$PQ" 2>&1); CODE=$?
printf '%s' "$OUT" | grep -q '001-a: открытых 2, «Спросить: да» 1' \
  || fail "preflight: вопросы спеки не посчитаны" "$OUT"
printf '%s' "$OUT" | grep -q '002-b' && fail "preflight: «вопросов нет, решены» принято за вопросы" "$OUT"
printf '%s' "$OUT" | grep -q '003-c: пометок 1' || fail "preflight: пометка не найдена" "$OUT"
[ "$CODE" -eq 1 ] || fail "preflight: при вопросах в спеках код 1, вышел $CODE" ""
rm -rf "$PQ/specs/001-a" "$PQ/specs/003-c"
HOME="$PQH" python3 "$SCRIPTS/preflight.py" /nonexistent --cwd "$PQ" >/dev/null 2>&1 \
  || fail "preflight: без вопросов и без команд код не 0" ""
rm -rf "$PQ" "$PQH"

# --- preflight: где агент уже ждал ------------------------------------------
# Список был зелёным, а агент ночью склеил push и PR и простоял до утра:
# сверяем список с событиями wait журнала агентов по классу команды.
PW=$(mktemp -d); PWH=$(mktemp -d); mkdir -p "$PW/.claude/logs"
git -C "$PW" init -q; git -C "$PW" -c user.name=t -c user.email=t@t commit -q --allow-empty -m init
printf '{"permissions": {"allow": ["Bash(git status *)"]}}' > "$PW/.claude/settings.json"
printf 'git status --short\n' > "$PW/cmds.txt"
python3 - "$PW/.claude/logs/agents.jsonl" <<'PY'
import datetime, json, sys
now = datetime.datetime.now().replace(microsecond=0)
t = lambda **k: (now - datetime.timedelta(days=1) + datetime.timedelta(**k)).isoformat()
ev = [
    # ночная склейка: рядом работающий сабагент пишет в ту же сессию через 5 с —
    # это не конец ожидания; конец — следующий ход самого координатора
    {"ts": t(), "event": "wait", "session_id": "S", "agent_type": None, "tool": "Bash", "class": "git push+gh pr"},
    {"ts": t(seconds=5), "event": "SubagentStop", "session_id": "S", "agent_type": ""},
    {"ts": t(hours=2), "event": "turn", "session_id": "S", "agent_type": None},
    {"ts": t(hours=3), "event": "wait", "session_id": "S", "agent_type": None, "tool": "Bash", "class": "git status"},
    {"ts": t(hours=3, minutes=1), "event": "turn", "session_id": "S", "agent_type": None},
    {"ts": t(hours=4), "event": "wait", "session_id": "S", "agent_type": None, "tool": "AskUserQuestion", "class": "AskUserQuestion"},
    {"ts": (now - datetime.timedelta(days=20)).isoformat(), "event": "wait", "session_id": "S", "agent_type": None, "tool": "Bash", "class": "make"},
]
open(sys.argv[1], "w").write("".join(json.dumps(e) + "\n" for e in ev))
PY
OUT=$(HOME="$PWH" python3 "$SCRIPTS/preflight.py" "$PW/cmds.txt" --cwd "$PW" 2>&1); CODE=$?
printf '%s' "$OUT" | grep -q 'НЕТ В СПИСКЕ git push+gh pr — 1 раз, ждал 2 ч 0 мин' \
  || fail "preflight: ночная склейка не найдена или ожидание посчитано до события сабагента" "$OUT"
printf '%s' "$OUT" | grep -q 'в списке     git status — 1 раз' || fail "preflight: команда из списка не узнана" "$OUT"
printf '%s' "$OUT" | grep -q 'make' && fail "preflight: ожидание старше окна попало в вывод" "$OUT"
printf '%s' "$OUT" | grep -q 'Вопросов человеку за 7 дн.: 1' || fail "preflight: вопросы человеку не посчитаны" "$OUT"
[ "$CODE" -eq 1 ] || fail "preflight: при ожидании вне списка код 1, вышел $CODE" "$OUT"
OUT=$(MUAGBA_PREFLIGHT_DAYS=30 HOME="$PWH" python3 "$SCRIPTS/preflight.py" "$PW/cmds.txt" --cwd "$PW" 2>&1)
printf '%s' "$OUT" | grep -q 'НЕТ В СПИСКЕ make' || fail "preflight: окно MUAGBA_PREFLIGHT_DAYS не действует" "$OUT"
# Из рабочего дерева журнал берётся в основном checkout'е: туда его пишет log_event.
git -C "$PW" worktree add -q "$PW/wt" 2>/dev/null
mkdir -p "$PW/wt/.claude"; cp "$PW/.claude/settings.json" "$PW/wt/.claude/"
OUT=$(HOME="$PWH" python3 "$SCRIPTS/preflight.py" "$PW/cmds.txt" --cwd "$PW/wt" 2>&1)
printf '%s' "$OUT" | grep -q 'git push+gh pr' || fail "preflight: из рабочего дерева журнал не найден" "$OUT"
# Всё ожидавшее — в списке и проходит: код 0.
printf 'git status --short\ngit push origin x && gh pr create\n' > "$PW/cmds2.txt"
printf '{"permissions": {"allow": ["Bash(git status *)", "Bash(git push *)", "Bash(gh pr *)"]}}' > "$PW/.claude/settings.json"
HOME="$PWH" python3 "$SCRIPTS/preflight.py" "$PW/cmds2.txt" --cwd "$PW" >/dev/null 2>&1 \
  || fail "preflight: всё ожидавшее в списке и проходит, а код не 0" "$(HOME="$PWH" python3 "$SCRIPTS/preflight.py" "$PW/cmds2.txt" --cwd "$PW" 2>&1)"
rm -rf "$PW" "$PWH"

# --- observe.journal: журнал сессии включён и не роняет docsys -------------
OJ=$(mktemp -d); mkdir -p "$OJ/.claude"; git -C "$OJ" init -q
detail "$OJ" observe.journal | grep -q 'журнал сессии выключен' \
  || fail "observe.journal: выключенный журнал не замечен" "$(detail "$OJ" observe.journal)"
mkdir -p "$OJ/docs/journal"
[ "$(verdict "$OJ" observe.journal)" = "ok" ] \
  || fail "observe.journal: проект без docsys не должен краснеть" "$(detail "$OJ" observe.journal)"
echo '{"exclude": ["docs/INDEX.md"]}' > "$OJ/.claude/doc-config.json"
detail "$OJ" observe.journal | grep -q 'frontmatter' \
  || fail "observe.journal: docsys проверяет журнал, а проба молчит" "$(detail "$OJ" observe.journal)"
echo '{"exclude": ["docs/INDEX.md", "docs/journal/**"]}' > "$OJ/.claude/doc-config.json"
[ "$(verdict "$OJ" observe.journal)" = "ok" ] \
  || fail "observe.journal: исключение docs/journal/** не засчитано" "$(detail "$OJ" observe.journal)"
rm -rf "$OJ"

# --- journal_watch: журнал сессии через сжатие контекста ---------------------
# Агент сам /compact не вызывает — сжимает Claude Code. Хук напоминает
# записать журнал заранее, сохраняет выжимку сжатия и возвращает журнал после.
JW=$(mktemp -d); mkdir -p "$JW/p" "$JW/s"
jw_usage() {  # <токены> → transcript с одним ответом модели такого размера
  printf '{"type":"assistant","message":{"usage":{"input_tokens":1,"cache_read_input_tokens":%d,"cache_creation_input_tokens":0}}}\n' \
    "$(( $1 - 1 ))" > "$JW/t.jsonl"
}
jw() {  # <режим> [лишние поля JSON] → stdout хука
  printf '{"session_id":"s1","cwd":"%s","transcript_path":"%s","scratchpad_dir":"%s"%s}' \
    "$JW/p" "$JW/t.jsonl" "$JW/s" "${2:-}" \
    | env -u CLAUDE_CODE_AUTO_COMPACT_WINDOW HOME="$JW/home" MUAGBA_JOURNAL_EVERY=100000 \
      python3 "$SCRIPTS/journal_watch.py" "$1"
}
# Пользовательские настройки машины — не часть теста: окно в них сменило бы порог.
mkdir -p "$JW/home"
# Нет docs/journal/ — хук молчит при любом росте.
jw_usage 50000; jw tick >/dev/null; jw_usage 900000
[ -z "$(jw tick)" ] || fail "journal_watch: говорит в проекте без docs/journal/" ""
[ -z "$(jw reinject)" ] || fail "journal_watch: reinject в проекте без docs/journal/" ""
rm -f "$JW/s/"*

mkdir -p "$JW/p/docs/journal"; echo x > "$JW/p/docs/journal/2026-01-01.md"
jw_usage 50000; [ -z "$(jw tick)" ] || fail "journal_watch: напомнил на первом вызове" ""
jw_usage 120000; [ -z "$(jw tick)" ] || fail "journal_watch: напомнил до порога" "рост 70K при пороге 100K"
jw_usage 160000
jw tick | grep -q '"additionalContext".*docs/journal/2026-01-01.md' \
  || fail "journal_watch: не напомнил за порогом" "$(jw_usage 160000; jw tick)"
jw_usage 165000; [ -z "$(jw tick)" ] || fail "journal_watch: напоминает на каждый вызов" ""
jw_usage 190000; jw tick | grep -q additionalContext \
  || fail "journal_watch: проигнорированное напоминание не повторено" ""
# Журнал записан — отсчёт заново: следующий рост меряется от этой точки.
touch -d '+1 min' "$JW/p/docs/journal/2026-01-01.md"
jw_usage 200000; [ -z "$(jw tick)" ] || fail "journal_watch: запись журнала не сбросила отсчёт" ""
jw_usage 280000; [ -z "$(jw tick)" ] || fail "journal_watch: отсчёт не от записи журнала" "рост 80K"
# Сжатие: контекст упал ниже отметки — отсчёт от нового размера.
jw_usage 40000; jw tick >/dev/null
jw_usage 130000; [ -z "$(jw tick)" ] || fail "journal_watch: сжатие не сбросило отсчёт" "рост 90K"
# И обратная сторона: без сброса отметка осталась бы на 200K, и рост от
# сжатого контекста не замечался бы, пока не перерастёт старую отметку.
jw_usage 150000; jw tick | grep -q additionalContext \
  || fail "journal_watch: рост после сжатия меряется от старой отметки" "рост 110K от 40K"
# Сабагент журнал сессии не ведёт.
jw_usage 900000
[ -z "$(jw tick ',"agent_id":"a1"')" ] || fail "journal_watch: напомнил сабагенту" ""

# Окно задано — напоминание на 75% окна, даже если рост до порога не дошёл.
# При окне 300K и записи на ~190K остальное до сжатия жило бы только в выжимке.
rm -f "$JW/s/"*; mkdir -p "$JW/p/.claude"
echo '{"autoCompactWindow": 300000}' > "$JW/p/.claude/settings.json"
jw_usage 40000; jw tick >/dev/null
touch -d '+2 min' "$JW/p/docs/journal/2026-01-01.md"
jw_usage 190000; jw tick >/dev/null   # запись журнала на 190K — отметка
jw_usage 220000; [ -z "$(jw tick)" ] || fail "journal_watch: напомнил до 75% окна" "220K из 300K"
jw_usage 226000; jw tick | grep -q 'из окна автосжатия 300K' \
  || fail "journal_watch: не напомнил на 75% окна" "$(jw_usage 226000; jw tick)"
jw_usage 230000; [ -z "$(jw tick)" ] || fail "journal_watch: у окна напоминает на каждый вызов" ""
# Повтор — раз в четверть остатка до окна (≈18K), а не четверть порога роста.
jw_usage 246000; jw tick | grep -q 'из окна' \
  || fail "journal_watch: у окна повтор не успевает до сжатия" ""
# Записал за порогом — у окна больше не напоминает.
touch -d '+3 min' "$JW/p/docs/journal/2026-01-01.md"
jw_usage 250000; [ -z "$(jw tick)" ] || fail "journal_watch: запись у окна не засчитана" ""
jw_usage 280000; [ -z "$(jw tick)" ] || fail "journal_watch: напомнил после записи у окна" ""
# Переменная окружения сильнее настройки — как у Claude Code.
rm -f "$JW/s/"*; jw_usage 10000; jw tick >/dev/null
echo '{"autoCompactWindow": 300000, "env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "100000"}}' > "$JW/p/.claude/settings.json"
jw_usage 80000; jw tick | grep -q 'из окна автосжатия 100K' \
  || fail "journal_watch: переменная окна не перебила настройку" "$(jw_usage 80000; jw tick)"
# Окно в пользовательских настройках тоже окно.
rm -f "$JW/s/"* "$JW/p/.claude/settings.json"; jw_usage 10000; jw tick >/dev/null
mkdir -p "$JW/home/.claude"; echo '{"autoCompactWindow": 100000}' > "$JW/home/.claude/settings.json"
jw_usage 80000; jw tick | grep -q 'из окна автосжатия 100K' \
  || fail "journal_watch: окно из пользовательских настроек не прочитано" ""

jw postcompact ',"trigger":"auto","compact_summary":"ВЫЖИМКА-42"'
grep -rqs 'ВЫЖИМКА-42' "$JW/p/.claude/logs/compact/" \
  || fail "journal_watch: выжимка сжатия не сохранена" "$(ls -R "$JW/p/docs/journal")"
jw reinject | grep -q 'docs/journal/2026-01-01.md' \
  || fail "journal_watch: после сжатия не назван журнал" "$(jw reinject)"
rm -rf "$JW"

# --- образец branch_policy в каркасе ----------------------------------------
# Лежит выключенным, но проект, включивший его, получает ровно этот код —
# значит, его тесты обязаны быть зелёными здесь.
OUT=$(PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$SCRIPTS/../../../template/.claude/hooks" -q 2>&1) \
  || fail "branch_policy: тесты образца красные" "$OUT"

# --- setup_state: согласованность базы с самой собой ------------------------
python3 "$SCRIPTS/setup_state.py" --check-spec >/dev/null 2>&1 \
  || fail "setup_state --check-spec" "реестр проб разошёлся с docs/gates.md"
python3 "$SCRIPTS/setup_state.py" --check-questions >/dev/null 2>&1 \
  || fail "setup_state --check-questions" "есть машинная проба без вопроса в банке"

[ -z "$(ls -A "$SANDBOX")" ] || fail "прогон насорил в песочницу проекта сессии" "$(ls -A "$SANDBOX")"
rm -rf "$SANDBOX"
[ "$FAILED" -eq 0 ] && echo "хуки и пробы: ок"
exit "$FAILED"
