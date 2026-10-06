export const money = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })
export const shortDate = new Intl.DateTimeFormat('es-PE', {
  day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC',
})
export const monthName = new Intl.DateTimeFormat('es-PE', {
  month: 'long', year: 'numeric', timeZone: 'UTC',
})

export function monthFromPeriod(period: string) {
  return monthName.format(new Date(`${period}T00:00:00Z`))
}
