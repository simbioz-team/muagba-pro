#!/usr/bin/env bash
# PreToolUse: Bash
# Блокирует команды, уничтожающие чужую работу. В мультиагентном режиме это
# не теория: параллельный агент теряет незакоммиченное дерево молча.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
read_hook_input

CMD=$(jq_get tool_input.command)
[ -z "$CMD" ] && exit 0

block() {
  cat >&2 <<MSG
Запрещено: $1
Команда: $CMD
Что делать: $2
MSG
  exit 2
}

# Разбор rm вынесен в отдельный скрипт: шаблон вида *"rm -rf /"* ловил ЛЮБОЙ
# абсолютный путь, то есть обычное `rm -rf /tmp/build`, и объяснял это
# «удалением от корня». Здесь блокируются только корень, домашний каталог и
# каталоги первого уровня — там, где рекурсивное удаление сносит систему,
# а не результат сборки.
RM_TARGET=$(printf '%s' "$CMD" | python3 "$(dirname "${BASH_SOURCE[0]}")/rm_danger.py" 2>/dev/null)
if [ -n "$RM_TARGET" ]; then
  block "рекурсивное удаление '$RM_TARGET'" \
        "это корень, домашний каталог или каталог первого уровня. Укажи путь внутри проекта."
fi

# Запись в защищённый путь через оболочку. Без этой проверки запрет
# protect-paths.sh обходился одной строкой `cat > docs/constitution.md`:
# тот хук смотрит на инструменты правки и про Bash ничего не знает.
# Ловятся очевидные формы — перенаправление, tee, sed -i, cp/mv, dd.
# Полного разбора оболочки здесь нет и быть не может.
WORK=$(work_dir)
TARGETS=$(printf '%s' "$CMD" | python3 "$(dirname "${BASH_SOURCE[0]}")/write_targets.py" 2>/dev/null)
if [ -n "$TARGETS" ]; then
  while IFS= read -r target; do
    [ -n "$target" ] || continue
    case "$target" in /*) abs="$target" ;; *) abs="$WORK/$target" ;; esac
    # Список — у проекта, которому принадлежит цель записи, а не у сессии.
    OWNER=$(owner_dir "$abs") || OWNER="$WORK"
    PATTERNS=$(protected_patterns "$OWNER")
    [ -n "$PATTERNS" ] || continue
    allowed=0
    while IFS= read -r pat; do
      case "$pat" in !*) [[ "$abs" == *"${pat#!}"* ]] && allowed=1 ;; esac
    done <<< "$PATTERNS"
    [ "$allowed" -eq 1 ] && continue
    while IFS= read -r pat; do
      [ -n "$pat" ] || continue
      case "$pat" in !*) continue ;; esac
      once=0
      case "$pat" in +*) once=1; pat="${pat#+}" ;; esac
      case "$abs" in
        *"$pat"*)
          [ "$once" -eq 1 ] && [ ! -e "$abs" ] && continue
          block "запись в защищённый путь '$target'" \
                "этот файл правит человек. Шаблон '$pat' из .claude/protected-paths.txt." ;;
      esac
    done <<< "$PATTERNS"
  done <<< "$TARGETS"
fi

# Разбор по argv, а не по подстроке: упоминание опасной команды в тексте —
# не её выполнение. Раньше `echo "не делай git reset --hard"` блокировался
# наравне с самим сбросом, и даже процитировать совет было нельзя.
DANGER=$(printf '%s' "$CMD" | python3 "$(dirname "${BASH_SOURCE[0]}")/cmd_danger.py" 2>/dev/null)
if [ -n "$DANGER" ]; then
  block "$(printf '%s' "$DANGER" | sed -n 1p)" "$(printf '%s' "$DANGER" | sed -n 2p)"
fi
exit 0
