import { TaxResult } from '@/lib/types'
import { TAX_EXEMPT_LABELS } from '@/lib/format'
import MetadataCards from './MetadataCards'
import LineItemsTable from './LineItemsTable'
import TotalsCard from './TotalsCard'

interface Props {
  result: TaxResult
  onReset: () => void
}

export default function ResultsPanel({ result, onReset }: Props) {
  const exemptLabel = result.tax_exempt_reason
    ? (TAX_EXEMPT_LABELS[result.tax_exempt_reason] ?? result.tax_exempt_reason)
    : null

  return (
    <div>
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={onReset} className="text-gray-400 hover:text-gray-700 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
          </button>
          <h2 className="text-lg font-bold text-gray-900">Invoice Results</h2>

          {result.tax_exempt && exemptLabel && (
            <span className="flex items-center gap-1 bg-amber-50 text-amber-700 border border-amber-200 text-xs font-medium px-2.5 py-0.5 rounded-full">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              {exemptLabel}
            </span>
          )}

          {result.extraction_method && (
            <span className="bg-blue-50 text-blue-700 border border-blue-100 text-xs font-medium px-2.5 py-0.5 rounded-full">
              {result.extraction_method === 'vision' ? 'Vision (scanned)' : 'PDF'}
            </span>
          )}
        </div>

        <button
          onClick={onReset}
          className="flex items-center gap-1.5 text-sm font-medium text-brand border border-brand rounded-lg px-4 py-1.5 hover:bg-brand-light transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Invoice
        </button>
      </div>

      <MetadataCards result={result} />
      <LineItemsTable items={result.line_item_taxes} />
      <TotalsCard
        subtotal={result.subtotal}
        totalTax={result.total_tax}
        grandTotal={result.grand_total}
      />
    </div>
  )
}
