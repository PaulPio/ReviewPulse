interface SentimentBarProps {
  positive: number
  mixed: number
  negative: number
  showLabels?: boolean
  height?: 'sm' | 'md'
}

const heightClass = { sm: 'h-1.5', md: 'h-2.5' } as const

export function SentimentBar({
  positive,
  mixed,
  negative,
  showLabels = true,
  height = 'sm',
}: Readonly<SentimentBarProps>) {
  const total = positive + mixed + negative
  if (total === 0) {
    return <span className="text-xs text-muted-foreground">No data</span>
  }

  const posPct  = Math.round((positive / total) * 100)
  const mixPct  = Math.round((mixed    / total) * 100)
  const negPct  = 100 - posPct - mixPct

  return (
    <div className="space-y-1">
      <div className={`flex w-full overflow-hidden rounded-full ${heightClass[height]}`}>
        <div className="bg-green-500"  style={{ width: `${posPct}%` }} />
        <div className="bg-yellow-400" style={{ width: `${mixPct}%` }} />
        <div className="bg-red-500"    style={{ width: `${negPct}%` }} />
      </div>
      {showLabels && (
        <div className="flex gap-3 text-xs text-muted-foreground">
          <span className="text-green-600">{posPct}% positive</span>
          <span className="text-yellow-600">{mixPct}% mixed</span>
          <span className="text-red-600">{negPct}% negative</span>
        </div>
      )}
    </div>
  )
}
