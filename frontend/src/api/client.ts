import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
  timeout: 15_000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('miedificio_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('miedificio_token')
      localStorage.removeItem('miedificio_user')
      window.dispatchEvent(new Event('miedificio:logout'))
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail[0]?.msg ?? 'Revisa los datos ingresados.'
  }
  return 'No pudimos completar la acción. Inténtalo nuevamente.'
}

