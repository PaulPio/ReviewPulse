export interface Author {
  id: string
  email: string
  name: string
  last_login_at: string | null
  created_at: string
}

export interface Book {
  id: string
  author_id: string
  title: string
  isbn: string | null
  amazon_url: string | null
  cover_image_url: string | null
  total_reviews: number
  avg_sentiment_score: number | null
  created_at: string
  updated_at: string
}

export interface Review {
  id: string
  book_id: string
  external_review_id: string
  reviewer_name: string | null
  rating: number
  review_text: string
  review_date: string
  sentiment: 'positive' | 'mixed' | 'negative' | null
  sentiment_confidence: number | null
  themes: string[]
  is_ai_generated: boolean | null
  ai_generated_confidence: number | null
  summary: string | null
  is_actionable: boolean | null
  analyzed_at: string | null
  created_at: string
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
  books_with_changes: { book_id: string; book_title: string; new_count: number }[]
  sentiment_shifts: { book_id: string; book_title: string; delta: number }[]
  actionable_reviews: Review[]
  ai_flagged_reviews: Review[]
}
