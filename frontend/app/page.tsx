'use client'

import { useState } from 'react'
import Header from '@/components/Header'
import UploadPanel from '@/components/UploadPanel'
import ProcessingPanel from '@/components/ProcessingPanel'
import ErrorPanel from '@/components/ErrorPanel'
import ResultsPanel from '@/components/results/ResultsPanel'
import { processInvoice, lookupInvoice } from '@/lib/api'
import { TaxResult } from '@/lib/types'

type View = 'upload' | 'processing' | 'error' | 'results'

export default function Home() {
  const [view, setView] = useState<View>('upload')
  const [result, setResult] = useState<TaxResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleProcess(file: File) {
    setView('processing')
    try {
      const data = await processInvoice(file)
      setResult(data)
      setView('results')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setView('error')
    }
  }

  async function handleLookup(id: string) {
    if (!id.trim()) return
    setView('processing')
    try {
      const data = await lookupInvoice(id.trim())
      setResult(data)
      setView('results')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setView('error')
    }
  }

  function reset() {
    setView('upload')
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onLookup={handleLookup} />
      <main className="max-w-6xl mx-auto px-6 py-10">
        {view === 'upload'     && <UploadPanel onProcess={handleProcess} />}
        {view === 'processing' && <ProcessingPanel />}
        {view === 'error'      && <ErrorPanel message={error!} onReset={reset} />}
        {view === 'results'    && result && <ResultsPanel result={result} onReset={reset} />}
      </main>
    </div>
  )
}
