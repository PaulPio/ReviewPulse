import { Badge } from '@/components/ui/Badge'
import type { Review } from '@/types'

interface Props {
  reviews: Review[]
}

export default function ReviewsTable({ reviews }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="pb-3 text-left font-medium text-muted-foreground">Review</th>
            <th className="pb-3 text-left font-medium text-muted-foreground">Rating</th>
            <th className="pb-3 text-left font-medium text-muted-foreground">Sentiment</th>
            <th className="pb-3 text-left font-medium text-muted-foreground">Themes</th>
            <th className="pb-3 text-left font-medium text-muted-foreground">Date</th>
          </tr>
        </thead>
        <tbody>
          {reviews.map(review => (
            <tr key={review.id} className="border-b border-border last:border-0">
              <td className="py-3 pr-4 max-w-md">
                <p className="truncate">{review.summary || review.review_text.slice(0, 100)}</p>
                {review.is_actionable && (
                  <Badge variant="mixed" className="mt-1">Actionable</Badge>
                )}
                {review.is_ai_generated && (
                  <Badge variant="negative" className="mt-1 ml-1">AI Flagged</Badge>
                )}
              </td>
              <td className="py-3 pr-4">{'★'.repeat(review.rating)}</td>
              <td className="py-3 pr-4">
                {review.sentiment && (
                  <Badge variant={review.sentiment as 'positive' | 'mixed' | 'negative'}>
                    {review.sentiment}
                  </Badge>
                )}
              </td>
              <td className="py-3 pr-4">
                <div className="flex flex-wrap gap-1">
                  {review.themes.slice(0, 3).map(theme => (
                    <Badge key={theme} variant="outline">{theme}</Badge>
                  ))}
                </div>
              </td>
              <td className="py-3 text-muted-foreground whitespace-nowrap">
                {new Date(review.review_date).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
