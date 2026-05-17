import { BarChart3, BookOpen, LineChart, Search as SearchIcon, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  api,
  type Book,
  type CompareBookSummary,
  type Job,
  type ReviewRow,
  type TrendPoint,
} from './api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

type MainTab = 'catalog' | 'book' | 'search' | 'compare' | 'digest' | 'metrics'

type TrendsResponse = {
  book_id: string
  granularity: string
  series: TrendPoint[]
  theme_counts: { theme: string; count: number }[]
}

function sentimentBadgeVariant(s: string): 'positive' | 'mixed' | 'negative' | 'default' {
  if (s === 'positive') return 'positive'
  if (s === 'negative') return 'negative'
  if (s === 'mixed') return 'mixed'
  return 'default'
}

export default function App() {
  const [authorId, setAuthorId] = useState(() => localStorage.getItem('rp_author_id') ?? '')
  const [tab, setTab] = useState<MainTab>('catalog')
  const [books, setBooks] = useState<Book[]>([])
  const [selectedBookId, setSelectedBookId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [title, setTitle] = useState('My novel')
  const [asin, setAsin] = useState('DEMOASIN01')
  const [q, setQ] = useState('characters')
  const [searchHits, setSearchHits] = useState<
    { review_id: string; book_title: string; snippet: string; score: number }[]
  >([])
  const [compareIds, setCompareIds] = useState('')
  const [compareBooks, setCompareBooks] = useState<CompareBookSummary[]>([])
  const [digestHtml, setDigestHtml] = useState<string | null>(null)
  const [digestBook, setDigestBook] = useState('')
  const [metrics, setMetrics] = useState<string>('')
  const [whatsNew, setWhatsNew] = useState<string>('')
  const [bookTrends, setBookTrends] = useState<TrendsResponse | null>(null)
  const [bookReviews, setBookReviews] = useState<ReviewRow[]>([])
  const [revSentiment, setRevSentiment] = useState('')

  const persistAuthor = (id: string) => {
    localStorage.setItem('rp_author_id', id)
    setAuthorId(id)
  }

  const refreshBooks = useCallback(async () => {
    if (!authorId) return
    setError(null)
    const list = await api<Book[]>('/api/v1/books')
    setBooks(list)
  }, [authorId])

  useEffect(() => {
    if (authorId) void refreshBooks().catch((e: Error) => setError(e.message))
  }, [authorId, refreshBooks])

  useEffect(() => {
    if (tab !== 'book' || !selectedBookId || !authorId) return
    const load = async () => {
      setError(null)
      try {
        const t = await api<TrendsResponse>(`/api/v1/books/${selectedBookId}/trends`)
        setBookTrends(t)
        const qs = revSentiment ? `?sentiment=${encodeURIComponent(revSentiment)}&page=1&page_size=15` : '?page=1&page_size=15'
        const r = await api<{ items: ReviewRow[] }>(`/api/v1/books/${selectedBookId}/reviews${qs}`)
        setBookReviews(r.items)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load book')
      }
    }
    void load()
  }, [tab, selectedBookId, authorId, revSentiment])

  async function pingSession() {
    await api('/api/v1/session/ping', { method: 'POST', body: '{}' })
  }

  async function loadFeed() {
    const items = await api<
      { book_title: string; summary: string; sentiment: string; score: number }[]
    >('/api/v1/feed/whats-new')
    setWhatsNew(
      items.length
        ? items.map((i) => `• ${i.book_title}: ${i.summary} (${i.sentiment})`).join('\n')
        : 'Nothing new in this window.',
    )
  }

  async function createDevAuthor(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const a = await api<{ id: string }>('/api/v1/auth/dev-authors', {
        method: 'POST',
        body: JSON.stringify({ display_name: 'Local author' }),
      })
      persistAuthor(a.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function addBook(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api('/api/v1/books', {
        method: 'POST',
        body: JSON.stringify({ title, asin: asin || null, isbn: null, catalog_url: null }),
      })
      await refreshBooks()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function ingestBook(bookId: string) {
    setBusy(true)
    setError(null)
    try {
      const job = await api<Job>(`/api/v1/books/${bookId}/ingest`, {
        method: 'POST',
        headers: { 'Idempotency-Key': `ui-${bookId}-${Date.now()}` },
      })
      alert(`Ingest job queued (${job.id.slice(0, 8)}…). Run Celery worker to process.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function runSearch(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const r = await api<{ items: typeof searchHits }>('/api/v1/search', {
        method: 'POST',
        body: JSON.stringify({ query: q, limit: 10 }),
      })
      setSearchHits(r.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function runCompare(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const ids = compareIds
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      const r = await api<{ books: CompareBookSummary[] }>('/api/v1/compare', {
        method: 'POST',
        body: JSON.stringify({ book_ids: ids }),
      })
      setCompareBooks(r.books)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function loadDigest(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const r = await api<{ html: string }>(`/api/v1/books/${digestBook}/digest`)
      setDigestHtml(r.html)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function downloadExportCsv(bookId: string) {
    setBusy(true)
    setError(null)
    try {
      const r = await fetch(`/api/v1/books/${bookId}/export.csv`, {
        headers: { 'X-Dev-Author-Id': localStorage.getItem('rp_author_id') ?? '' },
      })
      if (!r.ok) throw new Error(await r.text())
      const blob = await r.blob()
      const u = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = u
      a.download = `book-${bookId.slice(0, 8)}-quotes.csv`
      a.click()
      URL.revokeObjectURL(u)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed')
    } finally {
      setBusy(false)
    }
  }

  async function loadMetrics() {
    setBusy(true)
    setError(null)
    try {
      const m = await api<{
        total_estimated_cost_usd: number
        total_prompt_tokens: number
        by_book: Record<string, number>
      }>('/api/v1/metrics/summary')
      setMetrics(
        `Total ~$${m.total_estimated_cost_usd.toFixed(4)} · ${m.total_prompt_tokens} prompt tok · ` +
          Object.entries(m.by_book)
            .map(([k, v]) => `${k}: $${v.toFixed(4)}`)
            .join(', '),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  if (!authorId) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center p-6">
        <Card className="max-w-md w-full border-zinc-800 bg-zinc-900/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Sparkles className="size-5 text-violet-400" />
              ReviewPulse
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-zinc-400">
              Create a local author (dev) or paste an existing author UUID and press Continue.
            </p>
            <form onSubmit={createDevAuthor}>
              <Button type="submit" disabled={busy} className="w-full">
                Create dev author
              </Button>
            </form>
            <div className="flex gap-2">
              <Input
                className="flex-1 font-mono text-xs"
                placeholder="Author UUID"
                onChange={(e) => setAuthorId(e.target.value)}
                value={authorId}
              />
              <Button type="button" variant="outline" onClick={() => authorId && persistAuthor(authorId)}>
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const selectedBook = books.find((b) => b.id === selectedBookId)

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-6 py-4 flex flex-wrap gap-4 items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            <BookOpen className="size-5 text-violet-400" />
            ReviewPulse
          </h1>
          <p className="text-xs text-zinc-500 font-mono mt-0.5">author {authorId.slice(0, 8)}…</p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm items-center">
          <Button type="button" variant="outline" size="sm" onClick={() => void pingSession().catch(() => {})}>
            Ping session
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => void loadFeed()}>
            What&apos;s new
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6">
        <Tabs value={tab} onValueChange={(v) => setTab(v as MainTab)} className="w-full">
          <TabsList className="flex flex-wrap h-auto min-h-9 gap-1 w-full max-w-full justify-start">
            <TabsTrigger value="catalog" className="gap-1">
              <LineChart className="size-3.5 opacity-70" />
              Catalog
            </TabsTrigger>
            <TabsTrigger value="book" className="gap-1" disabled={!selectedBookId}>
              <BookOpen className="size-3.5 opacity-70" />
              Book
            </TabsTrigger>
            <TabsTrigger value="search" className="gap-1">
              <SearchIcon className="size-3.5 opacity-70" />
              Search
            </TabsTrigger>
            <TabsTrigger value="compare" className="gap-1">
              <BarChart3 className="size-3.5 opacity-70" />
              Compare
            </TabsTrigger>
            <TabsTrigger value="digest">Digest</TabsTrigger>
            <TabsTrigger value="metrics">Spend</TabsTrigger>
          </TabsList>

          {error && (
            <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}
          {whatsNew && (
            <pre className="mt-4 text-xs whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
              {whatsNew}
            </pre>
          )}

          <TabsContent value="catalog">
            <div className="grid md:grid-cols-2 gap-8 mt-2">
              <Card>
                <CardHeader>
                  <CardTitle>Add book</CardTitle>
                  <p className="text-sm text-zinc-400 font-normal">
                    Use ASIN matching <code className="text-violet-300">sample_reviews.json</code> (e.g. DEMOASIN01).
                  </p>
                </CardHeader>
                <CardContent>
                  <form onSubmit={addBook} className="space-y-2">
                    <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" />
                    <Input value={asin} onChange={(e) => setAsin(e.target.value)} placeholder="ASIN" />
                    <Button type="submit" disabled={busy}>
                      Save book
                    </Button>
                  </form>
                </CardContent>
              </Card>
              <div className="space-y-3">
                <h2 className="text-lg font-medium">Catalog</h2>
                <ul className="space-y-2">
                  {books.map((b) => (
                    <li key={b.id}>
                      <Card>
                        <CardContent className="py-4 flex items-center justify-between gap-4">
                          <div className="min-w-0">
                            <div className="font-medium truncate">{b.title}</div>
                            <div className="text-xs text-zinc-500 font-mono">{b.asin ?? '—'}</div>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              <Badge variant="default">{b.review_count ?? 0} reviews</Badge>
                              {b.analyzed_count ? (
                                <Badge variant="default">{b.analyzed_count} analyzed</Badge>
                              ) : null}
                              {b.pct_negative != null ? (
                                <Badge variant="negative">{b.pct_negative.toFixed(0)}% neg</Badge>
                              ) : null}
                            </div>
                          </div>
                          <div className="flex flex-col gap-1.5 shrink-0">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedBookId(b.id)
                                setTab('book')
                              }}
                            >
                              Open
                            </Button>
                            <Button type="button" size="sm" onClick={() => void ingestBook(b.id)}>
                              Ingest
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </li>
                  ))}
                  {books.length === 0 && <p className="text-sm text-zinc-500">No books yet.</p>}
                </ul>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="book">
            {!selectedBookId || !selectedBook ? (
              <p className="text-sm text-zinc-500 mt-4">Select a book from Catalog → Open.</p>
            ) : (
              <div className="space-y-6 mt-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-lg font-semibold">{selectedBook.title}</h2>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void downloadExportCsv(selectedBookId)}
                  >
                    Export themed CSV
                  </Button>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Trends (weekly)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {bookTrends && bookTrends.series.length > 0 ? (
                      <ul className="text-sm space-y-2">
                        {bookTrends.series.slice(-8).map((p) => (
                          <li key={p.period_start} className="flex justify-between gap-4 border-b border-zinc-800/80 pb-2">
                            <span className="text-zinc-400">{p.period_start}</span>
                            <span>
                              avg score {p.avg_sentiment_score.toFixed(2)} · {p.review_count} reviews
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-zinc-500">No trend data yet — ingest reviews first.</p>
                    )}
                    {bookTrends && bookTrends.theme_counts.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 mt-4">
                        {bookTrends.theme_counts.map((t) => (
                          <Badge key={t.theme} variant="default">
                            {t.theme} ({t.count})
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Reviews</CardTitle>
                    <div className="flex gap-2 pt-2">
                      <select
                        className="h-9 rounded-lg border border-zinc-700 bg-zinc-900 px-2 text-sm"
                        value={revSentiment}
                        onChange={(e) => setRevSentiment(e.target.value)}
                      >
                        <option value="">All sentiments</option>
                        <option value="positive">positive</option>
                        <option value="mixed">mixed</option>
                        <option value="negative">negative</option>
                      </select>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {bookReviews.length === 0 ? (
                      <p className="text-sm text-zinc-500">No reviews match filters.</p>
                    ) : (
                      bookReviews.map((r) => (
                        <div key={r.id} className="rounded-lg border border-zinc-800 p-3 text-sm space-y-2">
                          <div className="flex flex-wrap gap-1.5 items-center">
                            {r.analysis ? (
                              <Badge variant={sentimentBadgeVariant(r.analysis.sentiment)}>
                                {r.analysis.sentiment}
                              </Badge>
                            ) : (
                              <Badge>pending analysis</Badge>
                            )}
                            {r.rating != null ? <Badge variant="default">{r.rating}★</Badge> : null}
                            {r.analysis?.actionable ? <Badge variant="mixed">actionable</Badge> : null}
                            {r.analysis?.ai_generated ? <Badge variant="negative">AI-flagged</Badge> : null}
                          </div>
                          <p className="text-zinc-200">{r.body}</p>
                          {r.analysis?.themes?.length ? (
                            <div className="flex flex-wrap gap-1">
                              {r.analysis.themes.map((t) => (
                                <span key={t} className="text-xs text-violet-300">
                                  #{t}
                                </span>
                              ))}
                            </div>
                          ) : null}
                          {r.analysis?.summary ? (
                            <p className="text-xs text-zinc-500 border-t border-zinc-800 pt-2">{r.analysis.summary}</p>
                          ) : null}
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          <TabsContent value="search">
            <Card className="mt-2">
              <CardHeader>
                <CardTitle>Semantic search</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={runSearch} className="flex gap-2">
                  <Input className="flex-1" value={q} onChange={(e) => setQ(e.target.value)} />
                  <Button type="submit" disabled={busy}>
                    Search
                  </Button>
                </form>
                <ul className="space-y-2">
                  {searchHits.map((h) => (
                    <li key={h.review_id} className="rounded-lg border border-zinc-800 p-3 text-sm">
                      <div className="text-xs text-zinc-500 mb-1">{h.book_title}</div>
                      <div>{h.snippet}</div>
                      <div className="text-xs text-zinc-500 mt-1">score {h.score.toFixed(3)}</div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="compare">
            <Card className="mt-2">
              <CardHeader>
                <CardTitle>Compare books</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={runCompare} className="space-y-2">
                  <Input
                    className="font-mono text-sm"
                    placeholder="comma-separated book UUIDs"
                    value={compareIds}
                    onChange={(e) => setCompareIds(e.target.value)}
                  />
                  <Button type="submit" disabled={busy}>
                    Compare
                  </Button>
                </form>
                <div className="grid sm:grid-cols-2 gap-3">
                  {compareBooks.map((b) => (
                    <Card key={b.book_id} className="border-zinc-800">
                      <CardHeader className="py-3">
                        <CardTitle className="text-sm font-medium">{b.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="text-sm space-y-2">
                        <div>{b.review_count} reviews · {b.reviews_per_week.toFixed(1)} / wk</div>
                        <div className="flex gap-2 text-xs">
                          <Badge variant="positive">{b.sentiment_positive_pct.toFixed(0)}% +</Badge>
                          <Badge variant="mixed">{b.sentiment_mixed_pct.toFixed(0)}% ~</Badge>
                          <Badge variant="negative">{b.sentiment_negative_pct.toFixed(0)}% −</Badge>
                        </div>
                        <div className="text-xs text-zinc-500">AI-flagged {b.ai_flagged_pct.toFixed(0)}%</div>
                        {b.top_themes.length > 0 ? (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {b.top_themes.map((t) => (
                              <Badge key={t.theme} variant="default">
                                {t.theme} ({t.count})
                              </Badge>
                            ))}
                          </div>
                        ) : null}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="digest">
            <Card className="mt-2">
              <CardHeader>
                <CardTitle>Weekly digest preview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={loadDigest} className="flex gap-2">
                  <Input
                    className="flex-1 font-mono text-sm"
                    placeholder="Book UUID"
                    value={digestBook}
                    onChange={(e) => setDigestBook(e.target.value)}
                  />
                  <Button type="submit" disabled={busy}>
                    Render
                  </Button>
                </form>
                {digestHtml && (
                  <div
                    className="prose prose-invert max-w-none rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 text-sm"
                    dangerouslySetInnerHTML={{ __html: digestHtml }}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="metrics">
            <Card className="mt-2">
              <CardHeader>
                <CardTitle>LLM spend (estimated)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button type="button" onClick={() => void loadMetrics()}>
                  Refresh
                </Button>
                {metrics && <p className="text-sm text-zinc-300">{metrics}</p>}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
