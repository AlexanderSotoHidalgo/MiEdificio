import type { FeeStatus, PaymentStatus } from '../types'

const styles: Record<FeeStatus | PaymentStatus, string> = {
  Pendiente: 'bg-amber-50 text-amber-800 ring-amber-600/15',
  'Pago en revisión': 'bg-blue-50 text-blue-700 ring-blue-600/15',
  Pagada: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  Aprobado: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  Observado: 'bg-rose-50 text-rose-700 ring-rose-600/15',
}

export function StatusBadge({ status }: { status: FeeStatus | PaymentStatus }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${styles[status]}`}>
      {status}
    </span>
  )
}

