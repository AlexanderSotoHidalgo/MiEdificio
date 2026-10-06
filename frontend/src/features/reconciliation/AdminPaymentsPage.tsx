import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Eye, Inbox, Loader2, Search, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api, errorMessage } from '../../api/client'
import { AppShell } from '../../shared/components/AppShell'
import { StatusBadge } from '../../shared/components/StatusBadge'
import { money, monthFromPeriod, shortDate } from '../../shared/lib/format'
import type { FinancialSummary, PaymentReport } from '../../types'
import { ReceiptViewer } from './ReceiptViewer'

const predefined = ['El comprobante no es legible', 'El monto no coincide', 'La operación no fue encontrada', 'El comprobante corresponde a otro pago']

export function AdminPaymentsPage() {
  const client = useQueryClient()
  const [status, setStatus] = useState('En revisión')
  const [period, setPeriod] = useState('')
  const [unit, setUnit] = useState('')
  const [search, setSearch] = useState('')
  const [viewing, setViewing] = useState<PaymentReport | null>(null)
  const [observing, setObserving] = useState<PaymentReport | null>(null)
  const [reason, setReason] = useState(predefined[0])
  const query = useQuery({
    queryKey: ['payments', status, period, unit],
    queryFn: async () => (await api.get<PaymentReport[]>('/payments', { params: { status, period: period || undefined, unit: unit || undefined } })).data,
  })
  const summary = useQuery({ queryKey: ['summary', period], queryFn: async () => (await api.get<FinancialSummary>('/reports/summary', { params: { period: period || undefined } })).data })
  const payments = useMemo(() => (query.data ?? []).filter((item) => `${item.resident_name} ${item.operation_number} ${item.allocations.map((a) => a.unit_code).join(' ')}`.toLowerCase().includes(search.toLowerCase())), [query.data, search])
  const review = useMutation({
    mutationFn: ({ id, action, reviewReason }: { id: number; action: 'approve' | 'observe'; reviewReason?: string }) => api.post(`/payments/${id}/review`, { action, reason: reviewReason }),
    onSuccess: async () => { setObserving(null); await Promise.all([client.invalidateQueries({ queryKey: ['payments'] }), client.invalidateQueries({ queryKey: ['summary'] })]) },
  })
  const approve = (payment: PaymentReport) => { if (window.confirm(`¿Aprobar ${money.format(Number(payment.amount))}?`)) review.mutate({ id: payment.id, action: 'approve' }) }
  return <AppShell>
    <div><p className="text-sm font-semibold text-forest">Administración</p><h1 className="mt-1 font-['DM_Serif_Display'] text-4xl md:text-5xl">Conciliación de pagos</h1><p className="mt-3 text-sm text-black/50">Los más antiguos aparecen primero.</p></div>
    <section className="mt-8 grid gap-4 sm:grid-cols-3"><div className="card p-5"><p className="text-sm text-black/50">Por revisar</p><p className="mt-3 text-3xl font-bold text-forest">{status === 'En revisión' ? query.data?.length ?? '—' : '—'}</p></div><div className="card p-5"><p className="text-sm text-black/50">Emitido</p><p className="mt-3 text-2xl font-bold">{money.format(Number(summary.data?.issued ?? 0))}</p></div><div className="card p-5"><p className="text-sm text-black/50">Pendiente</p><p className="mt-3 text-2xl font-bold text-coral">{money.format(Number(summary.data?.pending ?? 0))}</p></div></section>
    <section className="card mt-6 overflow-hidden"><div className="grid gap-3 border-b p-4 md:grid-cols-[1fr_170px_150px_150px]"><label className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-black/35" size={17} /><input className="field py-2.5 pl-10" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Residente, unidad u operación" /></label><select className="field py-2.5" value={status} onChange={(e) => setStatus(e.target.value)}><option>En revisión</option><option>Aprobado</option><option>Observado</option></select><input aria-label="Periodo" className="field py-2.5" type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /><input aria-label="Unidad" className="field py-2.5" value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="Unidad" /></div>
      {review.isError && <p className="m-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{errorMessage(review.error)}</p>}
      {query.isLoading ? <div className="grid min-h-64 place-items-center"><Loader2 className="animate-spin" /></div> : query.isError ? <p className="p-6 text-rose-700">{errorMessage(query.error)}</p> : payments.length === 0 ? <div className="px-6 py-16 text-center"><Inbox className="mx-auto text-forest" /><p className="mt-3 text-sm text-black/50">No hay pagos con estos filtros.</p></div> : <div className="overflow-x-auto"><table className="w-full min-w-[1000px] text-left text-sm"><thead className="bg-black/[0.018] text-xs uppercase text-black/40"><tr><th className="px-5 py-4">Antigüedad</th><th className="px-4 py-4">Residente</th><th className="px-4 py-4">Aplicación</th><th className="px-4 py-4">Monto</th><th className="px-4 py-4">Operación</th><th className="px-4 py-4">Estado</th><th className="px-5 py-4">Acciones</th></tr></thead><tbody className="divide-y divide-black/[0.06]">{payments.map((payment) => <tr key={payment.id} className="align-top"><td className="px-5 py-5 text-black/55">{shortDate.format(new Date(payment.created_at))}</td><td className="px-4 py-5"><p className="font-semibold">{payment.resident_name}</p><p className="text-xs text-black/45">{payment.resident_email}</p></td><td className="px-4 py-5">{payment.allocations.map((item) => <p key={item.fee_id}>{item.unit_code} · {monthFromPeriod(item.period)} · {money.format(Number(item.amount))}</p>)}</td><td className="px-4 py-5 font-bold">{money.format(Number(payment.amount))}</td><td className="px-4 py-5"><p>{payment.operation_number}</p><p className="text-xs text-black/45">{shortDate.format(new Date(`${payment.payment_date}T00:00:00Z`))}</p></td><td className="px-4 py-5"><StatusBadge status={payment.status} />{payment.observation_reason && <p className="mt-2 max-w-48 text-xs text-rose-700">{payment.observation_reason}</p>}</td><td className="px-5 py-5"><div className="flex gap-2"><button className="btn-secondary px-3" onClick={() => setViewing(payment)}><Eye size={16} />Ver</button>{payment.status === 'En revisión' && <><button className="btn-primary px-3" onClick={() => approve(payment)} disabled={review.isPending}><Check size={16} />Aprobar</button><button className="btn-secondary px-3 text-rose-700" onClick={() => setObserving(payment)}><X size={16} />Observar</button></>}</div></td></tr>)}</tbody></table></div>}
    </section>
    {viewing && <ReceiptViewer payment={viewing} onClose={() => setViewing(null)} />}
    {observing && <div className="fixed inset-0 z-50 grid place-items-center bg-ink/50 p-4" role="dialog" aria-modal="true" aria-label="Observar pago"><form className="w-full max-w-md rounded-2xl bg-paper p-6" onSubmit={(event) => { event.preventDefault(); review.mutate({ id: observing.id, action: 'observe', reviewReason: reason }) }}><h2 className="text-xl font-semibold">Motivo de observación</h2><select className="field mt-5" value={reason} onChange={(e) => setReason(e.target.value)}>{predefined.map((item) => <option key={item}>{item}</option>)}</select><textarea className="field mt-3" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={1000} required /><div className="mt-5 flex gap-3"><button type="button" className="btn-secondary flex-1" onClick={() => setObserving(null)}>Cancelar</button><button className="btn-primary flex-1" disabled={review.isPending}>Confirmar</button></div></form></div>}
  </AppShell>
}
