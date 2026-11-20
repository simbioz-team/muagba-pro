import { expect, test } from 'claude-code/testing'

const VIEW = {
  spec: '033-feature', num: '033', path: '/p/specs/033-feature/tasks.md',
  done: 2, busy: 1, left: 2,
  agents: [{ agent_id: 'a1', type: 'muagba-base:implementer', minutes: 7 }],
  open: ['T3 c', 'T4 d', 'T5 e'],
}

const PANE = {
  plugin: 'muagba-base',
  component: 'Pane',
  requestId: 'tasks',
  props: {
    title: 'Задачи', isFocused: false, bodyColumns: 60, placement: 'dock',
    scroll: { offset: 0, bodyRows: 20 }, view: {},
  },
} as const

const NARTA: Record<string, Record<string, string>> = {
  'T-1': { key: 'T-1', title: 'сделанная', status_category: 'done' },
  'T-2': { key: 'T-2', title: 'идёт', status_category: 'in_progress' },
  'T-3': { key: 'T-3', title: 'ждёт', status_category: 'new' },
  'T-4': { key: 'T-4', title: 'проверяют', status_category: 'review' },
}
let writes: Array<{ path: string; text: string }> = []
let runs: string[][] = []
let toasts: string[] = []
let appended: string[] = []
let calls: string[] = []

function engine(on: any, store: Record<string, unknown>, opened: string[], closed: string[], stdout = JSON.stringify(VIEW), keys = '{"server":"","keys":[]}') {
  writes = []
  calls = []
  runs = []
  toasts = []
  appended = []
  on('command.register', (_: unknown, e: { name: string }) => ({ value: { command: e.name } }))
  on('store.get', (_: unknown, e: { key: string }) => ({ value: store[e.key] }))
  on('store.set', (_: unknown, e: { key: string; value: unknown }) => { store[e.key] = e.value; return { value: undefined } })
  on('ui.open', (_: unknown, e: { id: string }) => { opened.push(e.id); return { value: { isPlaced: true } } })
  on('ui.close', (_: unknown, e: { id: string }) => { closed.push(e.id); return { value: undefined } })
  on('ui.panes', () => ({ value: opened.filter(id => !closed.includes(id)).map(id => ({ id, title: id })) }))
  on('session.cwd', () => ({ value: '/p' }))
  on('session.root', () => ({ value: '/p' }))
  on('session.id', () => ({ value: 's1' }))
  on('process.run', (_: unknown, e: { argv: string[] }) => {
    runs.push(e.argv)
    const sync = e.argv.some(a => a.endsWith('template_sync.py'))
    const out = sync ? JSON.stringify({ systemMessage: 'muagba-base обновила файлы базы' })
      : e.argv.includes('--narta-keys') ? keys : stdout
    return { value: { exitCode: 0, stdout: out, stderr: '' } }
  })
  on('session.append', (_: unknown, e: any, next: (e: any) => unknown) => {
    const text = e?.message?.content?.[0]?.text
    if (typeof text === 'string' && text.includes('Перечитай')) appended.push(text)
    return next(e)
  })
  on('ui.toast', (_: unknown, e: { text: string }) => { toasts.push(e.text); return { value: undefined } })
  on('session.info', () => ({ value: { transcriptPath: '/p/t.jsonl' } }))
  on('clock.now', () => ({ value: Date.now() }))
  on('fs.write', (_: unknown, e: { path: string; text: string }) => { writes.push(e); return { value: undefined } })
  on('mcp.call', (_: unknown, e: { server: string; tool: string; args: { text: string } }) => {
    calls.push(`${e.server}/${e.tool}/${e.args.text}`)
    const row = NARTA[e.args.text]
    return { value: { isError: false, content: [{ type: 'text', text: JSON.stringify({ data: row ? [row] : [] }) }] } }
  })
  on('session.start', (_: unknown, e: { cwd: string }) => ({ cwd: e.cwd }))
  on('command.run', () => ({ text: '' }))
  // Таймер в тесте не тикает: отказ периода кончает интервал.
  on('clock.every', () => ({ deny: 'тест' }))
}

test('/progress включает панель, она показывает счёт и открытые задачи; второй раз — выключает', async ($, on) => {
  const store: Record<string, unknown> = {}
  const opened: string[] = []
  const closed: string[] = []
  engine(on, store, opened, closed)
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  expect(opened).toEqual([])

  const r1 = await $.command.run({ command: 'progress', args: '' })
  expect(r1.text).toMatch(/включена/)
  expect(store['tasks-pane']).toBe(true)
  expect(opened).toEqual(['tasks'])

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /033-feature/ }))?.text).toBe('033-feature')
    expect((await ui.find({ type: 'Text', text: /сделано/ }))?.text).toMatch(/2.*1.*2/)
    expect(await ui.find({ type: 'Text', text: /implementer · 7 мин/ })).toBeTruthy()
    expect(await ui.find({ type: 'Text', text: /T5 e/ })).toBeTruthy()
    await ui.unmount()
  }

  const r2 = await $.command.run({ command: 'progress', args: '' })
  expect(r2.text).toMatch(/выключена/)
  expect(store['tasks-pane']).toBe(false)
  expect(closed).toEqual(['tasks'])
})

test('включённая панель открывается в новой сессии сама', async ($, on) => {
  const store: Record<string, unknown> = { 'tasks-pane': true }
  const opened: string[] = []
  engine(on, store, opened, [])
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  expect(opened).toEqual(['tasks'])
})

test('без tasks.md панель так и говорит', async ($, on) => {
  const store: Record<string, unknown> = {}
  engine(on, store, [], [], 'null')
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'progress', args: 'on' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toMatch(/нет specs/)
  await ui.unmount()
})

test('ветка без номера спеки: панель говорит это и показывает исполнителей сессии', async ($, on) => {
  const store: Record<string, unknown> = {}
  const nospec = { spec: null, branch: 'feature/x', busy: 1, agents: [{ agent_id: 'a1', type: 'muagba-base:implementer', minutes: 3 }] }
  engine(on, store, [], [], JSON.stringify(nospec))
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'progress', args: 'on' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /не называет спеку/ }))?.text).toMatch(/feature\/x/)
  expect(await ui.find({ type: 'Text', text: /implementer · 3 мин/ })).toBeTruthy()
  await ui.unmount()
})

test('задачи Narta сессии: статусы спрашиваются у Narta, итог пишется для строки состояния', async ($, on) => {
  engine(on, {}, [], [], JSON.stringify(VIEW), JSON.stringify({ server: 'narta', keys: ['T-1', 'T-2', 'T-3', 'T-4'] }))
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'progress', args: 'on' })
  expect(calls).toEqual(['narta/search_tasks/T-1', 'narta/search_tasks/T-2', 'narta/search_tasks/T-3', 'narta/search_tasks/T-4'])
  const w = writes.at(-1)
  expect(w?.path).toBe('/p/.claude/logs/progress/s1.json')
  const sum = JSON.parse(w?.text ?? '{}')
  expect([sum.done, sum.busy, sum.review, sum.left]).toEqual([1, 1, 1, 1])
})

test('сессия без Narta к Narta не ходит и ничего не пишет', async ($, on) => {
  engine(on, {}, [], [])
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'progress', args: 'on' })
  expect(calls).toEqual([])
  expect(writes).toEqual([])
})

test('панель показывает задачи Narta, когда ветка не называет спеку', async ($, on) => {
  const v = { spec: null, branch: 'feature/x', busy: 1, agents: [], narta: { done: 1, busy: 1, review: 1, left: 1, tasks: [
    { key: 'T-1', title: 'сделанная', cat: 'done' }, { key: 'T-2', title: 'идёт', cat: 'in_progress' }, { key: 'T-3', title: 'ждёт', cat: 'new' },
    { key: 'T-4', title: 'проверяют', cat: 'review' }] } }
  engine(on, {}, [], [], JSON.stringify(v))
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'progress', args: 'on' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /Задачи сессии в Narta/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /T-2 идёт/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /T-3 ждёт/ })).toBeTruthy()
  expect((await ui.find({ type: 'Text', text: /T-4 проверяют/ }))?.text).toMatch(/◐/)
  expect(await ui.find({ type: 'Text', text: /На проверке:/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /T-1 сделанная/ })).toBeFalsy()
  await ui.unmount()
})

test('файлы базы: модуль зовёт синхронизацию на старте — и после перезагрузки плагина', async ($, on) => {
  engine(on, {}, [], [])
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await new Promise(r => setTimeout(r, 0))
  const sync = runs.filter(a => a.some(x => x.endsWith('template_sync.py')))
  expect(sync.length).toBe(1)
  expect(toasts).toEqual(['muagba-base обновила файлы базы'])
  // модели — напоминание перечитать: файлы в контексте прочитаны при старте
  expect(appended.length).toBe(1)
  expect(appended[0]).toMatch(/Перечитай/)
})

test('кнопка сворачивает панель до заголовка и счёта; выбор помнится', async ($, on) => {
  const store: Record<string, unknown> = {}
  engine(on, store, [], [])
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'progress', args: 'on' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /T5 e/ })).toBeTruthy()
  await ui.press({ key: 'compact' })
  expect(store['tasks-compact']).toBe(true)
  expect(await ui.find({ type: 'Text', text: /T5 e/ })).toBeFalsy()
  expect((await ui.find({ type: 'Text', text: /сделано/ }))?.text).toMatch(/2.*1.*2/)
  await ui.press({ key: 'compact' })
  expect(store['tasks-compact']).toBe(false)
  expect(await ui.find({ type: 'Text', text: /T5 e/ })).toBeTruthy()
  await ui.unmount()
})

test('свёрнутая панель открывается свёрнутой; /progress full разворачивает', async ($, on) => {
  const store: Record<string, unknown> = { 'tasks-pane': true, 'tasks-compact': true }
  engine(on, store, [], [])
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /T5 e/ })).toBeFalsy()
  await ui.unmount()
  const r = await $.command.run({ command: 'progress', args: 'full' })
  expect(r.text).toMatch(/развёрнута/)
  expect(store['tasks-compact']).toBe(false)
})
