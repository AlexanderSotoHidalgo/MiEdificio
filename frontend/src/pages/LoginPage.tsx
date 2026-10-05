import { Building2, CheckCircle2, Loader2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useAuth } from '../AuthContext'
import { errorMessage } from '../api/client'

export function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('residente@miedificio.pe')
  const [password, setPassword] = useState('Residente123!')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try { await login(email, password) } catch (reason) { setError(errorMessage(reason)) } finally { setLoading(false) }
  }

  return (
    <div className="grid min-h-screen bg-paper lg:grid-cols-[1.08fr_0.92fr]">
      <section className="relative hidden overflow-hidden bg-forest p-12 text-white lg:flex lg:flex-col">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full border-[70px] border-white/[0.04]" />
        <div className="relative flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-white/15"><Building2 /></div><span className="text-lg font-semibold">MiEdificio</span></div>
        <div className="relative my-auto max-w-xl">
          <p className="mb-5 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-200">Cobranza sin fricción</p>
          <h1 className="font-['DM_Serif_Display'] text-6xl leading-[1.08]">Cuentas claras,<br />vecinos tranquilos.</h1>
          <p className="mt-7 max-w-md text-lg leading-relaxed text-white/70">Un solo lugar para consultar cuotas, reportar pagos y mantener la administración al día.</p>
          <div className="mt-10 flex gap-7 text-sm text-white/70"><span className="flex items-center gap-2"><CheckCircle2 size={17} />Simple</span><span className="flex items-center gap-2"><CheckCircle2 size={17} />Transparente</span><span className="flex items-center gap-2"><CheckCircle2 size={17} />Seguro</span></div>
        </div>
        <p className="relative text-xs text-white/40">Diseñado para condominios que quieren dedicar menos tiempo a cobrar.</p>
      </section>
      <section className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center gap-3 lg:hidden"><div className="grid h-10 w-10 place-items-center rounded-xl bg-forest text-white"><Building2 size={20} /></div><span className="font-semibold">MiEdificio</span></div>
          <p className="text-sm font-semibold text-forest">Bienvenido de vuelta</p>
          <h2 className="mt-2 font-['DM_Serif_Display'] text-4xl">Ingresa a tu cuenta</h2>
          <p className="mt-3 text-sm leading-relaxed text-black/50">Consulta tus cuotas o continúa con la validación de pagos.</p>
          <form className="mt-9 space-y-5" onSubmit={submit}>
            <div><label className="label" htmlFor="email">Correo electrónico</label><input className="field" id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
            <div><label className="label" htmlFor="password">Contraseña</label><input className="field" id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></div>
            {error && <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
            <button className="btn-primary w-full py-3.5" disabled={loading}>{loading ? <><Loader2 className="animate-spin" size={18} />Ingresando…</> : 'Ingresar'}</button>
          </form>
          <div className="mt-8 rounded-xl border border-black/[0.07] bg-white/70 p-4 text-xs leading-relaxed text-black/50">
            <strong className="text-ink">Acceso demo:</strong> residente@miedificio.pe / Residente123!<br />admin@miedificio.pe / Admin123!
          </div>
        </div>
      </section>
    </div>
  )
}
