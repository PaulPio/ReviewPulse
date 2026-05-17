import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Book } from '@/types'

export function useBooks() {
  return useQuery({
    queryKey: ['books'],
    queryFn: () => api.get<Book[]>('/books'),
  })
}

export function useBook(bookId: string) {
  return useQuery({
    queryKey: ['book', bookId],
    queryFn: () => api.get<Book>(`/books/${bookId}`),
    enabled: !!bookId,
  })
}

export function useAddBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { title: string; isbn?: string; amazon_url?: string }) =>
      api.post<Book>('/books', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['books'] }),
  })
}
