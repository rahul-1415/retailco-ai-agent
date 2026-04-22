export interface Address {
  street: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  phone: string | null
}

export interface LineItemTax {
  description: string
  quantity: number | null
  unit_price: number | null
  total_amount: number
  category: string
  tax_rate: number
  tax_amount: number
}

export interface InvoiceSummary {
  invoice_id: string
  vendor: string
  date: string
  grand_total: number
  tax_exempt: boolean
  tax_exempt_reason: string | null
}

export interface TaxResult {
  invoice_id: string
  vendor: string
  vendor_address: Address | null
  bill_to_name: string | null
  bill_to_address: Address | null
  customer_id: string | null
  date: string
  due_date: string | null
  line_item_taxes: LineItemTax[]
  subtotal: number
  total_tax: number
  grand_total: number
  tax_exempt: boolean
  tax_exempt_reason: string | null
  extraction_method: string
}
