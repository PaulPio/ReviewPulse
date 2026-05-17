import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Star, TrendingUp, Zap, Bot, ArrowLeft } from 'lucide-react'
import { useBook } from '@/hooks/useBooks'
import { useReviews, useSentimentTimeline, useThemeBreakdown } from '@/hooks/useReviews'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { StatTile } from '@/components/ui/StatTile'
import SentimentTimeline from '@/components/book-detail/SentimentTimeline'
import ThemeBreakdown from '@/components/book-detail/ThemeBreakdown'
import ReviewsTable from '@/components/book-detail/ReviewsTable'

export default function BookDetailPage() {
  const { bookId } = useParams<{ bookId: string }>()

  const [sentimentFilter, setSentimentFilter]   = useState<string>('')
  const [actionableFilter, setActionableFilter] = useState<boolean | undefined>()
  const [aiFilter, setAiFilter]                 = useState<boolean | undefined>()
  const [page, setPage]                         = useState(1)

  const handleSentimentChange  = (v: string)            => { setSentimentFilter(v); setPage(1) }
  const handleActionableChange = (v: boolean | undefined) => { setActionableFilter(v); setPage(1) }
  const handleAiChange         = (v: boolean | undefined) => { setAiFilter(v); setPage(1) }

  const { data: book, isLoading } = useBook(bookId!)
  const { data: reviewsData, isFetching: reviewsFetching } = useReviews({
    bookId: bookId!,
    sentiment:      sentimentFilter   || undefined,
    is_actionable:  actionableFilter,
    is_ai_generated: aiFilter,
    page,
    per_page: 20,
  })
  const { data: timeline } = useSentimentTimeline(bookId!)
  const { data: themes }   = useThemeBreakdown(bookId!)

  if (isLoading)          return <p className="text-muted-foreground">Loading…</p>
  if (book === undefined) return <p>Book not found</p>

  const total    = book.sentiment_positive + book.sentiment_mixed + book.sentiment_negative
  const posPct   = Math.round((book.sentiment_positive / (total || 1)) * 100)

  const emptyPage = { items: [], total: 0, page: 1, page_size: 20, pages: 0 }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2">
          <ArrowLeft className="h-3 w-3" /> All books
        </Link>
        <h1 className="text-2xl font-semibold">{book.title}</h1>
        <p className="text-sm text-muted-foreground mt-0.5">{book.total_reviews} reviews analyzed</p>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile
          label="Avg Rating"
          value={book.avg_rating !== null ? `${book.avg_rating.toFixed(1)} ★` : '—'}
          icon={<Star className="h-4 w-4" />}
          variant="default"
        />
        <StatTile
          label="Positive"
          value={`${posPct}%`}
          sub={`${book.sentiment_positive} reviews`}
          icon={<TrendingUp className="h-4 w-4" />}
          variant="positive"
        />
        <StatTile
          label="Actionable"
          value={book.actionable_count}
          icon={<Zap className="h-4 w-4" />}
          variant={book.actionable_count > 0 ? 'warning' : 'default'}
        />
        <StatTile
          label="AI Flagged"
          value={book.ai_flagged_count}
          icon={<Bot className="h-4 w-4" />}
          variant={book.ai_flagged_count > 0 ? 'negative' : 'default'}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-[3fr_2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            {timeline && timeline.length > 0 ? (
              <SentimentTimeline data={timeline} />
            ) : (
              <p className="text-sm text-muted-foreground">Not enough data yet</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Theme Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {themes && themes.length > 0 ? (
              <ThemeBreakdown data={themes} />
            ) : (
              <p className="text-sm text-muted-foreground">No themes detected yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Reviews */}
      <Card>
        <CardHeader>
          <CardTitle>Reviews</CardTitle>
        </CardHeader>
        <CardContent>
          <ReviewsTable
            data={reviewsData ?? emptyPage}
            sentiment={sentimentFilter}
            onSentimentChange={handleSentimentChange}
            isActionable={actionableFilter}
            onActionableChange={handleActionableChange}
            isAiGenerated={aiFilter}
            onAiGeneratedChange={handleAiChange}
            page={page}
            onPageChange={setPage}
            isFetching={reviewsFetching}
          />
        </CardContent>
      </Card>
    </div>
  )
}
