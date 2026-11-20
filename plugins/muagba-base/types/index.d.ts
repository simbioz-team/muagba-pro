/** Что панель задач показывает: вывод `task_status.py --json`. */
export type TaskAgent = { agent_id: string; type: string; minutes: number }
export type TaskView = {
  spec: string
  num: string
  path: string
  done: number
  busy: number
  left: number
  agents: TaskAgent[]
  open: string[]
}

declare module 'claude-code' {
  interface PluginState {
    'muagba-base': { tasks: Shaped<TaskView | null> }
  }
}
