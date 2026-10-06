import { zodResolver } from '@hookform/resolvers/zod'
import { Building2, CheckCircle2, Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useAuth } from '../../AuthContext'
import { errorMessage } from '../../api/client'

const schema = z.object({
  email: z.string().email('Ingresa un correo válido'),
  password: z.string().min(8, 'Ingresa tu contraseña'),
})
type LoginValues = z.infer<typeof schema>

export function LoginPage() {
  const { login } = useAuth()
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<LoginValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: 'residente@miedificio.pe', password: 'Residente123!' },
  })
  const submit = handleSubmit(async (values) => {
    try { await login(values.email, values.password) }
    catch (error) { setError('root', { message: errorMessage(error) }) }
  })
  return (
    <div className="grid min-h-screen bg-paper lg:grid-cols-[1.08fr_0.92fr]">
      <section className="relative hidden overflow-hidden bg-forest p-12 text-white lg:flex lg:flex-col">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full border-[70px] border-white/[0.04]" />
        <div className="relative flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-white/15"><Building2 /></div><span className="text-lg font-semibold">MiEdificio</span></div>
        <div className="relative my-auto max-w-xl">
          <p className="mb-5 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-200">Cobranza sin fricción</p>
          <h1 className="font-['DM_Serif_Display'] text-6xl leading-[1.08]">Cuentas claras,<br />vecinos tranquilos.</h1>
          <p className="mt-7 max-w-md text-lg leading-relaxed text-white/70">Consulta cuotas, reporta pagos y mantén la administración al día.</p>
          <div className="mt-10 flex gap-7 text-sm text-white/70"><span className="flex items-center gap-2"><CheckCircle2 size={17} />Simple</span><span className="flex items-center gap-2"><CheckCircle2 size={17} />Seguro</span></div>
        </div>
      </section>
      <section className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center gap-3 lg:hidden"><div className="grid h-10 w-10 place-items-center rounded-xl bg-forest text-white"><Building2 size={20} /></div><span className="font-semibold">MiEdificio</span></div>
          <p className="text-sm font-semibold text-forest">Bienvenido</p>
          <h2 className="mt-2 font-['DM_Serif_Display'] text-4xl">Ingresa a tu cuenta</h2>
          <form className="mt-9 space-y-5" onSubmit={submit} noValidate>
            <div><label className="label" htmlFor="email">Correo electrónico</label><input className="field" id="email" type="email" autoComplete="email" {...register('email')} />{errors.email && <p className="field-error">{errors.email.message}</p>}</div>
            <div><label className="label" htmlFor="password">Contraseña</label><input className="field" id="password" type="password" autoComplete="current-password" {...register('password')} />{errors.password && <p className="field-error">{errors.password.message}</p>}</div>
            {errors.root && <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{errors.root.message}</p>}
            <button className="btn-primary w-full py-3.5" disabled={isSubmitting}>{isSubmitting ? <><Loader2 className="animate-spin" size={18} />Ingresando…</> : 'Ingresar'}</button>
          </form>
          <p className="mt-8 text-center text-xs text-black/45"><a className="underline" href="/terminos.html">Términos de uso</a> · <a className="underline" href="/privacidad.html">Política de privacidad</a></p>
        </div>
      </section>
    </div>
  )
}
