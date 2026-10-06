import axios, { type AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import type { AuthResponse } from '../types'

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export const api = axios.create({ baseURL, timeout: 20_000 })

export const orvalClient = async <T>(config: AxiosRequestConfig, options?: AxiosRequestConfig): Promise<T> => {
  const response = await api({ ...config, ...options, headers: { ...config.headers, ...options?.headers } })
  return response.data as T
}
let refreshPromise: Promise<string> | null = null

function clearSession() {
  localStorage.removeItem('miedificio_token')
  localStorage.removeItem('miedificio_refresh')
  localStorage.removeItem('miedificio_user')
  window.dispatchEvent(new Event('miedificio:logout'))
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('miedificio_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    if (error.response?.status === 401 && original && !original._retry && !original.url?.includes('/auth/')) {
      original._retry = true
      const refreshToken = localStorage.getItem('miedificio_refresh')
      if (!refreshToken) {
        clearSession()
        return Promise.reject(error)
      }
      refreshPromise ??= axios
        .post<AuthResponse>(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })
        .then(({ data }) => {
          localStorage.setItem('miedificio_token', data.access_token)
          localStorage.setItem('miedificio_refresh', data.refresh_token)
          localStorage.setItem('miedificio_user', JSON.stringify(data.user))
          return data.access_token
        })
        .finally(() => { refreshPromise = null })
      try {
        const token = await refreshPromise
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      } catch {
        clearSession()
      }
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail[0]?.msg ?? 'Revisa los datos ingresados.'
    if (error.response?.status === 403) return 'No tienes permisos para realizar esta acción.'
  }
  if (error instanceof Error && error.message) return error.message
  return 'No pudimos completar la acción. Inténtalo nuevamente.'
}
