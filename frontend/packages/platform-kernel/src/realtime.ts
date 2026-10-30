"use client"
import { useEffect, useRef } from 'react'
import { io, type Socket } from 'socket.io-client'
import type { RealtimeEvent, RealtimeEventHandler } from '@ai-video-studio/shared-types'
import { useAuthStore } from './stores/auth-store'

class RealtimeProviderImpl {
  private socket: Socket | null = null
  private handlers = new Map<string, Set<RealtimeEventHandler>>()
  private wsUrl: string = ''
  private connected = false

  connect(wsUrl: string, token: string | null): void {
    this.wsUrl = wsUrl
    if (this.socket?.connected) {
      this.disconnect()
    }

    this.socket = io(wsUrl, {
      auth: { token },
      transports: ['websocket'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 3,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    })

    this.socket.on('connect', () => {
      this.connected = true
      this.emit({ type: 'realtime:connected', payload: {} })
    })

    this.socket.on('disconnect', () => {
      this.connected = false
      this.emit({ type: 'realtime:disconnected', payload: {} })
    })

    this.socket.on('connect_error', () => {
      this.connected = false
    })

    this.socket.on('error', (error: unknown) => {
      this.emit({ type: 'realtime:error', payload: { error } })
    })

    this.socket.onAny((eventName: string, ...args: unknown[]) => {
      this.emit({ type: eventName, payload: args[0] ?? {} })
    })
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.connected = false
    }
  }

  on(eventType: string, handler: RealtimeEventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set())
    }
    this.handlers.get(eventType)!.add(handler)
    return () => {
      this.handlers.get(eventType)?.delete(handler)
    }
  }

  off(eventType: string, handler?: RealtimeEventHandler): void {
    if (handler) {
      this.handlers.get(eventType)?.delete(handler)
    } else {
      this.handlers.delete(eventType)
    }
  }

  emit(event: RealtimeEvent): void {
    const handlers = this.handlers.get(event.type)
    handlers?.forEach((h) => h(event))
  }

  send(event: string, data: unknown): void {
    if (this.socket?.connected) {
      this.socket.emit(event, data)
    }
  }

  isConnected(): boolean {
    return this.connected
  }
}

export const realtimeProvider = new RealtimeProviderImpl()

export function useRealtimeEvent(
  eventType: string,
  handler: RealtimeEventHandler
): void {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    const unsubscribe = realtimeProvider.on(eventType, (event) => {
      handlerRef.current(event)
    })
    return unsubscribe
  }, [eventType])
}

export function useRealtimeConnection(wsUrl: string): void {
  const token = useAuthStore((s) => s.accessToken)

  useEffect(() => {
    if (token) {
      realtimeProvider.connect(wsUrl, token)
    }
    return () => {
      realtimeProvider.disconnect()
    }
  }, [wsUrl, token])
}
