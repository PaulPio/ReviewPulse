import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'

export default function DigestPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['digest'],
    queryFn: () => api.get<{ data: { summary: string; highlights: string[] } }>('/digest'),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Weekly Digest</h1>
      <Card>
        <CardHeader>
          <CardTitle>This Week's Summary</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading digest...</p>
          ) : data?.data ? (
            <div className="space-y-4">
              <p className="text-sm">{data.data.summary}</p>
              {data.data.highlights?.length > 0 && (
                <ul className="list-disc pl-5 space-y-1">
                  {data.data.highlights.map((h, i) => (
                    <li key={i} className="text-sm">{h}</li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No digest available yet. Add books and ingest reviews to generate your weekly digest.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
