import { CheckCircle2, FileUp, Loader2, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { Fee } from '../types'

const money = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })

export function PaymentModal({ fee, onClose }: { fee: Fee; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [amount, setAmount] = useState(fee.balance)
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10))
  const [operation, setOperation] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [success, setSuccess] = useState(false)

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Selecciona un comprobante.')
      const form = new FormData()
      form.append('fee_id', String(fee.id)); form.append('amount', amount)
      form.append('payment_date', paymentDate); form.append('operation_number', operation)
      form.append('receipt', file)
      await api.post('/payments/report', form)
    },
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['fees'] }); setSuccess(true) },
  })

  const submit = (event: FormEvent) => { event.preventDefault(); mutation.mutate() }

  return (
    <div className="fixed inset-0 z-50 grid place-items-end bg-ink/45 p-0 backdrop-blur-sm sm:place-items-center sm:p-5" role="dialog" aria-modal="true" aria-label="Reportar pago">
      <div className="max-h-[95vh] w-full overflow-y-auto rounded-t-3xl bg-paper p-6 shadow-2xl sm:max-w-lg sm:rounded-3xl sm:p-8">
        <div className="flex items-start justify-between"><div><p className="text-xs font-bold uppercase tracking-widest text-forest">Unidad {fee.unit_code}</p><h2 className="mt-2 font-['DM_Serif_Display'] text-3xl">Reportar un pago</h2></div><button className="rounded-full p-2 hover:bg-black/5" onClick={onClose} aria-label="Cerrar"><X size={20} /></button></div>
        {success ? (
          <div className="py-12 text-center"><div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-mint text-forest"><CheckCircle2 size={31} /></div><h3 className="mt-5 text-xl font-semibold">Comprobante enviado</h3><p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-black/55">La administración lo revisará. Tu cuota ya figura como “Pago en revisión”.</p><button className="btn-primary mt-7" onClick={onClose}>Volver a mi cuenta</button></div>
        ) : (
          <form className="mt-7 space-y-5" onSubmit={submit}>
            <div className="rounded-2xl bg-mint/70 p-4"><p className="text-xs text-black/50">Saldo pendiente</p><p className="mt-1 text-xl font-bold text-forest">{money.format(Number(fee.balance))}</p></div>
            <div className="grid gap-4 sm:grid-cols-2"><div><label className="label" htmlFor="amount">Monto pagado</label><input className="field" id="amount" type="number" min="0.01" max={fee.balance} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required /></div><div><label className="label" htmlFor="date">Fecha de pago</label><input className="field" id="date" type="date" value={paymentDate} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setPaymentDate(e.target.value)} required /></div></div>
            <div><label className="label" htmlFor="operation">N.º de operación</label><input className="field" id="operation" value={operation} onChange={(e) => setOperation(e.target.value)} placeholder="Ej. 00483921" maxLength={80} required /></div>
            <div><span className="label">Comprobante</span><label className="flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed border-black/10 bg-white px-4 py-7 text-center transition hover:border-forest/40"><FileUp className="text-forest" /><span className="mt-2 text-sm font-semibold">{file ? file.name : 'Selecciona un PDF o imagen'}</span><span className="mt-1 text-xs text-black/45">Máximo 8 MB</span><input className="sr-only" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required /></label></div>
            {mutation.isError && <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{mutation.error instanceof Error && mutation.error.message === 'Selecciona un comprobante.' ? mutation.error.message : errorMessage(mutation.error)}</p>}
            <div className="flex gap-3 pt-2"><button type="button" className="btn-secondary flex-1" onClick={onClose}>Cancelar</button><button className="btn-primary flex-1" disabled={mutation.isPending}>{mutation.isPending ? <><Loader2 className="animate-spin" size={17} />Enviando…</> : 'Enviar reporte'}</button></div>
          </form>
        )}
      </div>
    </div>
  )
}

