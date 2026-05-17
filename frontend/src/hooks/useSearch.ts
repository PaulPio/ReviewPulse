import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SearchResponse } from '@/types'

export function useSemanticSearch() {
  return useMutation({
    mutationFn: (params: { query: string; top_k?: number; book_ids?: string[] }) =>
      api.post<SearchResponse>('/search', params),
  })
}
