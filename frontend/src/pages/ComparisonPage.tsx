import { useState } from 'react'
import { useBooks } from '@/hooks/useBooks'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { SentimentBar } from '@/components/ui/SentimentBar'
import type { Book } from '@/types'

function sentimentVariant(pos: number, neg: number, total: number): 'positive' | 'mixed' | 'negative' {
  if (total === 0) return 'mixed'
  if (pos / total >= 0.6) return 'positive'
  if (neg / total >= 0.4) return 'negative'
  return 'mixed'
}

function pct(n: number, total: number) {
  return total === 0 ? 0 : Math.round((n / total) * 100)
}

function ComparisonTable({ books }: Readonly<{ books: Book[] }>) {
  type RowDef = {
    label: string
    getNum: (b: Book) => number
    render?: (num: number) => React.ReactNode
  }

  const rows: RowDef[] = [
    { label: 'Total Reviews', getNum: b => b.total_reviews },
    {
      label: 'Avg Rating',
      getNum: b => b.avg_rating ?? -1,
      render: n => n < 0 ? '—' : `${n.toFixed(1)} ★`,
    },
    {
      label: 'Positive %',
      getNum: b => pct(b.sentiment_positive, b.sentiment_positive + b.sentiment_mixed + b.sentiment_negative),
      render: n => (
        <span className="flex items-center gap-2">
          <span>{n}%</span>
          <span className="h-1.5 rounded-full bg-green-500 inline-block" style={{ width: `${n}px` }} />
        </span>
      ),
    },
    {
      label: 'Mixed %',
      getNum: b => pct(b.sentiment_mixed, b.sentiment_positive + b.sentiment_mixed + b.sentiment_negative),
      render: n => (
        <span className="flex items-center gap-2">
          <span>{n}%</span>
          <span className="h-1.5 rounded-full bg-yellow-400 inline-block" style={{ width: `${n}px` }} />
        </span>
      ),
    },
    {
      label: 'Negative %',
      getNum: b => pct(b.sentiment_negative, b.sentiment_positive + b.sentiment_mixed + b.sentiment_negative),
      render: n => (
        <span className="flex items-center gap-2">
          <span>{n}%</span>
          <span className="h-1.5 rounded-full bg-red-500 inline-block" style={{ width: `${n}px` }} />
        </span>
      ),
    },
    { label: 'Actionable',  getNum: b => b.actionable_count },
    { label: 'AI Flagged',  getNum: b => b.ai_flagged_count },
  ]

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="pb-3 text-left font-medium text-muted-foreground w-36">Metric</th>
            {books.map(b => (
              <th key={b.id} className="pb-3 text-left font-medium">{b.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const nums    = books.map(b => row.getNum(b))
            const max     = Math.max(...nums)
            return (
              <tr key={row.label} className="border-b border-border last:border-0">
                <td className="py-2.5 pr-4 text-muted-foreground">{row.label}</td>
                {books.map((b, i) => {
                  const n        = nums[i]
                  const isWinner = n === max && max > 0
                  return (
                    <td key={b.id} className={`py-2.5 pr-6 ${isWinner ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}>
                      {row.render ? row.render(n) : n}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
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
        <div className="space-y-4">
          {/* Sentiment card grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {selectedBooks.map(book => {
              const total   = book.sentiment_positive + book.sentiment_mixed + book.sentiment_negative
              const variant = sentimentVariant(book.sentiment_positive, book.sentiment_negative, total)
              return (
                <Card key={book.id}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{book.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-3">
                      <span className="text-sm">{book.total_reviews} reviews</span>
                      {book.avg_rating !== null && (
                        <span className="text-sm font-medium">{book.avg_rating.toFixed(1)}★</span>
                      )}
                    </div>
                    <SentimentBar
                      positive={book.sentiment_positive}
                      mixed={book.sentiment_mixed}
                      negative={book.sentiment_negative}
                    />
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

          {/* Comparison table */}
          <Card>
            <CardHeader>
              <CardTitle>Side-by-Side Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <ComparisonTable books={selectedBooks} />
            </CardContent>
          </Card>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Select at least 2 books to compare</p>
      )}
    </div>
  )
}
