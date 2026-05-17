const headers = () =>
  ({
    'Content-Type': 'application/json',
    'X-Dev-Author-Id': localStorage.getItem('rp_author_id') ?? '',
  }) as Record<string, string>

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    headers: { ...headers(), ...(init?.headers as object) },
  })
  if (!r.ok) {
    const t = await r.text()
    throw new Error(`${r.status}: ${t}`)
  }
  if (r.status === 204) return undefined as T
  return r.json() as Promise<T>
}

export type Book = {
  id: string
  title: string
  isbn: string | null
  asin: string | null
  catalog_url?: string | null
  created_at: string
  review_count?: number
  analyzed_count?: number
  pct_negative?: number | null
}

export type ReviewAnalysis = {
  sentiment: string
  sentiment_confidence: number
  themes: string[]
  ai_generated: boolean
  summary: string
  actionable: boolean
}

export type ReviewRow = {
  id: string
  book_id: string
  body: string
  rating: number | null
  review_date: string | null
  created_at: string
  analysis: ReviewAnalysis | null
}

export type TrendPoint = {
  period_start: string
  avg_sentiment_score: number
  review_count: number
}

export type CompareBookSummary = {
  book_id: string
  title: string
  review_count: number
  sentiment_positive_pct: number
  sentiment_mixed_pct: number
  sentiment_negative_pct: number
  top_themes: { theme: string; count: number }[]
  ai_flagged_pct: number
  reviews_per_week: number
}

export type Job = {
  id: string
  status: string
  book_id: string | null
}
