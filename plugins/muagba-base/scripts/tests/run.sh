#!/usr/bin/env bash
# Прогон проверок хуков. Вызывается из CI и руками.
# Без него файлы случаев — декорация: лежат, но ничего не ловят.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$(dirname "$HERE")"
FAILED=0

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

# А вот когда ограничены оба триггера — красная по делу.
printf 'on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n\njobs:\n  c:\n    steps:\n      - run: ./.claude/check.sh\n' \
  > "$CB/.github/workflows/ci.yml"
[ "$(verdict "$CB" check.ci)" = "fail" ] \
  || fail "check.ci: оба триггера слушают main, а работа в feat/ — должна краснеть" "$(detail "$CB" check.ci)"
rm -rf "$CB"

# --- observe.log: пробы гоняют и в рабочем дереве ----------------------------
# .claude/logs/ в игноре и в дерево не копируется, поэтому журнала там нет
# никогда. Журнал ведётся в проекте сессии, дерево — её временный checkout.
WT=$(mktemp -d); mkdir -p "$WT/main/.claude/logs"
( cd "$WT/main" && git init -q && printf 'x\n' > a.txt && git add -A \
  && git -c user.email=t@t -c user.name=t commit -qm x \
  && git worktree add -q ../tree -b wt 2>/dev/null )
printf '{"a":1}\n' > "$WT/main/.claude/logs/agents.jsonl"
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
printf '.env\n!.env.example\ndocs/workflow.md\n+docs/sources/\n' > "$GB/.claude/protected-paths.txt"
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

# Чтение защищённого файла без записи блокировать не за что.
[ "$(guard 'python3 -c "import pathlib; print(pathlib.Path(\"docs/workflow.md\").read_text())"')" = "OK" ] \
  || fail "guard-bash: чтение защищённого файла принято за запись" ""

# Исключение должно переживать проверку по упоминанию: .env.example не .env.
[ "$(guard 'python3 - <<PY
import pathlib
p = pathlib.Path(".env.example")
p.write_text("KEY=")
PY')" = "OK" ] || fail "guard-bash: .env.example заблокирован шаблоном .env" ""
rm -rf "$GB"

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

# --- setup_state: согласованность базы с самой собой ------------------------
python3 "$SCRIPTS/setup_state.py" --check-spec >/dev/null 2>&1 \
  || fail "setup_state --check-spec" "реестр проб разошёлся с docs/gates.md"
python3 "$SCRIPTS/setup_state.py" --check-questions >/dev/null 2>&1 \
  || fail "setup_state --check-questions" "есть машинная проба без вопроса в банке"

[ "$FAILED" -eq 0 ] && echo "хуки и пробы: ок"
exit "$FAILED"
