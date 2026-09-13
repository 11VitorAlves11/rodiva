/** Brand mark (spec §3.3): a wheel and a curved road, no monogram. `tone="brand"`
 * keeps the two-colour mark stable across themes; `tone="mono"` uses the
 * current text colour for contexts that need a single flat colour. */
export function Logo({ size = 32, tone = "brand", className }: { size?: number; tone?: "brand" | "mono"; className?: string }) {
  const wheel = tone === "brand" ? "var(--color-copper)" : "currentColor";
  const road = tone === "brand" ? "var(--color-graphite)" : "currentColor";
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
      <path d="M4 39 Q22 25 44 29" stroke={road} strokeWidth={5} strokeLinecap="round" />
      <circle cx={20} cy={19} r={12.5} stroke={wheel} strokeWidth={5} />
      <circle cx={20} cy={19} r={3.25} fill={wheel} />
    </svg>
  );
}
