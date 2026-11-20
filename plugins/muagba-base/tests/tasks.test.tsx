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

function engine(on: any, store: Record<string, unknown>, opened: string[], closed: string[], stdout = JSON.stringify(VIEW)) {
  on('command.register', (_: unknown, e: { name: string }) => ({ value: { command: e.name } }))
  on('store.get', (_: unknown, e: { key: string }) => ({ value: store[e.key] }))
  on('store.set', (_: unknown, e: { key: string; value: unknown }) => { store[e.key] = e.value; return { value: undefined } })
  on('ui.open', (_: unknown, e: { id: string }) => { opened.push(e.id); return { value: { isPlaced: true } } })
  on('ui.close', (_: unknown, e: { id: string }) => { closed.push(e.id); return { value: undefined } })
  on('ui.panes', () => ({ value: opened.filter(id => !closed.includes(id)).map(id => ({ id, title: id })) }))
  on('session.cwd', () => ({ value: '/p' }))
  on('session.root', () => ({ value: '/p' }))
  on('session.id', () => ({ value: 's1' }))
  on('process.run', () => ({ value: { exitCode: 0, stdout, stderr: '' } }))
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
