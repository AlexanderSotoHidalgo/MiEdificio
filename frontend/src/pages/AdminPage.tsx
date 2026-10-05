import { Check, ExternalLink, Inbox, Loader2, Search, X, XCircle } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState, type FormEvent } from 'react'
import { api, errorMessage } from '../api/client'
import { AppShell } from '../components/AppShell'
import type { PaymentReport } from '../types'

const money = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })
const date = new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })

export function AdminPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [observing, setObserving] = useState<PaymentReport | null>(null)
  const [reason, setReason] = useState('')
  const [receiptError, setReceiptError] = useState('')
  const query = useQuery({ queryKey: ['pending-payments'], queryFn: async () => (await api.get<PaymentReport[]>('/payments/pending')).data })
  const payments = useMemo(() => (query.data ?? []).filter((item) => `${item.resident_name} ${item.unit_code} ${item.operation_number}`.toLowerCase().includes(search.toLowerCase())), [query.data, search])

  const review = useMutation({
    mutationFn: async ({ id, action, reason: comment }: { id: number; action: 'approve' | 'observe'; reason?: string }) => api.post(`/payments/${id}/review`, { action, reason: comment }),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['pending-payments'] }); setObserving(null); setReason('') },
  })

  const approve = (payment: PaymentReport) => {
    if (window.confirm(`¿Aprobar el pago de ${money.format(Number(payment.amount))} de ${payment.resident_name}?`)) review.mutate({ id: payment.id, action: 'approve' })
  }
  const observe = (event: FormEvent) => { event.preventDefault(); if (observing) review.mutate({ id: observing.id, action: 'observe', reason }) }
  const openReceipt = async (payment: PaymentReport) => {
    setReceiptError('')
    const popup = window.open('', '_blank')
    try {
      const response = await api.get<Blob>(`/payments/${payment.id}/receipt`, { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      if (popup) popup.location.href = url
      else window.location.href = url
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (error) { popup?.close(); setReceiptError(errorMessage(error)) }
  }

  return (
    <AppShell>
      <div><p className="text-sm font-semibold text-forest">Administración</p><h1 className="mt-1 font-['DM_Serif_Display'] text-4xl md:text-5xl">Validación de pagos</h1><p className="mt-3 text-sm text-black/50">Confirma que el comprobante coincide antes de aplicarlo a la cuota.</p></div>
      <section className="mt-9 grid gap-4 sm:grid-cols-3"><div className="card p-5"><p className="text-sm text-black/50">Por revisar</p><p className="mt-3 text-3xl font-bold text-forest">{query.data?.length ?? '—'}</p></div><div className="card p-5"><p className="text-sm text-black/50">Monto reportado</p><p className="mt-3 text-3xl font-bold">{money.format((query.data ?? []).reduce((sum, item) => sum + Number(item.amount), 0))}</p></div><div className="card flex items-center gap-3 bg-mint/60 p-5"><div className="grid h-11 w-11 place-items-center rounded-full bg-white text-forest"><Inbox /></div><p className="text-sm leading-relaxed text-black/60">Revisa monto, fecha y número de operación.</p></div></section>
      <section className="card mt-7 overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-black/[0.06] px-5 py-5 sm:flex-row sm:items-center sm:justify-between"><h2 className="font-semibold">Comprobantes pendientes</h2><label className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-black/35" size={17} /><input className="field py-2.5 pl-10 sm:w-72" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar residente, unidad…" /></label></div>
        {receiptError && <p className="mx-5 mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{receiptError}</p>}
        {review.isError && <p className="mx-5 mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage(review.error)}</p>}
        {query.isLoading ? <div className="grid min-h-64 place-items-center"><Loader2 className="animate-spin text-forest" /></div> : query.isError ? <p className="p-6 text-sm text-rose-700">{errorMessage(query.error)}</p> : payments.length === 0 ? <div className="px-6 py-16 text-center"><div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-mint text-forest"><Check size={25} /></div><p className="mt-4 font-semibold">Todo está al día</p><p className="mt-1 text-sm text-black/45">No hay comprobantes pendientes de revisión.</p></div> : <div className="overflow-x-auto"><table className="w-full min-w-[920px] text-left text-sm"><thead className="bg-black/[0.018] text-xs uppercase tracking-wider text-black/40"><tr><th className="px-6 py-4 font-semibold">Residente</th><th className="px-4 py-4 font-semibold">Unidad</th><th className="px-4 py-4 font-semibold">Monto</th><th className="px-4 py-4 font-semibold">Fecha pago</th><th className="px-4 py-4 font-semibold">Operación</th><th className="px-4 py-4 font-semibold">Comprobante</th><th className="px-6 py-4" /></tr></thead><tbody className="divide-y divide-black/[0.06]">{payments.map((payment) => <tr key={payment.id} className="hover:bg-black/[0.012]"><td className="px-6 py-5"><p className="font-semibold">{payment.resident_name}</p><p className="mt-0.5 text-xs text-black/45">{payment.resident_email}</p></td><td className="px-4 py-5 font-medium">{payment.unit_code}</td><td className="px-4 py-5 font-bold">{money.format(Number(payment.amount))}</td><td className="px-4 py-5 text-black/55">{date.format(new Date(`${payment.payment_date}T00:00:00Z`))}</td><td className="px-4 py-5 font-mono text-xs">{payment.operation_number}</td><td className="px-4 py-5"><button className="inline-flex items-center gap-1.5 font-semibold text-forest hover:underline" onClick={() => openReceipt(payment)}><ExternalLink size={15} />Ver archivo</button><p className="mt-1 max-w-32 truncate text-xs text-black/40">{payment.receipt_original_name}</p></td><td className="px-6 py-5"><div className="flex justify-end gap-2"><button className="btn-secondary px-3 py-2 text-rose-700" onClick={() => setObserving(payment)} disabled={review.isPending}><XCircle size={16} />Observar</button><button className="btn-primary px-3 py-2" onClick={() => approve(payment)} disabled={review.isPending}><Check size={16} />Aprobar</button></div></td></tr>)}</tbody></table></div>}
      </section>
      {observing && <div className="fixed inset-0 z-50 grid place-items-end bg-ink/45 p-0 backdrop-blur-sm sm:place-items-center sm:p-5" role="dialog" aria-modal="true"><form className="w-full rounded-t-3xl bg-paper p-6 shadow-2xl sm:max-w-md sm:rounded-3xl sm:p-8" onSubmit={observe}><div className="flex justify-between"><div><p className="text-xs font-bold uppercase tracking-widest text-rose-700">Observar pago</p><h2 className="mt-2 font-['DM_Serif_Display'] text-3xl">Indica el motivo</h2></div><button type="button" className="rounded-full p-2 hover:bg-black/5" onClick={() => setObserving(null)}><X size={20} /></button></div><p className="mt-3 text-sm leading-relaxed text-black/50">El motivo será visible para {observing.resident_name} y podrá enviar un nuevo reporte.</p><div className="mt-6"><label className="label" htmlFor="reason">Motivo de observación</label><textarea className="field min-h-28 resize-none" id="reason" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={1000} placeholder="Ej. El monto del comprobante no coincide…" required /></div>{review.isError && <p className="mt-3 text-sm text-rose-700">{errorMessage(review.error)}</p>}<div className="mt-6 flex gap-3"><button type="button" className="btn-secondary flex-1" onClick={() => setObserving(null)}>Cancelar</button><button className="btn-primary flex-1 bg-rose-700 hover:bg-rose-800" disabled={review.isPending}>{review.isPending ? <Loader2 className="animate-spin" size={17} /> : 'Enviar observación'}</button></div></form></div>}
    </AppShell>
  )
}
