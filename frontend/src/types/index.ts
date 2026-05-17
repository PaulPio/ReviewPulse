export interface Author {
  id: string
  email: string
  display_name: string
  last_login_at: string | null
  created_at: string
}

export interface Book {
  id: string
  author_id: string
  title: string
  isbn: string | null
  asin: string | null
  amazon_url: string | null
  cover_url: string | null
  description: string | null
  published_at: string | null
  created_at: string
  updated_at: string
  // Aggregated stats from BookWithStats
  total_reviews: number
  avg_rating: number | null
  sentiment_positive: number
  sentiment_mixed: number
  sentiment_negative: number
  ai_flagged_count: number
  actionable_count: number
  last_review_at: string | null
  total_cost_usd: number
}

export interface Review {
  id: string
  book_id: string
  author_id: string
  external_id: string
  reviewer_name: string | null
  rating: number | null
  title: string | null
  body: string
  review_date: string | null
  verified_purchase: boolean
  source: string
  sentiment: 'positive' | 'mixed' | 'negative' | null
  sentiment_confidence: number | null
  themes: string[] | null
  is_ai_generated: boolean | null
  ai_generated_confidence: number | null
  summary: string | null
  is_actionable: boolean | null
  actionable_reason: string | null
  analyzed_at: string | null
  created_at: string
}

export interface ReviewPage {
  items: Review[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Job {
  id: string
  book_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'partial'
  total_reviews: number | null
  processed_reviews: number
  failed_reviews: number
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface SearchResult {
  review_id: string
  book_id: string
  book_title: string
  snippet: string
  score: number
  sentiment: string | null
  review_date: string | null
  rating: number | null
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total_searched: number
}

export interface SentimentTimeline {
  period_start: string
  positive: number
  mixed: number
  negative: number
  total: number
}

export interface ThemeCount {
  theme: string
  count: number
}

export interface WhatsNew {
  new_reviews_count: number
  since: string
  actionable_reviews: { id: string; book_id: string; summary: string | null; rating: number | null }[]
  ai_flagged_reviews: { id: string; book_id: string; summary: string | null; rating: number | null }[]
}
