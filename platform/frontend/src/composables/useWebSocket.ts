import { ref, onUnmounted } from 'vue'
import { getAccessToken } from '@/api'

export type WsEvent = {
  event: string
  data: any
}

type EventHandler = (data: any) => void

export function useWebSocket() {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  const handlers = new Map<string, Set<EventHandler>>()

  function connect() {
    const token = getAccessToken()
    if (!token) return

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || location.host
    ws = new WebSocket(`${protocol}//${host}/ws?token=${token}`)

    ws.onopen = () => {
      connected.value = true
      startHeartbeat()
    }

    ws.onmessage = (event) => {
      try {
        const msg: WsEvent = JSON.parse(event.data)
        if (msg.event === 'pong') return
        const eventHandlers = handlers.get(msg.event)
        if (eventHandlers) {
          eventHandlers.forEach(fn => fn(msg.data))
        }
        // 通配符
        const allHandlers = handlers.get('*')
        if (allHandlers) {
          allHandlers.forEach(fn => fn(msg))
        }
      } catch { /* ignore */ }
    }

    ws.onclose = () => {
      connected.value = false
      stopHeartbeat()
      scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      if (getAccessToken()) connect()
    }, 3000)
  }

  function on(event: string, handler: EventHandler) {
    if (!handlers.has(event)) handlers.set(event, new Set())
    handlers.get(event)!.add(handler)
  }

  function off(event: string, handler: EventHandler) {
    handlers.get(event)?.delete(handler)
  }

  function disconnect() {
    stopHeartbeat()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws?.close()
    ws = null
  }

  onUnmounted(() => disconnect())

  return { connected, connect, disconnect, on, off }
}
