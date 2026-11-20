/** Что панель задач показывает: вывод `task_status.py --json`. */
export type TaskAgent = { agent_id: string; type: string; minutes: number }
/** Задача трекера (Narta): номер, название, категория статуса. */
export type NartaTask = { key: string; title: string; cat: string }
/** Итог по задачам Narta этой сессии; мод пишет его в .claude/logs/progress/<сессия>.json. */
export type NartaSummary = { done: number; busy: number; left: number; tasks: NartaTask[] }
/** Ветка не называет спеку: задачи Narta сессии, если есть, и её исполнители. */
export type TaskViewNoSpec = {
  spec: null
  branch: string
  busy: number
  agents: TaskAgent[]
  narta?: NartaSummary
}
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
