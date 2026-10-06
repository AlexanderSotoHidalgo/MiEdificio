import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FileUp, Loader2, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api, errorMessage } from '../../api/client'
import { money, monthFromPeriod } from '../../shared/lib/format'
import { compressImage } from '../../shared/lib/imageCompression'
import type { Fee } from '../../types'

const schema = z.object({
  paymentDate: z.string().min(1, 'Indica la fecha'),
  operationNumber: z.string().trim().min(3, 'Ingresa el número de operación').max(80),
  receipt: z.custom<File>((value) => value instanceof File, 'Selecciona un comprobante'),
})
type Values = z.infer<typeof schema>

export function PaymentModal({ fees, initialFee, onClose }: { fees: Fee[]; initialFee: Fee; onClose: () => void }) {
  const queryClient = useQueryClient()
  const candidates = fees.filter((fee) => Number(fee.available_to_report) > 0 && fee.status !== 'Anulada')
  const [selected, setSelected] = useState<Record<number, string>>({ [initialFee.id]: initialFee.available_to_report })
  const [preview, setPreview] = useState('')
  const [success, setSuccess] = useState(false)
  const { register, handleSubmit, setValue, setError, formState: { errors } } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { paymentDate: new Date().toISOString().slice(0, 10), operationNumber: '' },
  })
  const total = useMemo(() => Object.values(selected).reduce((sum, value) => sum + Number(value || 0), 0), [selected])
  useEffect(() => {
    const listener = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', listener)
    return () => { window.removeEventListener('keydown', listener); if (preview) URL.revokeObjectURL(preview) }
  }, [onClose, preview])

  const mutation = useMutation({
    mutationFn: async (values: Values) => {
      const allocations = Object.entries(selected).map(([feeId, amount]) => ({ fee_id: Number(feeId), amount }))
      if (!allocations.length || total <= 0) throw new Error('Selecciona al menos una cuota.')
      for (const allocation of allocations) {
        const fee = candidates.find((item) => item.id === allocation.fee_id)
        if (!fee || Number(allocation.amount) <= 0 || Number(allocation.amount) > Number(fee.available_to_report)) {
          throw new Error(`Revisa el monto asignado a la cuota ${fee?.unit_code ?? allocation.fee_id}.`)
        }
      }
      const form = new FormData()
      form.append('amount', total.toFixed(2))
      form.append('payment_date', values.paymentDate)
      form.append('operation_number', values.operationNumber)
      form.append('allocations', JSON.stringify(allocations))
      form.append('receipt', values.receipt)
      await api.post('/payments/report', form, { headers: { 'Idempotency-Key': crypto.randomUUID() } })
    },
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['fees'] }); setSuccess(true) },
  })
  const chooseFile = async (file?: File) => {
    if (!file) return
    if (file.size > 5 * 1024 * 1024) { setError('receipt', { message: 'El archivo supera 5 MB' }); return }
    const compressed = await compressImage(file)
    setValue('receipt', compressed, { shouldValidate: true })
    if (preview) URL.revokeObjectURL(preview)
    setPreview(URL.createObjectURL(compressed))
  }
  const toggleFee = (fee: Fee) => setSelected((current) => {
    const next = { ...current }
    if (next[fee.id] !== undefined) delete next[fee.id]
    else next[fee.id] = fee.available_to_report
    return next
  })
  return (
    <div className="fixed inset-0 z-50 grid place-items-end bg-ink/45 backdrop-blur-sm sm:place-items-center sm:p-5" role="dialog" aria-modal="true" aria-labelledby="payment-title">
      <div className="max-h-[96vh] w-full overflow-y-auto rounded-t-3xl bg-paper p-5 shadow-2xl sm:max-w-2xl sm:rounded-3xl sm:p-8">
        <div className="flex items-start justify-between"><div><p className="text-xs font-bold uppercase tracking-widest text-forest">Pago por Yape, Plin o transferencia</p><h2 id="payment-title" className="mt-2 font-['DM_Serif_Display'] text-3xl">Reportar pago</h2></div><button className="rounded-full p-2 hover:bg-black/5" onClick={onClose} aria-label="Cerrar"><X size={20} /></button></div>
        {success ? <div className="py-12 text-center"><div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-mint text-forest"><CheckCircle2 size={31} /></div><h3 className="mt-5 text-xl font-semibold">Comprobante enviado</h3><p className="mt-2 text-sm text-black/55">El saldo no cambiará hasta que administración apruebe el pago.</p><button className="btn-primary mt-7" onClick={onClose}>Volver a mi cuenta</button></div> :
          <form className="mt-7 space-y-5" onSubmit={handleSubmit((values) => mutation.mutate(values))} noValidate>
            <fieldset><legend className="label">Cuotas a pagar</legend><div className="max-h-48 space-y-2 overflow-y-auto rounded-2xl border border-black/10 bg-white p-3">{candidates.map((fee) => <div key={fee.id} className="grid grid-cols-[auto_1fr_110px] items-center gap-3 rounded-xl px-2 py-2 hover:bg-black/[0.025]"><input aria-label={`Seleccionar cuota ${fee.unit_code} ${fee.period}`} type="checkbox" checked={selected[fee.id] !== undefined} onChange={() => toggleFee(fee)} /><div><p className="text-sm font-semibold">{fee.unit_code} · {fee.concept}</p><p className="text-xs text-black/45 capitalize">{monthFromPeriod(fee.period)} · disponible {money.format(Number(fee.available_to_report))}</p></div><input aria-label={`Monto para ${fee.unit_code}`} className="field py-2 text-right" type="number" min="0.01" step="0.01" max={fee.available_to_report} disabled={selected[fee.id] === undefined} value={selected[fee.id] ?? ''} onChange={(event) => setSelected((current) => ({ ...current, [fee.id]: event.target.value }))} /></div>)}</div></fieldset>
            <div className="rounded-2xl bg-mint/70 p-4"><p className="text-xs text-black/50">Total reportado</p><p className="mt-1 text-2xl font-bold text-forest">{money.format(total)}</p></div>
            <div className="grid gap-4 sm:grid-cols-2"><div><label className="label" htmlFor="paymentDate">Fecha de pago</label><input className="field" id="paymentDate" type="date" max={new Date().toISOString().slice(0, 10)} {...register('paymentDate')} />{errors.paymentDate && <p className="field-error">{errors.paymentDate.message}</p>}</div><div><label className="label" htmlFor="operationNumber">N.º de operación</label><input className="field" id="operationNumber" {...register('operationNumber')} />{errors.operationNumber && <p className="field-error">{errors.operationNumber.message}</p>}</div></div>
            <div><span className="label">Comprobante</span><label className="flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed border-black/10 bg-white px-4 py-6 text-center hover:border-forest/40"><FileUp className="text-forest" /><span className="mt-2 text-sm font-semibold">Selecciona o toma una foto</span><span className="mt-1 text-xs text-black/45">PDF, JPG, PNG o WEBP · máximo 5 MB</span><input className="sr-only" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" capture="environment" onChange={(event) => void chooseFile(event.target.files?.[0])} /></label>{errors.receipt && <p className="field-error">{errors.receipt.message}</p>}{preview && <div className="mt-3 overflow-hidden rounded-xl border bg-white"><object data={preview} className="h-48 w-full object-contain" aria-label="Vista previa del comprobante" /></div>}</div>
            {mutation.isError && <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage(mutation.error)}</p>}
            <div className="flex gap-3 pt-2"><button type="button" className="btn-secondary flex-1" onClick={onClose}>Cancelar</button><button className="btn-primary flex-1" disabled={mutation.isPending || total <= 0}>{mutation.isPending ? <><Loader2 className="animate-spin" size={17} />Enviando…</> : 'Enviar reporte'}</button></div>
          </form>}
      </div>
    </div>
  )
}
