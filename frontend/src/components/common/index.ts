/** 通用加载/空状态组件 */

export function LoadingSpinner({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        <p className="text-sm text-gray-400">{text}</p>
      </div>
    </div>
  );
}

export function EmptyState({ icon, title, description }: { icon: string; title: string; description?: string }) {
  return (
    <div className="text-center py-16">
      <span className="text-4xl mb-3 block">{icon}</span>
      <h3 className="text-lg font-medium text-gray-500">{title}</h3>
      {description && <p className="text-gray-400 text-sm mt-1">{description}</p>}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
      <span className="text-red-500 text-lg mt-0.5">⚠️</span>
      <div className="flex-1">
        <p className="text-sm text-red-700">{message}</p>
        {onRetry && (
          <button onClick={onRetry} className="text-sm text-red-600 underline mt-1 hover:text-red-800">
            重试
          </button>
        )}
      </div>
    </div>
  );
}
