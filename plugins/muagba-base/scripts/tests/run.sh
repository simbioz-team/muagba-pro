#!/usr/bin/env bash
# Прогон проверок хуков. Вызывается из CI и руками.
# Без него файлы случаев — декорация: лежат, но ничего не ловят.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$(dirname "$HERE")"
FAILED=0

fail() { printf 'СБОЙ  %s\n      %s\n' "$1" "$2"; FAILED=1; }

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

# --- setup_state: согласованность базы с самой собой ------------------------
python3 "$SCRIPTS/setup_state.py" --check-spec >/dev/null 2>&1 \
  || fail "setup_state --check-spec" "реестр проб разошёлся с docs/gates.md"
python3 "$SCRIPTS/setup_state.py" --check-questions >/dev/null 2>&1 \
  || fail "setup_state --check-questions" "есть машинная проба без вопроса в банке"

[ "$FAILED" -eq 0 ] && echo "хуки и пробы: ок"
exit "$FAILED"
