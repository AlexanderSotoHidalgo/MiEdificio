import { useAuth } from './AuthContext'
import { AccountPage } from './features/account/AccountPage'
import { LoginPage } from './features/auth/LoginPage'
import { AdminPaymentsPage } from './features/reconciliation/AdminPaymentsPage'

export default function App() {
  const { user } = useAuth()
  if (!user) return <LoginPage />
  return user.role === 'administrador' ? <AdminPaymentsPage /> : <AccountPage />
}
