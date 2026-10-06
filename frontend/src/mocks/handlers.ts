import { http, HttpResponse } from 'msw'

const api = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export const handlers = [
  http.get(`${api}/fees/my-account`, () => HttpResponse.json([])),
  http.get(`${api}/payments`, () => HttpResponse.json([])),
  http.get(`${api}/reports/summary`, () => HttpResponse.json({ issued: '0.00', collected: '0.00', pending: '0.00', currency: 'PEN' })),
]
