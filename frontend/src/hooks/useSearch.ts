import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SearchResult } from '@/types'

export function useSemanticSearch() {
  return useMutation({
    mutationFn: (params: { query: string; top_k?: number; book_ids?: string[] }) =>
      api.post<{ data: { results: SearchResult[] } }>('/search', params).then(r => r.data),
  })
}
