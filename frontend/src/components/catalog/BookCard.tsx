import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { SentimentBar } from '@/components/ui/SentimentBar'
import type { Book } from '@/types'

export default function BookCard({ book }: Readonly<{ book: Book }>) {
  return (
    <Link to={`/books/${book.id}`}>
      <Card className="transition-shadow hover:shadow-md">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-16 w-12 shrink-0 items-center justify-center rounded bg-primary/10 text-primary text-sm font-bold">
              {book.title.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium truncate leading-snug">{book.title}</h3>
                {book.avg_rating !== null && (
                  <div className="flex items-baseline gap-0.5 shrink-0">
                    <span className="text-lg font-bold leading-none">{book.avg_rating.toFixed(1)}</span>
                    <span className="text-sm text-muted-foreground">★</span>
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{book.total_reviews} reviews</p>
              <div className="mt-2">
                <SentimentBar
                  positive={book.sentiment_positive}
                  mixed={book.sentiment_mixed}
                  negative={book.sentiment_negative}
                  showLabels={false}
                  height="sm"
                />
              </div>
              {book.actionable_count > 0 && (
                <div className="mt-2">
                  <Badge variant="mixed">{book.actionable_count} actionable</Badge>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
