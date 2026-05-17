import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { useSemanticSearch } from '@/hooks/useSearch'
import { Search } from 'lucide-react'

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
          placeholder="Search reviews semantically... e.g. 'pacing issues in the middle chapters'"
          className="flex-1"
        />
        <Button type="submit" disabled={search.isPending}>
          <Search className="mr-2 h-4 w-4" />
          Search
        </Button>
      </form>

      {search.isPending && <p className="text-sm text-muted-foreground">Searching...</p>}

      {search.data?.results && (
        <div className="space-y-3">
          {search.data.results.map(result => (
            <Card key={result.review_id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="default">{result.book_title}</Badge>
                      {result.sentiment && (
                        <Badge variant={result.sentiment as 'positive' | 'mixed' | 'negative'}>
                          {result.sentiment}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm">{result.snippet}</p>
                  </div>
                  <span className="text-sm font-medium text-primary whitespace-nowrap">
                    {Math.round(result.score * 100)}% match
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
