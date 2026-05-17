import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { ReviewPage } from '@/types'

interface ReviewsTableProps {
  data: ReviewPage
  sentiment: string
  onSentimentChange: (v: string) => void
  isActionable: boolean | undefined
  onActionableChange: (v: boolean | undefined) => void
  isAiGenerated: boolean | undefined
  onAiGeneratedChange: (v: boolean | undefined) => void
  page: number
  onPageChange: (p: number) => void
  isFetching?: boolean
}

export default function ReviewsTable({
  data,
  sentiment,
  onSentimentChange,
  isActionable,
  onActionableChange,
  isAiGenerated,
  onAiGeneratedChange,
  page,
  onPageChange,
  isFetching,
}: Readonly<ReviewsTableProps>) {
  const { items, total, page_size, pages } = data
  const from = (page - 1) * page_size + 1
  const to   = Math.min(page * page_size, total)

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={sentiment}
          onChange={e => onSentimentChange(e.target.value)}
          className="h-8 rounded-md border border-input bg-background px-2 text-sm"
        >
          <option value="">All sentiments</option>
          <option value="positive">Positive</option>
          <option value="mixed">Mixed</option>
          <option value="negative">Negative</option>
        </select>

        <button
          type="button"
          onClick={() => onActionableChange(isActionable ? undefined : true)}
          className={
            isActionable
              ? 'rounded-full border px-3 py-1 text-xs font-medium bg-primary/10 text-primary border-primary/20'
              : 'rounded-full border px-3 py-1 text-xs font-medium bg-transparent text-muted-foreground border-border'
          }
        >
          Actionable only
        </button>

        <button
          type="button"
          onClick={() => onAiGeneratedChange(isAiGenerated ? undefined : true)}
          className={
            isAiGenerated
              ? 'rounded-full border px-3 py-1 text-xs font-medium bg-primary/10 text-primary border-primary/20'
              : 'rounded-full border px-3 py-1 text-xs font-medium bg-transparent text-muted-foreground border-border'
          }
        >
          AI flagged only
        </button>

        {total > 0 && (
          <span className="ml-auto text-xs text-muted-foreground">
            Showing {from}–{to} of {total}
          </span>
        )}
      </div>

      {/* Table */}
      <div className={`overflow-x-auto transition-opacity ${isFetching ? 'opacity-60 pointer-events-none' : ''}`}>
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
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                  No reviews match the current filters.
                </td>
              </tr>
            ) : items.map(review => (
              <tr key={review.id} className="border-b border-border last:border-0">
                <td className="py-3 pr-4 max-w-md">
                  <p className="truncate">{review.summary ?? review.body.slice(0, 100)}</p>
                  <div className="mt-1 flex gap-1">
                    {review.is_actionable && <Badge variant="mixed">Actionable</Badge>}
                    {review.is_ai_generated && <Badge variant="negative">AI Flagged</Badge>}
                  </div>
                </td>
                <td className="py-3 pr-4 whitespace-nowrap">
                  {review.rating === null ? '—' : '★'.repeat(review.rating)}
                </td>
                <td className="py-3 pr-4">
                  {review.sentiment && (
                    <Badge variant={review.sentiment}>
                      {review.sentiment}
                    </Badge>
                  )}
                </td>
                <td className="py-3 pr-4">
                  <div className="flex flex-wrap gap-1">
                    {(review.themes ?? []).slice(0, 3).map(theme => (
                      <Badge key={theme} variant="outline">{theme}</Badge>
                    ))}
                  </div>
                </td>
                <td className="py-3 text-muted-foreground whitespace-nowrap">
                  {review.review_date ? new Date(review.review_date).toLocaleDateString() : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            ← Previous
          </Button>
          <span className="text-sm text-muted-foreground">Page {page} of {pages}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
          >
            Next →
          </Button>
        </div>
      )}
    </div>
  )
}
