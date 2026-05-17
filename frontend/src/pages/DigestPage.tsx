import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react'
import { useDigest } from '@/hooks/useDigest'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import type { DigestBook } from '@/types'

const trendConfig = {
  improving: { variant: 'positive' as const, Icon: TrendingUp,  label: 'Improving ↑' },
  declining: { variant: 'negative' as const, Icon: TrendingDown, label: 'Declining ↓' },
  stable:    { variant: 'outline'  as const, Icon: Minus,        label: 'Stable' },
}

function BookDigestCard({ book }: Readonly<{ book: DigestBook }>) {
  const trend = book.overall_sentiment_trend
    ? trendConfig[book.overall_sentiment_trend]
    : null

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base">
            <Link to={`/books/${book.book_id}`} className="hover:underline">
              {book.book_title}
            </Link>
          </CardTitle>
          {trend && (
            <Badge variant={trend.variant} className="flex items-center gap-1 shrink-0">
              <trend.Icon className="h-3 w-3" />
              {trend.label}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{book.sentiment_summary}</p>

        {book.actionable_highlights.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1.5">
              Actionable highlights
            </p>
            <ul className="space-y-1">
              {book.actionable_highlights.map((highlight) => (
                <li
                  key={highlight}
                  className="border-l-2 border-yellow-400 pl-3 text-sm text-foreground"
                >
                  {highlight}
                </li>
              ))}
            </ul>
          </div>
        )}

        {book.ai_flagged_alert && (
          <div className="flex items-start gap-2 rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <p>{book.ai_flagged_alert}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function DigestPage() {
  const { data: digest, isLoading, isError } = useDigest()

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Weekly Digest</h1>
        {digest?.generated_at && (
          <p className="text-sm text-muted-foreground">
            Generated {new Date(digest.generated_at).toLocaleDateString('en', {
              weekday: 'long', month: 'short', day: 'numeric',
            })}
          </p>
        )}
      </div>

      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map(n => (
            <div key={n} className="h-48 rounded-lg border border-border bg-muted animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No digest available yet. Add books and ingest reviews to generate your weekly digest.
          </CardContent>
        </Card>
      )}

      {digest && (
        digest.books.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No digest available yet. Add books and ingest reviews to generate your weekly digest.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {digest.books.map(book => (
              <BookDigestCard key={book.book_id} book={book} />
            ))}
          </div>
        )
      )}
    </div>
  )
}
