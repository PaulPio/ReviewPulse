import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, MessageSquare, Zap, Star, Sparkles, Plus, X } from 'lucide-react'
import { useBooks, useAddBook, useWhatsNew } from '@/hooks/useBooks'
import CatalogGrid from '@/components/catalog/CatalogGrid'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { StatTile } from '@/components/ui/StatTile'
import { Badge } from '@/components/ui/Badge'

export default function DashboardPage() {
  const { data: books, isLoading } = useBooks()
  const { data: whatsNew }         = useWhatsNew()
  const addBook                    = useAddBook()
  const [showAdd, setShowAdd]      = useState(false)
  const [title, setTitle]          = useState('')
  const [isbn, setIsbn]            = useState('')

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    await addBook.mutateAsync({ title, isbn: isbn || undefined })
    setTitle('')
    setIsbn('')
    setShowAdd(false)
  }

  const bookList = books ?? []

  const totalReviews    = bookList.reduce((s, b) => s + b.total_reviews, 0)
  const totalActionable = bookList.reduce((s, b) => s + b.actionable_count, 0)
  const ratedBooks      = bookList.filter(b => b.avg_rating !== null)
  const avgRating       = ratedBooks.length
    ? ratedBooks.reduce((s, b) => s + b.avg_rating!, 0) / ratedBooks.length
    : null

  const whatsNewItems = [
    ...(whatsNew?.actionable_reviews ?? []).map(r => ({ ...r, kind: 'actionable' as const })),
    ...(whatsNew?.ai_flagged_reviews  ?? []).map(r => ({ ...r, kind: 'ai'         as const })),
  ].slice(0, 5)

  if (isLoading) return <p className="text-muted-foreground">Loading books…</p>

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your Books</h1>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Book
        </Button>
      </div>

      {/* Stats strip */}
      {bookList.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            label="Books"
            value={bookList.length}
            icon={<BookOpen className="h-4 w-4" />}
          />
          <StatTile
            label="Total Reviews"
            value={totalReviews.toLocaleString()}
            icon={<MessageSquare className="h-4 w-4" />}
          />
          <StatTile
            label="Actionable"
            value={totalActionable}
            icon={<Zap className="h-4 w-4" />}
            variant={totalActionable > 0 ? 'warning' : 'default'}
          />
          <StatTile
            label="Avg Rating"
            value={avgRating === null ? '—' : `${avgRating.toFixed(1)} ★`}
            icon={<Star className="h-4 w-4" />}
          />
        </div>
      )}

      {/* What's New */}
      {whatsNew && whatsNew.new_reviews_count > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              What's New
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              {whatsNew.new_reviews_count} new reviews since{' '}
              {new Date(whatsNew.since).toLocaleDateString('en', { weekday: 'long', month: 'short', day: 'numeric' })}
            </p>
          </CardHeader>
          <CardContent className="space-y-2">
            {whatsNewItems.map(item => (
              <div
                key={`${item.kind}-${item.id}`}
                className="flex items-start justify-between gap-3 rounded-md border border-border p-2 text-sm"
              >
                <Link
                  to={`/books/${item.book_id}`}
                  className="text-foreground hover:underline line-clamp-1 flex-1 min-w-0"
                >
                  {item.summary ?? 'View review'}
                </Link>
                <Badge variant={item.kind === 'actionable' ? 'mixed' : 'negative'}>
                  {item.kind === 'actionable' ? 'Actionable' : 'AI Flagged'}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Add book form */}
      {showAdd && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle>Add a Book</CardTitle>
            <button onClick={() => setShowAdd(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAdd} className="flex gap-3">
              <Input
                placeholder="Book title"
                value={title}
                onChange={e => setTitle(e.target.value)}
                required
                className="flex-1"
              />
              <Input
                placeholder="ISBN (optional)"
                value={isbn}
                onChange={e => setIsbn(e.target.value)}
                className="w-40"
              />
              <Button type="submit" disabled={addBook.isPending}>
                {addBook.isPending ? 'Adding…' : 'Add'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <CatalogGrid books={bookList} />
    </div>
  )
}
