import { useState } from 'react'
import { useBooks, useAddBook } from '@/hooks/useBooks'
import CatalogGrid from '@/components/catalog/CatalogGrid'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Plus, X } from 'lucide-react'

export default function DashboardPage() {
  const { data: books, isLoading } = useBooks()
  const addBook = useAddBook()
  const [showAdd, setShowAdd] = useState(false)
  const [title, setTitle] = useState('')
  const [isbn, setIsbn] = useState('')

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    await addBook.mutateAsync({ title, isbn: isbn || undefined })
    setTitle('')
    setIsbn('')
    setShowAdd(false)
  }

  if (isLoading) return <p className="text-muted-foreground">Loading books...</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your Books</h1>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Book
        </Button>
      </div>

      {showAdd && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Add a Book</CardTitle>
            <button onClick={() => setShowAdd(false)}><X className="h-4 w-4" /></button>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAdd} className="flex gap-3">
              <Input placeholder="Book title" value={title} onChange={e => setTitle(e.target.value)} required className="flex-1" />
              <Input placeholder="ISBN (optional)" value={isbn} onChange={e => setIsbn(e.target.value)} className="w-40" />
              <Button type="submit" disabled={addBook.isPending}>
                {addBook.isPending ? 'Adding...' : 'Add'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <CatalogGrid books={books || []} />
    </div>
  )
}
