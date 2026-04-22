'use client'

import { InvoiceSummary } from '@/lib/types'
import { fmt, TAX_EXEMPT_LABELS } from '@/lib/format'

interface Props {
  invoices: InvoiceSummary[]
  onSelect: (id: string) => void
}

export default function HistoryPanel({ invoices, onSelect }: Props) {
  if (invoices.length === 0) return null

  return (
    <div className="mt-10">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Recent Invoices
      </h2>
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden divide-y divide-gray-100">
        {invoices.map((inv) => {
          const exemptLabel = inv.tax_exempt_reason
            ? (TAX_EXEMPT_LABELS[inv.tax_exempt_reason] ?? inv.tax_exempt_reason)
            : null

          return (
            <button
              key={inv.invoice_id}
              onClick={() => onSelect(inv.invoice_id)}
              className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors text-left"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{inv.vendor}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{inv.invoice_id} · {inv.date}</p>
                </div>
                {inv.tax_exempt && exemptLabel && (
                  <span className="shrink-0 flex items-center gap-1 bg-amber-50 text-amber-700 border border-amber-200 text-xs font-medium px-2 py-0.5 rounded-full">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                    </svg>
                    {exemptLabel}
                  </span>
                )}
              </div>
              <div className="shrink-0 ml-4 text-right">
                <p className="text-sm font-semibold text-gray-900">{fmt(inv.grand_total)}</p>
                {!inv.tax_exempt && (
                  <p className="text-xs text-gray-400 mt-0.5">incl. tax</p>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
