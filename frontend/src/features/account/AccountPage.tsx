import { useQuery } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Clock3, Download, Loader2, ReceiptText } from 'lucide-react'
import { useState } from 'react'
import { api, errorMessage } from '../../api/client'
import { PaymentModal } from '../payments/PaymentModal'
import { AppShell } from '../../shared/components/AppShell'
import { StatusBadge } from '../../shared/components/StatusBadge'
import { money, monthFromPeriod, shortDate } from '../../shared/lib/format'
import type { Fee } from '../../types'

async function openProtectedFile(url: string, filename?: string) {
  const response = await api.get<Blob>(url, { responseType: 'blob' })
  const objectUrl = URL.createObjectURL(response.data)
  if (filename) {
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = filename
    link.click()
  } else window.open(objectUrl, '_blank', 'noopener,noreferrer')
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}

export function AccountPage() {
  const [selected, setSelected] = useState<Fee | null>(null)
  const [downloadError, setDownloadError] = useState('')
  const query = useQuery({
    queryKey: ['fees'],
    queryFn: async () => (await api.get<Fee[]>('/fees/my-account')).data,
  })
  const fees = query.data ?? []
  const total = fees.reduce((sum, fee) => sum + Number(fee.balance), 0)
  const reviewing = fees.filter((fee) => Number(fee.in_review_amount) > 0).length
  const downloadStatement = async () => {
    try {
      setDownloadError('')
      await openProtectedFile('/reports/my-account.pdf', 'estado-de-cuenta.pdf')
    } catch (error) {
      setDownloadError(errorMessage(error))
    }
  }
  return (
    <AppShell>
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-semibold text-forest">Tu hogar, al día</p>
          <h1 className="mt-1 font-['DM_Serif_Display'] text-4xl md:text-5xl">Estado de cuenta</h1>
          <p className="mt-3 text-sm text-black/50">Consulta saldos derivados de pagos aprobados.</p>
        </div>
        <button className="btn-secondary" onClick={() => void downloadStatement()}>
          <Download size={17} />
          Descargar PDF
        </button>
      </div>
      {downloadError && (
        <p className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{downloadError}</p>
      )}
      {query.isLoading ? (
        <div className="grid min-h-[380px] place-items-center">
          <Loader2 className="animate-spin text-forest" />
        </div>
      ) : query.isError ? (
        <div className="mt-8 rounded-2xl bg-rose-50 p-5 text-sm text-rose-700">
          <AlertCircle className="mb-2" />
          {errorMessage(query.error)}
        </div>
      ) : (
        <>
          <section className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="card p-5">
              <div className="flex justify-between">
                <p className="text-sm text-black/50">Saldo total</p>
                <ReceiptText size={19} className="text-coral" />
              </div>
              <p className="mt-4 text-2xl font-bold">{money.format(total)}</p>
            </div>
            <div className="card p-5">
              <div className="flex justify-between">
                <p className="text-sm text-black/50">En revisión</p>
                <Clock3 size={19} className="text-blue-600" />
              </div>
              <p className="mt-4 text-2xl font-bold">{reviewing}</p>
            </div>
            <div className="card p-5">
              <div className="flex justify-between">
                <p className="text-sm text-black/50">Pagadas</p>
                <CheckCircle2 size={19} className="text-emerald-600" />
              </div>
              <p className="mt-4 text-2xl font-bold">
                {fees.filter((fee) => fee.status === 'Pagada').length}
              </p>
            </div>
          </section>
          {fees.length === 0 ? (
            <div className="card mt-7 px-6 py-16 text-center text-sm text-black/45">
              Aún no tienes cuotas registradas.
            </div>
          ) : (
            <>
              <div className="mt-6 space-y-3 md:hidden">
                {fees.map((fee) => (
                  <FeeCard key={fee.id} fee={fee} onReport={() => setSelected(fee)} />
                ))}
              </div>
              <section className="card mt-7 hidden overflow-hidden md:block">
                <div className="border-b border-black/[0.06] px-6 py-5">
                  <h2 className="font-semibold">Detalle de cuotas</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[900px] text-left text-sm">
                    <thead className="bg-black/[0.018] text-xs uppercase text-black/40">
                      <tr>
                        <th className="px-6 py-4">Periodo</th>
                        <th className="px-4 py-4">Unidad</th>
                        <th className="px-4 py-4">Concepto</th>
                        <th className="px-4 py-4">Vencimiento</th>
                        <th className="px-4 py-4">Importe</th>
                        <th className="px-4 py-4">Pagado</th>
                        <th className="px-4 py-4">Saldo</th>
                        <th className="px-4 py-4">Estado</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-black/[0.06]">
                      {fees.map((fee) => (
                        <tr key={fee.id}>
                          <td className="px-6 py-5 font-semibold capitalize">
                            {monthFromPeriod(fee.period)}
                          </td>
                          <td className="px-4 py-5">{fee.unit_code}</td>
                          <td className="px-4 py-5">{fee.concept}</td>
                          <td className="px-4 py-5 text-black/55">
                            {shortDate.format(new Date(`${fee.due_date}T00:00:00Z`))}
                          </td>
                          <td className="px-4 py-5">{money.format(Number(fee.amount))}</td>
                          <td className="px-4 py-5">{money.format(Number(fee.paid_amount))}</td>
                          <td className="px-4 py-5 font-semibold">{money.format(Number(fee.balance))}</td>
                          <td className="px-4 py-5">
                            <StatusBadge status={fee.status} />
                            <Observation fee={fee} />
                          </td>
                          <td className="px-6 py-5 text-right">
                            <FeeActions fee={fee} onReport={() => setSelected(fee)} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </>
      )}
      {selected && <PaymentModal fees={fees} initialFee={selected} onClose={() => setSelected(null)} />}
    </AppShell>
  )
}

function Observation({ fee }: { fee: Fee }) {
  const observed = fee.payment_reports.find((item) => item.status === 'Observado' && item.observation_reason)
  return observed ? (
    <p className="mt-2 max-w-56 text-xs leading-relaxed text-rose-700">{observed.observation_reason}</p>
  ) : null
}

function FeeCard({ fee, onReport }: { fee: Fee; onReport: () => void }) {
  return (
    <article className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold capitalize">{monthFromPeriod(fee.period)}</p>
          <p className="mt-1 text-xs text-black/45">
            Unidad {fee.unit_code} · {fee.concept}
          </p>
        </div>
        <StatusBadge status={fee.status} />
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
        <div>
          <p className="text-black/45">Importe</p>
          <p className="mt-1 font-semibold">{money.format(Number(fee.amount))}</p>
        </div>
        <div>
          <p className="text-black/45">Pagado</p>
          <p className="mt-1 font-semibold">{money.format(Number(fee.paid_amount))}</p>
        </div>
        <div>
          <p className="text-black/45">Saldo</p>
          <p className="mt-1 font-semibold">{money.format(Number(fee.balance))}</p>
        </div>
      </div>
      <Observation fee={fee} />
      <div className="mt-4"><FeeActions fee={fee} onReport={onReport} mobile /></div>
    </article>
  )
}

function FeeActions({ fee, onReport, mobile = false }: { fee: Fee; onReport: () => void; mobile?: boolean }) {
  const receipt = fee.payment_reports.find((item) => item.status === 'Aprobado' && item.receipt_number)
  return (
    <div className={`flex gap-2 ${mobile ? 'flex-col' : 'justify-end'}`}>
      {receipt?.receipt_number && (
        <button
          className="btn-secondary whitespace-nowrap py-2"
          onClick={() => void openProtectedFile(`/payments/${receipt.id}/acknowledgement`, `${receipt.receipt_number}.pdf`)}
        >
          <Download size={15} />Recibo
        </button>
      )}
      {Number(fee.available_to_report) > 0 && (
        <button className={`${mobile ? 'btn-primary' : 'btn-secondary'} whitespace-nowrap py-2`} onClick={onReport}>
          Reportar
        </button>
      )}
    </div>
  )
}
