import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import type { Book } from '@/types'

interface BookCardProps {
  book: Book
}

function dominantSentiment(book: Book): 'positive' | 'mixed' | 'negative' | null {
  const total = book.sentiment_positive + book.sentiment_mixed + book.sentiment_negative
  if (total === 0) return null
  if (book.sentiment_positive >= book.sentiment_mixed && book.sentiment_positive >= book.sentiment_negative) return 'positive'
  if (book.sentiment_negative > book.sentiment_mixed) return 'negative'
  return 'mixed'
}

export default function BookCard({ book }: BookCardProps) {
  const sentiment = dominantSentiment(book)

  return (
    <Link to={`/books/${book.id}`}>
      <Card className="transition-shadow hover:shadow-md">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-16 w-12 items-center justify-center rounded bg-primary/10 text-primary text-xs font-bold">
              {book.title.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium truncate">{book.title}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {book.total_reviews} reviews
                {book.avg_rating !== null && ` · ${book.avg_rating.toFixed(1)}★`}
              </p>
              {sentiment && (
                <div className="mt-2 flex gap-1">
                  <Badge variant={sentiment}>
                    {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
                  </Badge>
                  {book.actionable_count > 0 && (
                    <Badge variant="mixed">{book.actionable_count} actionable</Badge>
                  )}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
