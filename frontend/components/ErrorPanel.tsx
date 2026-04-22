interface Props {
  message: string
  onReset: () => void
}

export default function ErrorPanel({ message, onReset }: Props) {
  return (
    <div className="max-w-xl mx-auto">
      <div className="bg-red-50 border border-red-100 rounded-2xl px-6 py-5 flex items-start gap-4">
        <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <div>
          <p className="text-sm font-semibold text-red-800">Processing failed</p>
          <p className="mt-0.5 text-xs text-red-600">{message}</p>
        </div>
      </div>
      <div className="mt-5 flex justify-center">
        <button
          onClick={onReset}
          className="text-sm font-medium text-gray-600 border border-gray-200 bg-white rounded-xl px-5 py-2.5 hover:bg-gray-50 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
