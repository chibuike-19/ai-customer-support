import { Fragment, useState } from "react"
import { RefreshCw } from "lucide-react"
import { StatusBadge } from "@/components/StatusBadge"
import { StatusFilter } from "@/components/StatusFilter"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { type EventRow, formatDate, useApi } from "@/lib/api"

function summarise(event: EventRow) {
  if (event.error) return event.error
  const result = event.result ?? {}
  if (event.status === "skipped") return String(result.reason ?? "")
  if (result.action) return `${result.action} · ${result.section ?? ""}${result.proposed_action ? ` · ${result.proposed_action}` : ""}`
  return ""
}

export function EventsTab() {
  const [status, setStatus] = useState("all")
  const [open, setOpen] = useState<number | null>(null)
  const { data, error, loading, reload } = useApi<EventRow[]>(status === "all" ? "/events" : `/events?status=${status}`)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <StatusFilter value={status} onChange={setStatus} options={["processing", "processed", "skipped", "failed"]} />
        <Button variant="outline" size="icon" onClick={reload} disabled={loading} aria-label="Refresh">
          <RefreshCw className={loading ? "animate-spin" : ""} />
        </Button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Received</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Attempts</TableHead>
              <TableHead>Outcome</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.map((event) => (
              <Fragment key={event.id}>
                <TableRow className="cursor-pointer" onClick={() => setOpen(open === event.id ? null : event.id)}>
                  <TableCell className="whitespace-nowrap">{formatDate(event.created_at)}</TableCell>
                  <TableCell>
                    <StatusBadge status={event.status} />
                  </TableCell>
                  <TableCell>{event.attempts}</TableCell>
                  <TableCell className={`max-w-xl truncate ${event.error ? "text-red-700" : ""}`}>{summarise(event)}</TableCell>
                </TableRow>
                {open === event.id && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={4}>
                      <pre className="max-h-96 overflow-auto rounded bg-neutral-50 p-3 text-xs whitespace-pre-wrap">
                        {JSON.stringify({ gmail_message_id: event.gmail_message_id, error: event.error, result: event.result }, null, 2)}
                      </pre>
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            ))}
            {data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="py-8 text-center text-neutral-500">
                  No events yet
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
