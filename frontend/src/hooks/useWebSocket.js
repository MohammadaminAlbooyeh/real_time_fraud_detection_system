import { useEffect, useRef, useCallback } from 'react'

const CHANNELS = ['alerts', 'transactions', 'metrics']

export default function useWebSocket(channel, onMessage) {
  const wsRef = useRef(null)
  const reconnectTimeout = useRef(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!CHANNELS.includes(channel)) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = 'localhost:8000'
    const url = `${protocol}://${host}/api/v1/ws/${channel}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current)
        reconnectTimeout.current = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (onMessage) onMessage(msg)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      if (mountedRef.current) {
        reconnectTimeout.current = setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [channel, onMessage])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  return wsRef
}
