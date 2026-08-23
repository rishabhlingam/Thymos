function SkeletonBlock({ className = "" }) {
  return <div className={`animate-pulse bg-slate-200 rounded ${className}`} />
}

export function TableSkeleton({ rows = 6 }) {
  return (
    <div className="p-4 space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonBlock key={i} className="h-8 w-full" />
      ))}
    </div>
  )
}

export function ChartGridSkeleton({ count = 4 }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border border-slate-100 rounded-lg p-3 space-y-3">
          <SkeletonBlock className="h-4 w-1/3" />
          <SkeletonBlock className="h-64 w-full" />
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="space-y-4">
      <SkeletonBlock className="h-6 w-1/4" />
      <SkeletonBlock className="h-24 w-full" />
    </div>
  )
}

export default SkeletonBlock