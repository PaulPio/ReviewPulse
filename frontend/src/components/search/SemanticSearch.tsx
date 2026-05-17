import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { ScoreBar } from '@/components/ui/ScoreBar'
import { useSemanticSearch } from '@/hooks/useSearch'
import { Search } from 'lucide-react'

const sentimentDot: Record<string, string> = {
  positive: 'bg-green-500',
  mixed:    'bg-yellow-400',
  negative: 'bg-red-500',
}

export default function SemanticSearch() {
  const [query, setQuery] = useState('')
  const search = useSemanticSearch()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      search.mutate({ query: query.trim(), top_k: 10 })
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSearch} className="flex gap-2">
        <Input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search reviews using natural language… e.g. 'pacing issues in the middle chapters'"
          className="flex-1"
        />
        <Button type="submit" disabled={search.isPending}>
          <Search className="mr-2 h-4 w-4" />
          Search
        </Button>
      </form>

      {search.isPending && (
        <p className="text-sm text-muted-foreground">Searching…</p>
      )}

      {search.data && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {search.data.total_searched.toLocaleString()} reviews searched — {search.data.results.length} results
          </p>

          {search.data.results.length === 0 && (
            <p className="text-sm text-muted-foreground">No matching reviews found.</p>
          )}

          {search.data.results.map(result => (
            <Card key={result.review_id}>
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2 min-w-0">
                    <Link
                      to={`/books/${result.book_id}`}
                      className="text-sm font-medium hover:underline truncate"
                    >
                      {result.book_title}
                    </Link>
                    {result.sentiment && (
                      <span
                        className={`h-2 w-2 rounded-full shrink-0 ${sentimentDot[result.sentiment] ?? 'bg-muted'}`}
                        title={result.sentiment}
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                    {result.rating !== null && <span>{'★'.repeat(result.rating)}</span>}
                    {result.review_date && (
                      <span>{new Date(result.review_date).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>

                <p className="text-sm text-foreground">{result.snippet}</p>

                <ScoreBar score={result.score} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
