import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from './api/client'
import type { AuthResponse, User } from './types'

interface AuthContextValue {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function storedUser(): User | null {
  try {
    const raw = localStorage.getItem('miedificio_user')
    return raw ? (JSON.parse(raw) as User) : null
  } catch { return null }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(storedUser)
  const logout = useCallback(() => {
    const refresh = localStorage.getItem('miedificio_refresh')
    if (refresh) void api.post('/auth/logout', { refresh_token: refresh }).catch(() => undefined)
    localStorage.removeItem('miedificio_token')
    localStorage.removeItem('miedificio_refresh')
    localStorage.removeItem('miedificio_user')
    setUser(null)
  }, [])
  useEffect(() => {
    window.addEventListener('miedificio:logout', logout)
    return () => window.removeEventListener('miedificio:logout', logout)
  }, [logout])
  const login = async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password })
    const { data } = await api.post<AuthResponse>('/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    localStorage.setItem('miedificio_token', data.access_token)
    localStorage.setItem('miedificio_refresh', data.refresh_token)
    localStorage.setItem('miedificio_user', JSON.stringify(data.user))
    setUser(data.user)
  }
  return <AuthContext.Provider value={useMemo(() => ({ user, login, logout }), [user, logout])}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return context
}
