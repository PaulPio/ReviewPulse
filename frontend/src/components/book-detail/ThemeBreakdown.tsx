import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { ThemeCount } from '@/types'

interface Props {
  data: ThemeCount[]
}

export default function ThemeBreakdown({ data }: Props) {
  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical">
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis dataKey="theme" type="category" tick={{ fontSize: 12 }} width={100} />
          <Tooltip />
          <Bar dataKey="count" fill="hsl(222, 84%, 55%)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
