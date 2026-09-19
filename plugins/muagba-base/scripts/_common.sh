# Общие помощники хуков muagba-base. Подключается через `source`.
# Вход хука — JSON на stdin. Читаем один раз в HOOK_INPUT.

read_hook_input() {
  HOOK_INPUT=$(cat)
}

# jq_get <путь> — достать поле из HOOK_INPUT. Пусто, если нет.
# Используем python3, а не jq: он есть на любой машине разработчика,
# а лишняя зависимость в базе, которую копируют в каждый проект, не нужна.
jq_get() {
  printf '%s' "$HOOK_INPUT" | python3 -c '
import json, sys
path = sys.argv[1].split(".")
try:
    cur = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for key in path:
    if not isinstance(cur, dict) or key not in cur:
        sys.exit(0)
    cur = cur[key]
if cur is not None:
    print(cur if isinstance(cur, str) else json.dumps(cur, ensure_ascii=False))
' "$1" 2>/dev/null
}

# Корень проекта, где стартовала сессия.
project_dir() {
  printf '%s' "${CLAUDE_PROJECT_DIR:-$PWD}"
}

# Рабочая директория ЭТОГО вызова. В worktree-сессии она отличается от
# project_dir: ${CLAUDE_PROJECT_DIR} остаётся на основном checkout, а cwd
# едет за агентом. Всё, что проверяет файлы проекта, должно брать её.
work_dir() {
  local cwd
  cwd=$(jq_get cwd)
  printf '%s' "${cwd:-$(project_dir)}"
}
