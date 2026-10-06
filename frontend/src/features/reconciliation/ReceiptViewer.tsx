import { Loader2, Minus, Plus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, errorMessage } from '../../api/client'
import type { PaymentReport } from '../../types'

export function ReceiptViewer({ payment, onClose }: { payment: PaymentReport; onClose: () => void }) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState('')
  const [zoom, setZoom] = useState(1)
  useEffect(() => {
    let objectUrl = ''
    api.get<Blob>(`/payments/${payment.id}/receipt`, { responseType: 'blob' })
      .then(({ data }) => { objectUrl = URL.createObjectURL(data); setUrl(objectUrl) })
      .catch((reason) => setError(errorMessage(reason)))
    const keyboard = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', keyboard)
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); window.removeEventListener('keydown', keyboard) }
  }, [payment.id, onClose])
  return <div className="fixed inset-0 z-50 grid place-items-center bg-ink/70 p-3" role="dialog" aria-modal="true" aria-labelledby="receipt-title"><div className="flex h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-paper"><header className="flex items-center justify-between border-b bg-white px-4 py-3"><div><h2 id="receipt-title" className="font-semibold">Comprobante de {payment.resident_name}</h2><p className="text-xs text-black/45">Operación {payment.operation_number}</p></div><div className="flex items-center gap-1"><button className="rounded-lg p-2 hover:bg-black/5" aria-label="Alejar" onClick={() => setZoom((value) => Math.max(.5, value - .25))}><Minus /></button><span className="w-12 text-center text-xs">{Math.round(zoom * 100)}%</span><button className="rounded-lg p-2 hover:bg-black/5" aria-label="Acercar" onClick={() => setZoom((value) => Math.min(3, value + .25))}><Plus /></button><button className="ml-2 rounded-lg p-2 hover:bg-black/5" aria-label="Cerrar visor" onClick={onClose}><X /></button></div></header><div className="flex-1 overflow-auto bg-slate-200 p-5">{error ? <p className="rounded-xl bg-rose-50 p-4 text-rose-700">{error}</p> : !url ? <div className="grid h-full place-items-center"><Loader2 className="animate-spin" /></div> : payment.content_type === 'application/pdf' ? <iframe title="Comprobante PDF" src={url} className="mx-auto h-full min-h-[600px] w-full origin-top bg-white" style={{ transform: `scale(${zoom})`, width: `${100 / zoom}%` }} /> : <img src={url} alt="Comprobante de pago" className="mx-auto origin-top shadow-xl" style={{ transform: `scale(${zoom})` }} />}</div></div></div>
}
