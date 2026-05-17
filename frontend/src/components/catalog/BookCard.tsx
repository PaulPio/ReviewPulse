import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import type { Book } from '@/types'

interface BookCardProps {
  book: Book
}

export default function BookCard({ book }: BookCardProps) {
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
              </p>
              {book.avg_sentiment_score !== null && (
                <div className="mt-2 flex gap-1">
                  <Badge variant={book.avg_sentiment_score > 0.6 ? 'positive' : book.avg_sentiment_score > 0.4 ? 'mixed' : 'negative'}>
                    {book.avg_sentiment_score > 0.6 ? 'Positive' : book.avg_sentiment_score > 0.4 ? 'Mixed' : 'Negative'}
                  </Badge>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
