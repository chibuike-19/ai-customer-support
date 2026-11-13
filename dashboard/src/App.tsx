import { EventsTab } from "@/components/EventsTab"
import { KnowledgeBaseTab } from "@/components/KnowledgeBaseTab"
import { TicketsTab } from "@/components/TicketsTab"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { type Summary, useApi } from "@/lib/api"

function Stat({ label, value, tone = "" }: { label: string; value?: number; tone?: string }) {
  return (
    <Card className="py-4">
      <CardContent className="px-4">
        <p className="text-sm text-neutral-500">{label}</p>
        <p className={`text-2xl font-semibold ${tone}`}>{value ?? 0}</p>
      </CardContent>
    </Card>
  )
}

export default function App() {
  const { data: summary } = useApi<Summary>("/summary")

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-lg font-semibold">Three Pillars Global · Support</h1>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Answered tickets" value={summary?.tickets.answered} />
          <Stat label="Escalated tickets" value={summary?.tickets.escalated} tone="text-amber-700" />
          <Stat label="Processed emails" value={summary?.events.processed} />
          <Stat label="Failed emails" value={summary?.events.failed} tone="text-red-700" />
        </div>
        <Tabs defaultValue="tickets">
          <TabsList>
            <TabsTrigger value="tickets">Tickets</TabsTrigger>
            <TabsTrigger value="events">Events</TabsTrigger>
            <TabsTrigger value="knowledge-base">Knowledge base</TabsTrigger>
          </TabsList>
          <TabsContent value="tickets" className="mt-4">
            <TicketsTab />
          </TabsContent>
          <TabsContent value="events" className="mt-4">
            <EventsTab />
          </TabsContent>
          <TabsContent value="knowledge-base" className="mt-4">
            <KnowledgeBaseTab />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
