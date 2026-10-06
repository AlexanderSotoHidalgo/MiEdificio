export type Role = 'administrador' | 'residente' | 'tesorero' | 'portero'

export interface User {
  id: number
  building_id: number | null
  full_name: string
  email: string
  role: Role
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export type FeeStatus = 'Pendiente' | 'Pago en revisión' | 'Pagada' | 'Vencida' | 'Anulada'
export type PaymentStatus = 'En revisión' | 'Aprobado' | 'Observado'

export interface PaymentSummary {
  id: number
  status: PaymentStatus
  amount: string
  operation_number: string
  observation_reason: string | null
  receipt_number: string | null
  created_at: string
}

export interface Fee {
  id: number
  unit_id: number
  unit_code: string
  concept: string
  period: string
  due_date: string
  amount: string
  paid_amount: string
  in_review_amount: string
  balance: string
  available_to_report: string
  currency: 'PEN'
  status: FeeStatus
  payment_reports: PaymentSummary[]
}

export interface PaymentAllocation {
  fee_id: number
  unit_code: string
  concept: string
  period: string
  amount: string
}

export interface PaymentReport {
  id: number
  resident_id: number
  resident_name: string
  resident_email: string
  amount: string
  currency: string
  payment_date: string
  operation_number: string
  original_filename: string
  content_type: string
  status: PaymentStatus
  observation_reason: string | null
  reviewed_at: string | null
  created_at: string
  allocations: PaymentAllocation[]
  receipt_number: string | null
}

export interface FinancialSummary {
  issued: string
  collected: string
  pending: string
  currency: string
}
