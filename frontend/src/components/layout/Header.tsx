import { useAuth } from '@/hooks/useAuth'
import { LogOut } from 'lucide-react'

export default function Header() {
  const { user, signOut } = useAuth()

  return (
    <header className="flex h-14 items-center justify-between border-b border-border px-6">
      <h1 className="text-lg font-semibold md:hidden">ReviewPulse</h1>
      <div className="ml-auto flex items-center gap-4">
        <span className="text-sm text-muted-foreground">{user?.email}</span>
        <button
          onClick={() => { signOut(); globalThis.location.assign('/login') }}
          className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
