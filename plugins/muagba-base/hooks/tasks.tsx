// Панель задач: спека, сделано, в работе, осталось — и что именно открыто.
// Включается и выключается командой /progress; выбор помнится между сессиями.
// Считает scripts/task_status.py --json: тот же код, что и сегмент строки
// состояния, чтобы подсчёт жил в одном месте и проверялся run.sh.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { NartaSummary, NartaTask, TaskView } from '../types'

const PANE = 'tasks'
const TITLE = 'Задачи'
const KEY = 'tasks-pane'
const EVERY_MS = 15_000
// Тег меняется, когда меняются поля TaskView: старое значение переживает перезагрузку.
const view = atom({ plugin: 'muagba-base', key: 'tasks' } as const, null, { shape: 'tasks-2' })

// Задачи Narta этой сессии: номер → последний известный статус. Закрытые не
// переспрашиваем — они не возвращаются. Модуль перезагрузился — спросим заново.
const narta = new Map<string, NartaTask>()
const FINAL = new Set(['done', 'cancelled'])
const NARTA_EVERY_MS = 60_000
let nartaAt = 0
let nartaBusy = false

function summarize(): NartaSummary {
  const tasks = [...narta.values()]
  const n = (cats: string[]) => tasks.filter(t => cats.includes(t.cat)).length
  return {
    done: n(['done']),
    busy: n(['in_progress', 'review']),
    left: tasks.filter(t => !FINAL.has(t.cat) && !['in_progress', 'review'].includes(t.cat)).length,
    tasks,
  }
}

// Статусы задач Narta, которые сессия создала, взяла или перевела. Номера —
// из стенограммы (task_status.py --narta-keys), статусы — у Narta через
// подключение самой сессии: своих ключей у базы нет. Сессия без Narta — no-op.
async function refreshNarta($: EngineInterface, force = false) {
  const now = await $.clock.now()
  if (nartaBusy || (!force && now - nartaAt < NARTA_EVERY_MS)) return
  nartaBusy = true
  nartaAt = now
  try {
    const sid = await $.session.id()
    const info = await $.session.info()
    const root = await $.session.root()
    const run = await $.process.run(
      ['python3', `${$.plugin.root}/scripts/task_status.py`, '--narta-keys'],
      {
        stdin: JSON.stringify({
          session_id: sid,
          transcript_path: info.transcriptPath,
          workspace: { current_dir: await $.session.cwd(), project_dir: root },
        }),
        timeoutMs: 10_000,
      },
    )
    const got = JSON.parse(run.stdout || '{}') as { server?: string; keys?: string[] }
    if (!got.server || !got.keys?.length) return
    for (const key of got.keys) {
      const known = narta.get(key)
      if (known && FINAL.has(known.cat)) continue
      const res = await $.mcp.call(got.server, 'search_tasks', { text: key, limit: 5 })
      const text = res.content.map(b => b.text ?? '').join('')
      if (res.isError || text.startsWith('[narta:unavailable]')) break // сервис лежит — не долбим
      try {
        const rows = (JSON.parse(text) as { data?: Array<Record<string, unknown>> }).data ?? []
        const row = rows.find(x => x.key === key)
        if (row) {
          narta.set(key, { key, title: String(row.title ?? ''), cat: String(row.status_category ?? '') })
        }
      } catch {
        // ответ не JSON — задачу пропускаем, спросим в следующий раз
      }
    }
    await $.fs.write(`${root}/.claude/logs/progress/${sid}.json`, JSON.stringify(summarize()))
  } catch {
    // Счёт важнее точности: сбой оставляет прошлую картину.
  } finally {
    nartaBusy = false
  }
}

// Включена ли панель в этой сессии; после перезагрузки модуля восстанавливается из $.store.
let enabled = false

async function refresh($: EngineInterface) {
  await refreshNarta($)
  if (!enabled) return
  const input = JSON.stringify({
    session_id: await $.session.id(),
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
    void refreshNarta($, true)
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
    if (v.spec === null && v.narta) {
      const n = v.narta
      const busy = n.tasks.filter(t => t.cat === 'in_progress' || t.cat === 'review')
      const left = n.tasks.filter(t => t.cat === 'new' || t.cat === 'triage' || t.cat === '')
      const room = Math.max(3, (e.viewport?.rows ?? 24) - 6 - busy.length)
      return (
        <Box flexDirection="column">
          <Text bold>Задачи сессии в Narta</Text>
          <Text>
            <Text color="green">✓ {n.done}</Text> сделано · <Text color="yellow">⏵ {n.busy}</Text> в
            работе · <Text color="cyan">○ {n.left}</Text> осталось
          </Text>
          {busy.length > 0 && <Text dimColor>В работе:</Text>}
          {busy.map(t => (
            <Text wrap="truncate-end">
              {'  '}⏵ {t.key} {t.title}
              {t.cat === 'review' ? ' (проверка)' : ''}
            </Text>
          ))}
          {left.length > 0 && <Text dimColor>Осталось:</Text>}
          {left.slice(0, room).map(t => (
            <Text wrap="truncate-end">
              {'  '}○ {t.key} {t.title}
            </Text>
          ))}
          {left.length > room && <Text dimColor>  …и ещё {left.length - room}</Text>}
        </Box>
      )
    }
    if (v.spec === null) {
      return (
        <Box flexDirection="column">
          <Text dimColor wrap="truncate-end">
            Ветка {v.branch} не называет спеку (033-…) — счёта нет.
          </Text>
          <Text>
            <Text color="yellow">⏵ {v.busy}</Text> исполнителей этой сессии в работе
          </Text>
          {v.agents.map(a => (
            <Text wrap="truncate-end">
              {'  '}
              {a.type.replace(/^muagba-base:/, '')} · {a.minutes} мин
            </Text>
          ))}
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
