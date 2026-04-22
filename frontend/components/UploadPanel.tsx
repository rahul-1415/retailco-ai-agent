'use client'

import { useState, useRef, DragEvent, ChangeEvent } from 'react'

interface Props {
  onProcess: (file: File) => void
}

export default function UploadPanel({ onProcess }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function setSelected(f: File) {
    if (f.type === 'application/pdf') setFile(f)
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault()
    setDragging(true)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setSelected(f)
  }

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) setSelected(f)
  }

  function clear() {
    setFile(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div>
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Invoice Tax Calculator</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Upload a vendor invoice — the agent extracts line items, assigns tax categories, and calculates tax payable.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-2xl bg-white cursor-pointer flex flex-col items-center justify-center gap-4 py-20 px-8 transition-colors ${
          dragging ? 'border-brand bg-brand-light' : 'border-gray-200 hover:border-gray-300'
        }`}
      >
        <div className="w-14 h-14 rounded-full bg-gray-50 flex items-center justify-center">
          <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-gray-700">
            Drop a PDF here, or <span className="text-brand underline underline-offset-2">browse</span>
          </p>
          <p className="mt-1 text-xs text-gray-400">Supports native and scanned PDFs</p>
        </div>
        <input ref={inputRef} type="file" accept="application/pdf" className="hidden" onChange={onFileChange} />
      </div>

      {/* Selected file */}
      {file && (
        <div className="mt-4 bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-800">{file.name}</p>
              <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          </div>
          <button onClick={e => { e.stopPropagation(); clear() }} className="text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Process button */}
      <div className="mt-5 flex justify-center">
        <button
          onClick={() => file && onProcess(file)}
          disabled={!file}
          className="flex items-center gap-2 bg-brand text-white text-sm font-semibold px-6 py-2.5 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed hover:bg-brand-dark transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
          </svg>
          Process Invoice
        </button>
      </div>
    </div>
  )
}
