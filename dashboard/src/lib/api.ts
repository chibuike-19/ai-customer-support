import { useCallback, useEffect, useState } from "react"

export type EventRow = {
  id: number
  gmail_message_id: string
  status: "processing" | "processed" | "skipped" | "failed"
  attempts: number
  error: string | null
  result: Record<string, unknown> | null
  created_at: string
  processed_at: string | null
}

export type TicketRow = {
  id: number
  customer_email: string
  subject: string
  category: string | null
  status: "open" | "answered" | "escalated"
  proposed_action: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export type Message = {
  id: number
  direction: "in" | "out"
  from_address: string
  body: string
  created_at: string
}

export type TicketDetail = Omit<TicketRow, "message_count"> & { gmail_thread_id: string; messages: Message[] }

export type KnowledgeBaseEntry = {
  id: number
  section: string
  title: string
  content: string
  updated_at: string
}

export type Summary = {
  tickets: Partial<Record<TicketRow["status"], number>>
  events: Partial<Record<EventRow["status"], number>>
}

// The browser sends the Basic auth login it was given when the page loaded.
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `${response.status} ${response.statusText}`)
  }
  return response.json()
}

/** Fetch a path, refetch when it changes, and expose a reload function. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const reload = useCallback(async () => {
    if (path === null) return
    setLoading(true)
    try {
      setData(await api<T>(path))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    reload()
  }, [reload])

  return { data, error, loading, reload, setData }
}

export function formatDate(value: string | null) {
  if (!value) return "—"
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
}
