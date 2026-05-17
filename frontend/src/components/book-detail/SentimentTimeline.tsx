import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import type { SentimentTimeline as TimelineData } from '@/types'

export default function SentimentTimeline({ data }: Readonly<{ data: TimelineData[] }>) {
  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="period_start"
            tick={{ fontSize: 11 }}
            tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
          />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Area type="monotone" dataKey="positive" stackId="1" fill="hsl(142, 71%, 35%)" fillOpacity={0.4} stroke="hsl(142, 71%, 35%)" />
          <Area type="monotone" dataKey="mixed"    stackId="1" fill="hsl(38, 92%, 42%)"  fillOpacity={0.35} stroke="hsl(38, 92%, 42%)" />
          <Area type="monotone" dataKey="negative" stackId="1" fill="hsl(0, 72%, 45%)"   fillOpacity={0.35} stroke="hsl(0, 72%, 45%)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
