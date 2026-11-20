/** Что панель задач показывает: вывод `task_status.py --json`. */
export type TaskAgent = { agent_id: string; type: string; minutes: number }
/** Ветка не называет спеку: только исполнители этой сессии. */
export type TaskViewNoSpec = { spec: null; branch: string; busy: number; agents: TaskAgent[] }
export type TaskViewSpec = {
  spec: string
  num: string
  path: string
  done: number
  busy: number
  left: number
  agents: TaskAgent[]
  open: string[]
}
export type TaskView = TaskViewSpec | TaskViewNoSpec

declare module 'claude-code' {
  interface PluginState {
    'muagba-base': { tasks: Shaped<TaskView | null> }
  }
}
