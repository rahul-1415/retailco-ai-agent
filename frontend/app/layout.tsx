import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'RetailCo Tax Agent',
  description: 'Automated invoice tax classification and calculation',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen antialiased">{children}</body>
    </html>
  )
}
