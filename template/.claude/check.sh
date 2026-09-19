#!/usr/bin/env bash
# Единственная команда, дающая честный pass/fail.
# Её вызывает Stop-хук плагина muagba-base и она же гоняется в CI.
#
# Пока проект не настроен — автоопределение. Как только стек выбран,
# замени тело на явные команды: явное лучше угаданного.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

run() { echo "==> $*"; "$@" || exit 1; }

# Заполненность документов рамок. Мягко: новый проект не должен быть красным
# только из-за пустых заготовок. Когда рамки дописаны — убери --soft,
# и незаполненный слот начнёт ронять проверку.
python3 .claude/check-frames.py --soft

if [ -f Makefile ] && grep -qE '^check:' Makefile; then
  run make check
elif [ -f justfile ] && grep -qE '^check:' justfile; then
  run just check
elif [ -f package.json ] && grep -q '"check"' package.json; then
  run npm run check
else
  echo "check.sh: проверка кода ещё не настроена (этап Э6) — гейта нет."
fi
