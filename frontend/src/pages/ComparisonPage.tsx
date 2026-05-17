import { useState } from 'react'
import { useBooks } from '@/hooks/useBooks'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import type { Book } from '@/types'

function sentimentVariant(pos: number, neg: number, total: number): 'positive' | 'mixed' | 'negative' {
  if (total === 0) return 'mixed'
  const posPct = pos / total
  const negPct = neg / total
  if (posPct >= 0.6) return 'positive'
  if (negPct >= 0.4) return 'negative'
  return 'mixed'
}

function SentimentBar({ book }: Readonly<{ book: Book }>) {
  const total = book.sentiment_positive + book.sentiment_mixed + book.sentiment_negative
  if (total === 0) return <p className="text-xs text-muted-foreground">No sentiment data</p>

  const posPct  = Math.round(book.sentiment_positive / total * 100)
  const mixPct  = Math.round(book.sentiment_mixed    / total * 100)
  const negPct  = 100 - posPct - mixPct

  return (
    <div className="space-y-1">
      <div className="flex h-2 w-full overflow-hidden rounded-full">
        <div className="bg-green-500"  style={{ width: `${posPct}%` }} />
        <div className="bg-yellow-400" style={{ width: `${mixPct}%` }} />
        <div className="bg-red-500"    style={{ width: `${negPct}%` }} />
      </div>
      <div className="flex gap-3 text-xs text-muted-foreground">
        <span className="text-green-600">{posPct}% positive</span>
        <span className="text-yellow-600">{mixPct}% mixed</span>
        <span className="text-red-600">{negPct}% negative</span>
      </div>
    </div>
  )
}

export default function ComparisonPage() {
  const { data: books } = useBooks()
  const [selected, setSelected] = useState<string[]>([])

  const toggle = (id: string) =>
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 5 ? [...prev, id] : prev
    )

  const selectedBooks = books?.filter(b => selected.includes(b.id)) ?? []

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

      {selectedBooks.length >= 2 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {selectedBooks.map(book => {
            const total = book.sentiment_positive + book.sentiment_mixed + book.sentiment_negative
            const variant = sentimentVariant(book.sentiment_positive, book.sentiment_negative, total)
            return (
              <Card key={book.id}>
                <CardHeader>
                  <CardTitle className="text-base">{book.title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm">{book.total_reviews} reviews</span>
                    {book.avg_rating !== null && (
                      <span className="text-sm font-medium">{book.avg_rating.toFixed(1)}★</span>
                    )}
                  </div>
                  <SentimentBar book={book} />
                  <div className="flex flex-wrap gap-1">
                    <Badge variant={variant}>
                      {variant.charAt(0).toUpperCase() + variant.slice(1)} overall
                    </Badge>
                    {book.actionable_count > 0 && (
                      <Badge variant="mixed">{book.actionable_count} actionable</Badge>
                    )}
                    {book.ai_flagged_count > 0 && (
                      <Badge variant="negative">{book.ai_flagged_count} AI flagged</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Select at least 2 books to compare</p>
      )}
    </div>
  )
}
