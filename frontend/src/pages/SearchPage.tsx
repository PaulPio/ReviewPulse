import SemanticSearch from '@/components/search/SemanticSearch'

export default function SearchPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Semantic Search</h1>
      <p className="text-sm text-muted-foreground">
        Search across all your book reviews using natural language
      </p>
      <SemanticSearch />
    </div>
  )
}
