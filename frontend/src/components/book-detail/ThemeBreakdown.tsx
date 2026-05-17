import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { ThemeCount } from '@/types'

export default function ThemeBreakdown({ data }: Readonly<{ data: ThemeCount[] }>) {
  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical">
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis dataKey="theme" type="category" tick={{ fontSize: 11 }} width={110} />
          <Tooltip cursor={{ fill: 'hsl(var(--accent))' }} />
          <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
