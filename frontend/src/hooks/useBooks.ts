import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Book } from '@/types'

export function useBooks() {
  return useQuery({
    queryKey: ['books'],
    queryFn: () => api.get<{ data: Book[] }>('/books').then(r => r.data),
  })
}

export function useBook(bookId: string) {
  return useQuery({
    queryKey: ['book', bookId],
    queryFn: () => api.get<{ data: Book }>(`/books/${bookId}`).then(r => r.data),
    enabled: !!bookId,
  })
}

export function useAddBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { title: string; isbn?: string; amazon_url?: string }) =>
      api.post<{ data: Book }>('/books', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['books'] }),
  })
}
