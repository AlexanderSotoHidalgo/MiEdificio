import { Building2, CircleUserRound, CreditCard, LogOut } from 'lucide-react'
import type { ReactNode } from 'react'
import { useAuth } from '../../AuthContext'

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  return (
    <div className="min-h-screen bg-paper lg:flex">
      <aside className="hidden w-64 shrink-0 flex-col bg-forest p-6 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/15"><Building2 size={21} /></div>
          <div><p className="font-semibold">MiEdificio</p><p className="text-xs text-white/60">Gestión simple</p></div>
        </div>
        <nav className="mt-12">
          <div className="flex items-center gap-3 rounded-xl bg-white/15 px-3 py-3 text-sm font-medium">
            <CreditCard size={18} />{user?.role === 'administrador' ? 'Conciliar pagos' : 'Estado de cuenta'}
          </div>
        </nav>
        <div className="mt-auto border-t border-white/15 pt-5">
          <div className="mb-4 flex items-center gap-3">
            <CircleUserRound className="text-white/70" />
            <div className="min-w-0"><p className="truncate text-sm font-medium">{user?.full_name}</p><p className="text-xs capitalize text-white/60">{user?.role}</p></div>
          </div>
          <button className="flex items-center gap-2 text-sm text-white/70 hover:text-white" onClick={logout}><LogOut size={16} />Cerrar sesión</button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex h-16 items-center justify-between border-b border-black/[0.06] bg-white/70 px-5 backdrop-blur lg:hidden">
          <div className="flex items-center gap-2 font-semibold"><Building2 className="text-forest" /> MiEdificio</div>
          <button aria-label="Cerrar sesión" onClick={logout}><LogOut size={20} /></button>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-7 sm:px-5 md:px-9 lg:py-11">{children}</main>
      </div>
    </div>
  )
}
