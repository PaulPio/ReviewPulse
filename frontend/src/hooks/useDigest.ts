import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { DigestResponse } from '@/types'

export function useDigest() {
  return useQuery({
    queryKey: ['digest'],
    queryFn: () => api.get<DigestResponse>('/digest'),
  })
}
