#!/usr/bin/env bash
# Единственная команда, дающая честный pass/fail.
# Её вызывает гейт хода плагина muagba-base и она же гоняется в CI.
#
# Две части (ADR-0015, вопрос В6.9). Гейт хода передаёт
# MUAGBA_GATE_EVENT=Stop|SubagentStop — тогда идёт быстрая часть: то, что
# ловит большинство ошибок за секунды (линтер, типы, документы). Полная —
# без MUAGBA_GATE_EVENT: вручную, перед слиянием и в CI на PR. Поделил —
# CI на pull_request обязан звать этот файл без MUAGBA_GATE_EVENT, это
# сверяет проба check.split. Быстрой цели нет — гейт гоняет полную, как
# раньше.
#
# Параллельные прогоны в одном дереве (гейт и фоновый прогон агента) не
# должны делить ничего изменяемого: покрытие — в файл на запуск
# (COVERAGE_FILE=.coverage.$$ или параллельный режим), тестовая база — с
# уникальным именем, серверы тестов (API, dev-сервер, браузерные наборы) —
# на свободном порту, выбранном при запуске, а не на зашитом или
# вычисленном из пути дерева: у narta гейт и фоновый прогон исполнителя
# в одном дереве четыре раза столкнулись на порту набора вёрстки. Иначе
# проверка краснеет при зелёных тестах.
#
# Что изменилось с последнего зелёного прогона гейта в этом дереве, гейт
# передаёт сам: MUAGBA_GATE_CHANGED — файл со списком путей (по строке),
# MUAGBA_GATE_BASE — то зелёное дерево git. Дорогие условные шаги решай по
# нему (gate_touches ниже), а не по всей ветке: ветка фичи с первых задач
# трогает всё, и шаг идёт на каждом прогоне. Нет переменной (первый прогон
# в дереве, полная проверка, CI) — gate_touches говорит «да».
#
# Ход координатора (Stop) засчитывает зелёное исполнителя (SubagentStop) на
# том же дереве, обратное — нет. Значит, часть Stop не шире SubagentStop.
#
# Пока проект не настроен — автоопределение. Как только стек выбран,
# замени тело на явные команды: явное лучше угаданного.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

run() { echo "==> $*"; "$@" || exit 1; }

# gate_touches <префикс…> — менялся ли с последнего зелёного прогона гейта
# путь под одним из префиксов. Без сведений от гейта — да.
gate_touches() {
  [ -n "${MUAGBA_GATE_CHANGED:-}" ] && [ -f "$MUAGBA_GATE_CHANGED" ] || return 0
  local path p
  while IFS= read -r path; do
    for p in "$@"; do case "$path" in "$p"*) return 0 ;; esac; done
  done < "$MUAGBA_GATE_CHANGED"
  return 1
}
# gate_only <префикс…> — менялись только пути под этими префиксами (и
# хоть что-то менялось). Без сведений от гейта — нет.
gate_only() {
  [ -n "${MUAGBA_GATE_CHANGED:-}" ] && [ -s "$MUAGBA_GATE_CHANGED" ] || return 1
  local path p hit
  while IFS= read -r path; do
    hit=
    for p in "$@"; do case "$path" in "$p"*) hit=1 ;; esac; done
    [ -n "$hit" ] || return 1
  done < "$MUAGBA_GATE_CHANGED"
  return 0
}
has_target() {  # <имя> — цель в Makefile, justfile или скрипт npm
  { [ -f Makefile ] && grep -qE "^$1:" Makefile; } \
    || { [ -f justfile ] && grep -qE "^$1:" justfile; } \
    || { [ -f package.json ] && grep -q "\"${1/-/:}\"" package.json; }
}
run_target() {  # <имя>
  if [ -f Makefile ] && grep -qE "^$1:" Makefile; then run make "$1"
  elif [ -f justfile ] && grep -qE "^$1:" justfile; then run just "$1"
  else run npm run "${1/-/:}"; fi
}

# Заполненность документов рамок. Мягко: новый проект не должен быть красным
# только из-за пустых заготовок. Когда рамки дописаны — убери --soft,
# и незаполненный слот начнёт ронять проверку.
python3 .claude/check-frames.py --soft

# Коды ответа сетевых взаимодействий — по реестру (ADR-0019, вопрос В6.10).
# Без .claude/response-codes.json ничего не делает.
[ -f .claude/check-codes.py ] && { python3 .claude/check-codes.py || exit 1; }

if [ -n "${MUAGBA_GATE_EVENT:-}" ]; then
  # С последнего зелёного правились только документы и спеки (журнал,
  # отметки задач) — короткий набор, если проект его завёл: цель
  # check-docs проверяет всё, что в этих каталогах можно сломать (формы
  # спек, ссылки, линт markdown). Нет цели — идём дальше, как обычно:
  # пропуск без неё снял бы проверку изменённого.
  if gate_only docs/ specs/ && has_target check-docs; then
    run_target check-docs; exit 0
  fi
  # Быстрая часть для гейта хода — если проект её завёл.
  if has_target check-quick; then
    run_target check-quick; exit 0
  fi
fi

if has_target check; then
  run_target check
else
  echo "check.sh: проверка кода ещё не настроена (этап Э6) — гейта нет."
fi
