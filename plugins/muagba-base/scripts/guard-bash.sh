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

# Вопрос человеку вместо запрета. Нужен там, где хук не может знать ответ:
# удаление невосстановимого файла бывает и нужным, и катастрофой, и отличает
# их только тот, кому эти данные принадлежат. exit 2 здесь врал бы.
ASK=""
ask_later() { [ -n "$ASK" ] || ASK="$1"; }
ask_now() {
  python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": sys.argv[1]}}, ensure_ascii=False))' "$1"
  exit 0
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

WORK=$(work_dir)

# Шаблон защиты, под который попадает путь: печатает его и отдаёт 0. Молчит
# и 1, если путь не защищён или проект списка не завёл. Список берём у
# проекта, которому принадлежит ЦЕЛЬ, а не у сессии: правила на файл
# накладывает тот проект, в котором файл лежит.
protected_pattern_for() {
  local abs="$1" owner patterns pat once
  owner=$(owner_dir "$abs") || owner="$WORK"
  patterns=$(protected_patterns "$owner")
  [ -n "$patterns" ] || return 1
  while IFS= read -r pat; do
    case "$pat" in !*) mentions "$abs" "${pat#!}" && return 1 ;; esac
  done <<< "$patterns"
  while IFS= read -r pat; do
    [ -n "$pat" ] || continue
    case "$pat" in !*) continue ;; esac
    once=0
    case "$pat" in +*) once=1; pat="${pat#+}" ;; esac
    mentions "$abs" "$pat" || continue
    # '+' — «записывается один раз»: файла ещё нет, значит это создание.
    [ "$once" -eq 1 ] && [ ! -e "$abs" ] && continue
    printf '%s' "$pat"
    return 0
  done <<< "$patterns"
  return 1
}

abs_path() {  # относительный путь достраиваем от рабочей директории
  case "$1" in /*) printf '%s' "$1" ;; *) printf '%s' "$WORK/$1" ;; esac
}

# Запись в защищённый путь через оболочку. Без этой проверки запрет
# protect-paths.sh обходился одной строкой `cat > docs/constitution.md`:
# тот хук смотрит на инструменты правки и про Bash ничего не знает.
# Ловятся очевидные формы — перенаправление, tee, sed -i, cp/mv, dd.
# Полного разбора оболочки здесь нет и быть не может.
TARGETS=$(printf '%s' "$CMD" | python3 "$(dirname "${BASH_SOURCE[0]}")/write_targets.py" 2>/dev/null)
if [ -n "$TARGETS" ]; then
  while IFS= read -r target; do
    [ -n "$target" ] || continue
    # '?' — запись есть, а цель вычисляется в коде и статически не читается.
    # Ни один разбор её не получит: это предел подхода, а не пробел регулярки.
    # Поэтому сверяем защищённые пути по тексту самой команды, сняв кавычки:
    # путь, собранный как Path(x)/"docs"/"workflow.md", иначе не читается как
    # docs/workflow.md. Нашли на себе — такая правка прошла мимо хука.
    if [ "$target" = "?" ]; then
      PATTERNS=$(protected_patterns "$WORK")
      [ -n "$PATTERNS" ] || continue
      BARE=$(printf '%s' "$CMD" | tr -d "\"'")
      # Исключения вырезаем из текста: иначе упоминание .env.example
      # сработает по шаблону .env.
      while IFS= read -r pat; do
        case "$pat" in !*) BARE=${BARE//"${pat#!}"/} ;; esac
      done <<< "$PATTERNS"
      while IFS= read -r pat; do
        [ -n "$pat" ] || continue
        # Шаблоны '+' пропускаем: там создание разрешено, а цель неизвестна,
        # и запрет сломал бы штатное заведение файлов.
        case "$pat" in !*|+*) continue ;; esac
        if mentions "$BARE" "$pat"; then
          block "запись в защищённый путь '$pat' — цель вычисляется в коде" \
                "статический разбор вычисленный путь не видит, поэтому здесь запрет по упоминанию. Правь этот файл инструментом Edit либо вынеси путь в команду явным литералом."
        fi
      done <<< "$PATTERNS"
      continue
    fi
    abs=$(abs_path "$target")
    if pat=$(protected_pattern_for "$abs"); then
      block "запись в защищённый путь '$target'" \
            "этот файл правит человек. Шаблон '$pat' из .claude/protected-paths.txt."
    fi
  done <<< "$TARGETS"
fi

# Удаление. Защита путей до сих пор смотрела только на запись, и
# `rm docs/constitution.md` проходил насквозь: запрет на правку стоял, а на
# снос — нет. Нашёл сосед, доводивший проект на базе.
DELETES=$(printf '%s' "$CMD" | python3 "$(dirname "${BASH_SOURCE[0]}")/rm_targets.py" 2>/dev/null)

# Каталоги и файлы, которые гит не хранит потому, что они пересобираются.
# Список нужен, чтобы вопрос про невосстановимое не задавался на каждой
# уборке сборочного мусора. Он заведомо неполон и это нормально: лишний
# вопрос стоит одного нажатия, пропущенное удаление данных — всего.
BUILD_DIRS='.venv venv node_modules bower_components dist build target __pycache__
.pytest_cache .mypy_cache .ruff_cache .tox .nox .cache .next .nuxt .parcel-cache
.turbo coverage htmlcov .gradle .terraform .eggs'

unrecoverable() {  # <abs> → 0, если удаление вернуть будет неоткуда
  local abs="$1" owner rel base d
  [ -e "$abs" ] || return 1          # маска или несуществующий путь — не наше дело
  owner=$(owner_dir "$abs") || return 1
  git -C "$owner" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 1
  # Файл в гите восстанавливается из истории; не в гите — ничем.
  git -C "$owner" check-ignore -q -- "$abs" 2>/dev/null || return 1
  rel="${abs#"$owner"/}"
  for d in $BUILD_DIRS; do
    case "/$rel/" in */"$d"/*) return 1 ;; esac
  done
  base=$(basename -- "$abs")
  case "$base" in
    *.pyc|*.pyo|*.class|*.o|*.so|*.log|.coverage|coverage.xml|*.egg-info) return 1 ;;
  esac
  return 0
}

if [ -n "$DELETES" ]; then
  while IFS= read -r target; do
    [ -n "$target" ] || continue
    abs=$(abs_path "$target")
    if pat=$(protected_pattern_for "$abs"); then
      block "удаление защищённого пути '$target'" \
            "этот файл правит человек, а удаление — самая необратимая из правок. Шаблон '$pat' из .claude/protected-paths.txt."
    fi
    # Не запрет, а вопрос: хук не знает, ценны ли эти данные, а человек знает.
    # Живой случай — агент одной цепочкой `проверил && rm -f` снёс базу с
    # данными заказчика, успев напечатать, сколько в ней записей.
    if unrecoverable "$abs"; then
      ask_later "Удаление '$target': файл не отслеживается гитом и не похож на артефакт сборки — восстановить его будет неоткуда, ни из истории, ни пересборкой. Подтверди, если эти данные точно не нужны."
    fi
  done <<< "$DELETES"
fi

# Разбор по argv, а не по подстроке: упоминание опасной команды в тексте —
# не её выполнение. Раньше `echo "не делай git reset --hard"` блокировался
# наравне с самим сбросом, и даже процитировать совет было нельзя.
DANGER=$(printf '%s' "$CMD" | python3 "$(dirname "${BASH_SOURCE[0]}")/cmd_danger.py" 2>/dev/null)
if [ -n "$DANGER" ]; then
  block "$(printf '%s' "$DANGER" | sed -n 1p)" "$(printf '%s' "$DANGER" | sed -n 2p)"
fi

# Вопрос задаём последним: запрет сильнее вопроса, и команда, в которой есть
# и то и другое, обязана упереться в запрет, а не в приглашение подтвердить.
[ -n "$ASK" ] && ask_now "$ASK"
exit 0
