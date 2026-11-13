import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { type KnowledgeBaseEntry, api, formatDate, useApi } from "@/lib/api"

function EntryCard({ entry, onSaved }: { entry: KnowledgeBaseEntry; onSaved: (entry: KnowledgeBaseEntry) => void }) {
  const [draft, setDraft] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save() {
    if (draft === null) return
    setSaving(true)
    try {
      onSaved(await api<KnowledgeBaseEntry>(`/knowledge-base/${entry.id}`, { method: "PUT", body: JSON.stringify({ content: draft }) }))
      setDraft(null)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="gap-3 py-4">
      <CardHeader className="flex flex-row items-start justify-between gap-4 px-4">
        <div>
          <CardTitle className="text-base">{entry.title}</CardTitle>
          <p className="mt-1 text-xs text-neutral-500">Updated {formatDate(entry.updated_at)}</p>
        </div>
        {draft === null ? (
          <Button variant="outline" size="sm" onClick={() => setDraft(entry.content)}>
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setDraft(null)} disabled={saving}>
              Cancel
            </Button>
            <Button size="sm" onClick={save} disabled={saving || draft.trim() === entry.content}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent className="px-4">
        {draft === null ? (
          <p className="text-sm whitespace-pre-wrap text-neutral-700">{entry.content}</p>
        ) : (
          <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} className="min-h-48 font-mono text-sm" />
        )}
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </CardContent>
    </Card>
  )
}

export function KnowledgeBaseTab() {
  const { data, error, setData } = useApi<KnowledgeBaseEntry[]>("/knowledge-base")
  const [search, setSearch] = useState("")
  const [section, setSection] = useState<string | null>(null)

  const sections = useMemo(() => [...new Set(data?.map((entry) => entry.section))], [data])
  const current = section ?? sections[0]
  const query = search.trim().toLowerCase()
  const entries = (data ?? []).filter((entry) =>
    query
      ? `${entry.title}\n${entry.content}`.toLowerCase().includes(query)
      : entry.section === current,
  )

  function saved(updated: KnowledgeBaseEntry) {
    setData((rows) => rows?.map((row) => (row.id === updated.id ? updated : row)) ?? null)
  }

  return (
    <div className="grid gap-6 md:grid-cols-[220px_1fr]">
      <nav className="space-y-1">
        <Input placeholder="Search all sections" value={search} onChange={(e) => setSearch(e.target.value)} className="mb-3 bg-white" />
        {sections.map((name) => (
          <button
            key={name}
            onClick={() => {
              setSection(name)
              setSearch("")
            }}
            className={`block w-full rounded-md px-3 py-2 text-left text-sm ${!query && name === current ? "bg-neutral-900 text-white" : "hover:bg-neutral-100"}`}
          >
            {name}
          </button>
        ))}
      </nav>
      <div className="space-y-3">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <p className="text-xs text-neutral-500">
          Edits apply to the next email straight away. Running scripts/seed_knowledge_base.py overwrites them with the markdown files.
        </p>
        {entries.map((entry) => (
          <div key={entry.id}>
            {query && <p className="mb-1 text-xs text-neutral-500">{entry.section}</p>}
            <EntryCard entry={entry} onSaved={saved} />
          </div>
        ))}
      </div>
    </div>
  )
}
