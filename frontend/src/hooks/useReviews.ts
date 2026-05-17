import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ReviewPage, SentimentTimeline, ThemeCount } from '@/types'

interface ReviewsParams {
  bookId: string
  sentiment?: string
  is_actionable?: boolean
  is_ai_generated?: boolean
  theme?: string
  page?: number
  per_page?: number
}

export function useReviews(params: ReviewsParams) {
  const { bookId, ...filters } = params
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined) query.set(k, String(v))
  })

  return useQuery({
    queryKey: ['reviews', bookId, filters],
    queryFn: () => api.get<ReviewPage>(`/books/${bookId}/reviews?${query.toString()}`),
    enabled: !!bookId,
  })
}

export function useSentimentTimeline(bookId: string) {
  return useQuery({
    queryKey: ['sentiment-timeline', bookId],
    queryFn: () =>
      api.get<{ data: SentimentTimeline[] }>(`/books/${bookId}/trends`).then(r => r.data),
    enabled: !!bookId,
  })
}

export function useThemeBreakdown(bookId: string) {
  return useQuery({
    queryKey: ['theme-breakdown', bookId],
    queryFn: () =>
      api.get<{ data: ThemeCount[] }>(`/books/${bookId}/trends/themes`).then(r => r.data),
    enabled: !!bookId,
  })
}
