import { AlertCircle } from 'lucide-react'

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex flex-col items-center justify-center space-y-4 text-center">
      <AlertCircle className="w-10 h-10 text-red-500" />
      <div className="text-red-800 font-medium">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors font-medium text-sm"
        >
          Retry
        </button>
      )}
    </div>
  )
}
