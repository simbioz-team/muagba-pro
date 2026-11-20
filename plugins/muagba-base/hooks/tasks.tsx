// Панель задач: спека, сделано, в работе, осталось — и что именно открыто.
// Включается и выключается командой /progress; выбор помнится между сессиями.
// Считает scripts/task_status.py --json: тот же код, что и сегмент строки
// состояния, чтобы подсчёт жил в одном месте и проверялся run.sh.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { TaskView } from '../types'

const PANE = 'tasks'
const TITLE = 'Задачи'
const KEY = 'tasks-pane'
const EVERY_MS = 15_000
// Тег меняется, когда меняются поля TaskView: старое значение переживает перезагрузку.
const view = atom({ plugin: 'muagba-base', key: 'tasks' } as const, null, { shape: 'tasks-1' })

// Включена ли панель в этой сессии; после перезагрузки модуля восстанавливается из $.store.
let enabled = false

async function refresh($: EngineInterface) {
  if (!enabled) return
  const input = JSON.stringify({
    workspace: { current_dir: await $.session.cwd(), project_dir: await $.session.root() },
  })
  try {
    const run = await $.process.run(
      ['python3', `${$.plugin.root}/scripts/task_status.py`, '--json'],
      { stdin: input, timeoutMs: 5_000 },
    )
    const got = run.exitCode === 0 ? (JSON.parse(run.stdout || 'null') as TaskView | null) : null
    await update($, view, () => got)
  } catch {
    // Панель важнее точности: сбой подсчёта оставляет прошлую картину.
  }
}

async function turnOn($: EngineInterface) {
  enabled = true
  await $.store.set(KEY, true)
  await refresh($)
  return $.ui.open({ id: PANE, title: TITLE })
}

async function turnOff($: EngineInterface) {
  enabled = false
  await $.store.set(KEY, false)
  await $.ui.close({ id: PANE })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'progress',
      description: 'Панель задач спеки: /progress — включить или выключить, /progress on | off',
    })
    if ((await $.store.get(KEY)) === true) {
      await turnOn($)
    }
    // Исполнители стартуют и кончаются между ответами: без таймера счёт «в работе» отстаёт.
    $.clock.every(EVERY_MS, () => void refresh($))
    return next(e)
  })

  on('command.run', { command: 'progress' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    const isOpen = (await $.ui.panes()).some(p => p.id === PANE)
    const want = arg === 'on' ? true : arg === 'off' ? false : !isOpen
    if (!want) {
      await turnOff($)
      return { text: 'Панель задач выключена. Включить — /progress.' }
    }
    const opened = await turnOn($)
    return {
      text: opened.isPlaced
        ? 'Панель задач включена. Выключить — /progress.'
        : `Панель задач включена, но ждёт места: ${opened.reason}`,
    }
  })

  // Закрыли панель крестиком или клавишей — это тоже «выключить».
  on('ui.close', async ($, e, next) => {
    if (e.id === PANE && e.origin.kind === 'person') {
      enabled = false
      await $.store.set(KEY, false)
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    void refresh($)
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const v = await read($, view)
    if (v === null) {
      return (
        <Box flexDirection="column">
          <Text dimColor>В проекте нет specs/*/tasks.md — считать нечего.</Text>
        </Box>
      )
    }
    const rows = Math.max(3, (e.viewport?.rows ?? 24) - 6 - v.agents.length)
    const short = (t: string) => t.replace(/^muagba-base:/, '')
    return (
      <Box flexDirection="column">
        <Text bold wrap="truncate-end">
          {v.spec}
        </Text>
        <Text>
          <Text color="green">✓ {v.done}</Text> сделано · <Text color="yellow">⏵ {v.busy}</Text> в
          работе · <Text color="cyan">○ {v.left}</Text> осталось
        </Text>
        {v.agents.length > 0 && <Text dimColor>В работе:</Text>}
        {v.agents.map(a => (
          <Text wrap="truncate-end">
            {'  '}
            {short(a.type)} · {a.minutes} мин
          </Text>
        ))}
        {v.open.length > 0 && <Text dimColor>Открыто:</Text>}
        {v.open.slice(0, rows).map(t => (
          <Text wrap="truncate-end">
            {'  '}○ {t}
          </Text>
        ))}
        {v.open.length > rows && <Text dimColor>  …и ещё {v.open.length - rows}</Text>}
      </Box>
    )
  })
}
