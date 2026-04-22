import { Address } from '@/lib/types'

export function fmt(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export function fmtAddress(addr: Address | null | undefined): string {
  if (!addr) return '—'
  return [addr.street, addr.city, addr.state, addr.zip_code].filter(Boolean).join(', ') || '—'
}

export const TAX_EXEMPT_LABELS: Record<string, string> = {
  pre_taxed: 'Tax already applied',
  used_products: 'Used goods — tax exempt',
}
