import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const COLORS: Record<string, string> = {
  processed: "bg-emerald-100 text-emerald-800",
  answered: "bg-emerald-100 text-emerald-800",
  processing: "bg-sky-100 text-sky-800",
  open: "bg-sky-100 text-sky-800",
  skipped: "bg-neutral-100 text-neutral-700",
  escalated: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-800",
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge className={cn("font-medium", COLORS[status] ?? "bg-neutral-100 text-neutral-700")}>{status}</Badge>
}
