interface ScoreBarProps {
  score: number  // 0..1
}

export function ScoreBar({ score }: Readonly<ScoreBarProps>) {
  const pct = Math.round(score * 100)
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-primary">{pct}% match</p>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
