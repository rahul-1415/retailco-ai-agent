'use client'

import { useEffect, useState } from 'react'

const STEPS = ['Extracting line items…', 'Classifying categories…', 'Calculating tax…']

export default function ProcessingPanel() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setStep(s => (s + 1) % STEPS.length), 2000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="flex flex-col items-center justify-center py-36 gap-5">
      <div className="w-12 h-12 rounded-full border-4 border-gray-100 border-t-brand spinner" />
      <div className="text-center">
        <p className="text-sm font-semibold text-gray-800">Processing invoice…</p>
        <p className="mt-1 text-xs text-gray-400 transition-all">{STEPS[step]}</p>
      </div>
    </div>
  )
}
