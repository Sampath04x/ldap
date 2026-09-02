import { FileQuestion } from 'lucide-react'

export function EmptyState({ message, description }: { message: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center text-gray-500">
      <FileQuestion className="w-12 h-12 text-gray-300 mb-4" />
      <h3 className="text-lg font-medium text-gray-900">{message}</h3>
      {description && <p className="mt-1">{description}</p>}
    </div>
  )
}
