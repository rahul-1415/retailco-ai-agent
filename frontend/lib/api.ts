import { TaxResult, InvoiceSummary } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:3000'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function processInvoice(file: File): Promise<TaxResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/invoices`, { method: 'POST', body: form })
  return handleResponse<TaxResult>(res)
}

export async function lookupInvoice(id: string): Promise<TaxResult> {
  const res = await fetch(`${API_BASE}/invoices/${encodeURIComponent(id)}`)
  if (res.status === 404) throw new Error('Invoice not found')
  return handleResponse<TaxResult>(res)
}

export async function listInvoices(): Promise<InvoiceSummary[]> {
  const res = await fetch(`${API_BASE}/invoices`)
  return handleResponse<InvoiceSummary[]>(res)
}
