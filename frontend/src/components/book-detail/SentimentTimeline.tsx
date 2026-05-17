import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { SentimentTimeline as TimelineData } from '@/types'

interface Props {
  data: TimelineData[]
}

export default function SentimentTimeline({ data }: Props) {
  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <XAxis dataKey="period_start" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Area type="monotone" dataKey="positive" stackId="1" fill="hsl(142, 71%, 35%)" fillOpacity={0.4} stroke="hsl(142, 71%, 35%)" />
          <Area type="monotone" dataKey="mixed" stackId="1" fill="hsl(38, 92%, 42%)" fillOpacity={0.35} stroke="hsl(38, 92%, 42%)" />
          <Area type="monotone" dataKey="negative" stackId="1" fill="hsl(0, 72%, 45%)" fillOpacity={0.35} stroke="hsl(0, 72%, 45%)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
