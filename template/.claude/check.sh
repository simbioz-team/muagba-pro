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
# должны писать общих файлов: покрытие — в файл на запуск
# (COVERAGE_FILE=.coverage.$$ или параллельный режим), тестовая база — с
# уникальным именем. Иначе проверка краснеет при зелёных тестах.
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

# Быстрая часть для гейта хода — если проект её завёл.
if [ -n "${MUAGBA_GATE_EVENT:-}" ]; then
  if [ -f Makefile ] && grep -qE '^check-quick:' Makefile; then
    run make check-quick; exit 0
  elif [ -f justfile ] && grep -qE '^check-quick:' justfile; then
    run just check-quick; exit 0
  elif [ -f package.json ] && grep -q '"check:quick"' package.json; then
    run npm run check:quick; exit 0
  fi
fi

if [ -f Makefile ] && grep -qE '^check:' Makefile; then
  run make check
elif [ -f justfile ] && grep -qE '^check:' justfile; then
  run just check
elif [ -f package.json ] && grep -q '"check"' package.json; then
  run npm run check
else
  echo "check.sh: проверка кода ещё не настроена (этап Э6) — гейта нет."
fi
