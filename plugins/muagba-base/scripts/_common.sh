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

# Проект, которому принадлежит ФАЙЛ. Поднимаемся от него, пока не найдём
# .claude/. Это важнее cwd сессии: правила, действующие на файл, — это
# правила того проекта, в котором файл лежит. Сессия может настраивать
# соседний каталог (скил настройки прямо это умеет), и тогда cwd указывает
# не туда: применялись бы правила чужого проекта, а то и захардкоженные
# умолчания. Найдено обкаткой.
owner_dir() {
  local d
  d=$(dirname -- "$1" 2>/dev/null) || return 1
  while [ -n "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]; do
    if [ -d "$d/.claude" ] || [ -d "$d/.git" ]; then
      printf '%s' "$d"
      return 0
    fi
    d=$(dirname -- "$d")
  done
  return 1
}

# Шаблоны защищённых путей проекта, по одному на строку. Молчит, если проект
# список не завёл: база обязана быть no-op на неподготовленном проекте.
protected_patterns() {
  local list="$1/.claude/protected-paths.txt"
  [ -f "$list" ] || return 0
  while IFS= read -r line; do
    line="${line%%#*}"; line="${line// /}"
    [ -n "$line" ] && printf '%s\n' "$line"
  done < "$list"
}

# mentions <текст> <шаблон> — встречается ли шаблон как путь, а не как кусок
# чужого слова. Простой поиск подстроки ловил `os.environ` шаблоном `.env` и
# отвергал любой heredoc, читающий переменные окружения: исполнители теряли
# по два прогона, пока не догадывались перейти на Edit. Совпадение считается,
# только если слева не буква-цифра-подчёркивание, а справа — то же самое, но
# лишь когда шаблон кончается словарным символом: у `.git/` граница уже стоит
# своим слэшем, и проверка справа запретила бы `.git/config`.
mentions() {
  local rest="$1" pat="$2" before pre post post_matters
  [ -n "$pat" ] || return 1
  case "${pat: -1}" in
    [A-Za-z0-9_]) post_matters=1 ;;
    *) post_matters=0 ;;
  esac
  while [[ "$rest" == *"$pat"* ]]; do
    before="${rest%%"$pat"*}"
    pre="${before: -1}"
    rest="${rest#*"$pat"}"
    post="${rest:0:1}"
    [[ "$pre" =~ [A-Za-z0-9_] ]] && continue
    [ "$post_matters" -eq 1 ] && [[ "$post" =~ [A-Za-z0-9_] ]] && continue
    return 0
  done
  return 1
}
