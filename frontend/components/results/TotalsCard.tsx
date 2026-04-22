import { fmt } from '@/lib/format'

interface Props {
  subtotal: number
  totalTax: number
  grandTotal: number
}

export default function TotalsCard({ subtotal, totalTax, grandTotal }: Props) {
  return (
    <div className="flex justify-end">
      <div className="bg-white border border-gray-200 rounded-2xl px-6 py-5 w-72 space-y-3">
        <Row label="Subtotal"    value={fmt(subtotal)} />
        <Row label="Total Tax"   value={fmt(totalTax)} />
        <div className="border-t border-gray-100 pt-3 flex justify-between">
          <span className="text-sm font-semibold text-gray-900">Grand Total</span>
          <span className="text-sm font-bold text-gray-900">{fmt(grandTotal)}</span>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  )
}
