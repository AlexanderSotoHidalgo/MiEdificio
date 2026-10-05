import { AlertCircle, CheckCircle2, Clock3, Loader2, ReceiptText } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { AppShell } from '../components/AppShell'
import { PaymentModal } from '../components/PaymentModal'
import { StatusBadge } from '../components/StatusBadge'
import type { Fee } from '../types'

const money = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })
const month = new Intl.DateTimeFormat('es-PE', { month: 'long', year: 'numeric', timeZone: 'UTC' })
const shortDate = new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })

export function ResidentPage() {
  const [selected, setSelected] = useState<Fee | null>(null)
  const query = useQuery({ queryKey: ['fees'], queryFn: async () => (await api.get<Fee[]>('/fees/my-account')).data })
  const fees = query.data ?? []
  const total = fees.reduce((sum, fee) => sum + Number(fee.balance), 0)
  const reviewing = fees.filter((fee) => fee.status === 'Pago en revisión').length

  return (
    <AppShell>
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="text-sm font-semibold text-forest">Tu hogar, al día</p><h1 className="mt-1 font-['DM_Serif_Display'] text-4xl md:text-5xl">Estado de cuenta</h1><p className="mt-3 text-sm text-black/50">Revisa tus cuotas y reporta tus pagos en pocos pasos.</p></div><p className="text-xs text-black/40">Actualizado ahora</p></div>
      {query.isLoading ? <div className="grid min-h-[380px] place-items-center"><Loader2 className="animate-spin text-forest" /></div> : query.isError ? <div className="mt-8 rounded-2xl bg-rose-50 p-5 text-sm text-rose-700"><AlertCircle className="mb-2" />{errorMessage(query.error)}</div> : <>
        <section className="mt-9 grid gap-4 sm:grid-cols-3">
          <div className="card p-5"><div className="flex items-center justify-between"><p className="text-sm text-black/50">Saldo total</p><ReceiptText size={19} className="text-coral" /></div><p className="mt-4 text-2xl font-bold">{money.format(total)}</p><p className="mt-1 text-xs text-black/40">En {fees.filter((fee) => Number(fee.balance) > 0).length} cuota(s)</p></div>
          <div className="card p-5"><div className="flex items-center justify-between"><p className="text-sm text-black/50">En revisión</p><Clock3 size={19} className="text-blue-600" /></div><p className="mt-4 text-2xl font-bold">{reviewing}</p><p className="mt-1 text-xs text-black/40">Comprobantes enviados</p></div>
          <div className="card p-5"><div className="flex items-center justify-between"><p className="text-sm text-black/50">Cuotas pagadas</p><CheckCircle2 size={19} className="text-emerald-600" /></div><p className="mt-4 text-2xl font-bold">{fees.filter((fee) => fee.status === 'Pagada').length}</p><p className="mt-1 text-xs text-black/40">Historial visible</p></div>
        </section>
        <section className="card mt-7 overflow-hidden">
          <div className="border-b border-black/[0.06] px-5 py-5 md:px-6"><h2 className="font-semibold">Detalle de cuotas</h2></div>
          {fees.length === 0 ? <div className="px-6 py-16 text-center text-sm text-black/45">Aún no tienes cuotas registradas.</div> : <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-black/[0.018] text-xs uppercase tracking-wider text-black/40"><tr><th className="px-6 py-4 font-semibold">Periodo</th><th className="px-4 py-4 font-semibold">Unidad</th><th className="px-4 py-4 font-semibold">Vencimiento</th><th className="px-4 py-4 font-semibold">Importe</th><th className="px-4 py-4 font-semibold">Pagado</th><th className="px-4 py-4 font-semibold">Saldo</th><th className="px-4 py-4 font-semibold">Estado</th><th className="px-6 py-4" /></tr></thead><tbody className="divide-y divide-black/[0.06]">{fees.map((fee) => { const observation = fee.payment_reports.find((report) => report.status === 'Observado'); return <tr key={fee.id} className="align-top hover:bg-black/[0.012]"><td className="px-6 py-5 font-semibold capitalize">{month.format(new Date(Date.UTC(fee.period_year, fee.period_month - 1, 1)))}</td><td className="px-4 py-5">{fee.unit_code}</td><td className="px-4 py-5 text-black/55">{shortDate.format(new Date(`${fee.due_date}T00:00:00Z`))}</td><td className="px-4 py-5">{money.format(Number(fee.amount))}</td><td className="px-4 py-5 text-black/55">{money.format(Number(fee.paid_amount))}</td><td className="px-4 py-5 font-semibold">{money.format(Number(fee.balance))}</td><td className="px-4 py-5"><StatusBadge status={fee.status} />{observation?.review_comment && <p className="mt-2 max-w-[180px] text-xs leading-relaxed text-rose-700">Observación: {observation.review_comment}</p>}</td><td className="px-6 py-5 text-right">{fee.status === 'Pendiente' && Number(fee.balance) > 0 && <button className="btn-secondary whitespace-nowrap py-2" onClick={() => setSelected(fee)}>Reportar pago</button>}</td></tr>})}</tbody></table></div>}
        </section>
      </>}
      {selected && <PaymentModal fee={selected} onClose={() => setSelected(null)} />}
    </AppShell>
  )
}
