import clsx from 'clsx'

function Bone({ className }) {
  return (
    <div className={clsx('animate-pulse rounded bg-gray-200 dark:bg-gray-700/60', className)} />
  )
}

export function SkeletonCard() {
  return (
    <div className="p-3 space-y-2">
      <Bone className="aspect-[2/3] w-full rounded-lg" />
      <Bone className="h-3 w-4/5" />
      <Bone className="h-3 w-3/5" />
    </div>
  )
}

export function SkeletonListRow() {
  return (
    <div className="flex items-center gap-4 p-3">
      <Bone className="shrink-0 h-16 w-12 rounded-md" />
      <div className="flex-1 space-y-2">
        <Bone className="h-3.5 w-2/5" />
        <Bone className="h-3 w-1/3" />
      </div>
      <Bone className="hidden md:block h-3 w-28" />
    </div>
  )
}

export default function Skeleton({ className }) {
  return <Bone className={className} />
}
