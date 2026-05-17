import BookCard from './BookCard'
import type { Book } from '@/types'

interface CatalogGridProps {
  books: Book[]
}

export default function CatalogGrid({ books }: CatalogGridProps) {
  if (books.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-lg font-medium">No books yet</p>
        <p className="text-sm text-muted-foreground mt-1">Add your first book to get started</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {books.map(book => (
        <BookCard key={book.id} book={book} />
      ))}
    </div>
  )
}
