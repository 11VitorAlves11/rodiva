import { cn } from "../../lib/cn";

export function Skeleton({ className, lines = 3 }: { className?: string; lines?: number }) {
  return (
    <div className={cn("animate-pulse space-y-2", className)} role="status" aria-label="A carregar">
      {Array.from({ length: lines }, (_, index) => (
        <div key={index} className="h-4 rounded bg-sunken" />
      ))}
    </div>
  );
}
