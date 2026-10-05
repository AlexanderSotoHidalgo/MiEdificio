import { useAuth } from './AuthContext'
import { AdminPage } from './pages/AdminPage'
import { LoginPage } from './pages/LoginPage'
import { ResidentPage } from './pages/ResidentPage'

export default function App() {
  const { user } = useAuth()
  if (!user) return <LoginPage />
  return user.role === 'administrador' ? <AdminPage /> : <ResidentPage />
}

