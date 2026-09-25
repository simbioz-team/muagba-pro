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
    | MUAGBA_JOURNAL_EVERY=100000 python3 "$SCRIPTS/journal_watch.py" "$1"
}
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
