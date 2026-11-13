import { useState } from "react"
import { RefreshCw } from "lucide-react"
import { StatusBadge } from "@/components/StatusBadge"
import { StatusFilter } from "@/components/StatusFilter"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { type TicketDetail, type TicketRow, formatDate, useApi } from "@/lib/api"

function TicketSheet({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { data, error } = useApi<TicketDetail>(id === null ? null : `/tickets/${id}`)
  const ticket = data?.id === id ? data : null

  return (
    <Sheet open={id !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>{ticket?.subject || "(no subject)"}</SheetTitle>
          <SheetDescription>{ticket?.customer_email}</SheetDescription>
        </SheetHeader>
        {error && <p className="px-4 text-sm text-red-600">{error}</p>}
        {ticket && (
          <div className="space-y-4 px-4 pb-6">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <StatusBadge status={ticket.status} />
              {ticket.category && <span className="text-neutral-600">{ticket.category}</span>}
            </div>
            {ticket.proposed_action && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
                <span className="font-medium">Proposed action:</span> {ticket.proposed_action}
              </div>
            )}
            {ticket.messages.map((message) => (
              <div
                key={message.id}
                className={`rounded-md border p-3 text-sm ${message.direction === "out" ? "ml-8 bg-neutral-50" : "mr-8 bg-white"}`}
              >
                <div className="mb-2 flex justify-between gap-2 text-xs text-neutral-500">
                  <span>{message.direction === "out" ? "Our reply" : message.from_address}</span>
                  <span>{formatDate(message.created_at)}</span>
                </div>
                <p className="whitespace-pre-wrap">{message.body}</p>
              </div>
            ))}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

export function TicketsTab() {
  const [status, setStatus] = useState("all")
  const [selected, setSelected] = useState<number | null>(null)
  const { data, error, loading, reload } = useApi<TicketRow[]>(status === "all" ? "/tickets" : `/tickets?status=${status}`)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <StatusFilter value={status} onChange={setStatus} options={["open", "answered", "escalated"]} />
        <Button variant="outline" size="icon" onClick={reload} disabled={loading} aria-label="Refresh">
          <RefreshCw className={loading ? "animate-spin" : ""} />
        </Button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Updated</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Subject</TableHead>
              <TableHead>Section</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Messages</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.map((ticket) => (
              <TableRow key={ticket.id} className="cursor-pointer" onClick={() => setSelected(ticket.id)}>
                <TableCell className="whitespace-nowrap">{formatDate(ticket.updated_at)}</TableCell>
                <TableCell>{ticket.customer_email}</TableCell>
                <TableCell className="max-w-xs truncate">{ticket.subject || "(no subject)"}</TableCell>
                <TableCell className="text-neutral-600">{ticket.category ?? "—"}</TableCell>
                <TableCell>
                  <StatusBadge status={ticket.status} />
                </TableCell>
                <TableCell className="text-right">{ticket.message_count}</TableCell>
              </TableRow>
            ))}
            {data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-neutral-500">
                  No tickets yet
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <TicketSheet id={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
