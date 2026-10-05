export type Role = 'administrador' | 'residente'

export interface User {
  id: number
  full_name: string
  email: string
  role: Role
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export type FeeStatus = 'Pendiente' | 'Pago en revisión' | 'Pagada'
export type PaymentStatus = 'Pendiente' | 'Aprobado' | 'Observado'

export interface PaymentSummary {
  id: number
  status: PaymentStatus
  amount: string
  operation_number: string
  review_comment: string | null
  created_at: string
}

export interface Fee {
  id: number
  unit_id: number
  unit_code: string
  period_year: number
  period_month: number
  due_date: string
  amount: string
  paid_amount: string
  balance: string
  status: FeeStatus
  payment_reports: PaymentSummary[]
}

export interface PaymentReport {
  id: number
  fee_id: number
  unit_code: string
  resident_name: string
  resident_email: string
  amount: string
  payment_date: string
  operation_number: string
  receipt_original_name: string
  receipt_content_type: string
  status: PaymentStatus
  review_comment: string | null
  reviewed_at: string | null
  created_at: string
}
