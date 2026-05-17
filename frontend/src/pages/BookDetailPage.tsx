import { useParams } from 'react-router-dom'
import { useBook } from '@/hooks/useBooks'
import { useReviews, useSentimentTimeline, useThemeBreakdown } from '@/hooks/useReviews'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import SentimentTimeline from '@/components/book-detail/SentimentTimeline'
import ThemeBreakdown from '@/components/book-detail/ThemeBreakdown'
import ReviewsTable from '@/components/book-detail/ReviewsTable'

export default function BookDetailPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const { data: book, isLoading } = useBook(bookId!)
  const { data: reviewsData } = useReviews({ bookId: bookId!, per_page: 20 })
  const { data: timeline } = useSentimentTimeline(bookId!)
  const { data: themes } = useThemeBreakdown(bookId!)

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (!book) return <p>Book not found</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{book.title}</h1>
        <p className="text-sm text-muted-foreground mt-1">{book.total_reviews} reviews analyzed</p>
      </div>

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

      <Card>
        <CardHeader>
          <CardTitle>Reviews</CardTitle>
        </CardHeader>
        <CardContent>
          {reviewsData?.data && reviewsData.data.length > 0 ? (
            <ReviewsTable reviews={reviewsData.data} />
          ) : (
            <p className="text-sm text-muted-foreground">No reviews yet</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
