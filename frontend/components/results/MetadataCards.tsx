import { TaxResult } from '@/lib/types'
import { fmtAddress } from '@/lib/format'

interface Props {
  result: TaxResult
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
      <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900 truncate">{value || '—'}</p>
    </div>
  )
}

export default function MetadataCards({ result }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      <Card label="Vendor"       value={result.vendor} />
      <Card label="Invoice #"    value={result.invoice_id} />
      <Card label="Date"         value={result.date} />
      <Card label="Due Date"     value={result.due_date ?? '—'} />
      <Card label="Bill To"      value={result.bill_to_name ?? '—'} />
      <Card label="Customer ID"  value={result.customer_id ?? '—'} />
      <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 col-span-2">
        <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Vendor Address</p>
        <p className="mt-1 text-sm font-semibold text-gray-900 truncate">{fmtAddress(result.vendor_address)}</p>
      </div>
    </div>
  )
}
