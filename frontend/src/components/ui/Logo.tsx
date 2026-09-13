/** Brand mark (spec §3.3): a spoked wheel and a curved road, no monogram.
 * `tone="brand"` keeps the two-colour mark stable across themes; `tone="mono"`
 * uses the current text colour for contexts that need a single flat colour. */
export function Logo({ size = 32, tone = "brand", className }: { size?: number; tone?: "brand" | "mono"; className?: string }) {
  const wheel = tone === "brand" ? "var(--color-graphite)" : "currentColor";
  const road = tone === "brand" ? "var(--color-copper)" : "currentColor";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      role="img"
      aria-label="Rodiva"
      className={className}
    >
      <circle cx={24} cy={22} r={14} stroke={wheel} strokeWidth={3} />
      <path d="M24 22V8M24 22 36.1 29M24 22 11.9 29" stroke={wheel} strokeWidth={2.25} strokeLinecap="round" />
      <circle cx={24} cy={22} r={2.5} fill={wheel} />
      <path d="M6 38Q24 20 42 10" stroke={road} strokeWidth={5} strokeLinecap="round" />
    </svg>
  );
}
