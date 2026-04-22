import { LineItemTax } from '@/lib/types'
import { fmt } from '@/lib/format'

interface Props {
  items: LineItemTax[]
}

export default function LineItemsTable({ items }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden mb-5">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50">
            {['Description', 'Qty', 'Unit Price', 'Amount', 'Category', 'Tax Rate', 'Tax'].map((h, i) => (
              <th
                key={h}
                className={`text-xs font-semibold text-gray-500 uppercase tracking-wide py-3 whitespace-nowrap
                  ${i === 0 ? 'text-left px-5' : i === 6 ? 'text-right px-5' : 'text-right px-4'}`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => {
            const zeroTax = item.tax_rate === 0
            return (
              <tr
                key={i}
                className={`border-b border-gray-100 last:border-0 hover:bg-green-50/30 transition-colors ${i % 2 !== 0 ? 'bg-gray-50/50' : ''}`}
              >
                <td className="px-5 py-3 text-gray-800 max-w-xs">
                  <span className="line-clamp-2">{item.description}</span>
                </td>
                <td className="px-4 py-3 text-right text-gray-600 whitespace-nowrap">
                  {item.quantity ?? '—'}
                </td>
                <td className="px-4 py-3 text-right text-gray-600 whitespace-nowrap">
                  {fmt(item.unit_price)}
                </td>
                <td className="px-4 py-3 text-right text-gray-800 font-medium whitespace-nowrap">
                  {fmt(item.total_amount)}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-block bg-gray-100 text-gray-700 text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap">
                    {item.category}
                  </span>
                </td>
                <td className={`px-4 py-3 text-right font-medium whitespace-nowrap ${zeroTax ? 'text-brand' : 'text-gray-700'}`}>
                  {item.tax_rate}%
                </td>
                <td className={`px-5 py-3 text-right font-medium whitespace-nowrap ${zeroTax ? 'text-brand' : 'text-gray-800'}`}>
                  {fmt(item.tax_amount)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
