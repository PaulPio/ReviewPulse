import { useState } from 'react'
import { useBooks } from '@/hooks/useBooks'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

export default function ComparisonPage() {
  const { data: books } = useBooks()
  const [selected, setSelected] = useState<string[]>([])

  const toggle = (id: string) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 5 ? [...prev, id] : prev
    )
  }

  const selectedBooks = books?.filter(b => selected.includes(b.id)) || []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Compare Books</h1>

      <div className="flex flex-wrap gap-2">
        {books?.map(book => (
          <Button
            key={book.id}
            variant={selected.includes(book.id) ? 'default' : 'outline'}
            size="sm"
            onClick={() => toggle(book.id)}
          >
            {book.title}
          </Button>
        ))}
      </div>

      {selectedBooks.length >= 2 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {selectedBooks.map(book => (
            <Card key={book.id}>
              <CardHeader>
                <CardTitle className="text-base">{book.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">{book.total_reviews} reviews</p>
                {book.avg_sentiment_score !== null && (
                  <Badge variant={book.avg_sentiment_score > 0.6 ? 'positive' : book.avg_sentiment_score > 0.4 ? 'mixed' : 'negative'}>
                    Sentiment: {Math.round(book.avg_sentiment_score * 100)}%
                  </Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {selectedBooks.length < 2 && (
        <p className="text-sm text-muted-foreground">Select at least 2 books to compare</p>
      )}
    </div>
  )
}
