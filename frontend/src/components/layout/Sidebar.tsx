import { NavLink } from 'react-router-dom'
import { BookOpen, BarChart3, Search, Mail, GitCompare } from 'lucide-react'

const navItems = [
  { to: '/', icon: BookOpen, label: 'Catalog', end: true },
  { to: '/compare', icon: GitCompare, label: 'Compare' },
  { to: '/search', icon: Search, label: 'Search' },
  { to: '/digest', icon: Mail, label: 'Digest' },
]

export default function Sidebar() {
  return (
    <aside className="hidden w-60 border-r border-border bg-card md:block">
      <div className="flex h-14 items-center border-b border-border px-4">
        <BarChart3 className="mr-2 h-6 w-6 text-primary" />
        <span className="text-lg font-semibold">ReviewPulse</span>
      </div>
      <nav className="space-y-1 p-3">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
