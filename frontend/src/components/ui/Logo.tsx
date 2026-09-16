/** Official Rodiva wheel-and-road symbol supplied with the product identity. */
export function Logo({ size = 32, tone = "brand", className = "" }: { size?: number; tone?: "brand" | "mono"; className?: string }) {
  const lightSource = tone === "brand" ? "/icons/symbol-light.svg" : "/icons/symbol-mono-black.svg";
  const darkSource = tone === "brand" ? "/icons/symbol-dark.svg" : "/icons/symbol-mono-white.svg";

  return (
    <span role="img" aria-label="Rodiva" className={`inline-grid shrink-0 place-items-center ${className}`} style={{ width: size, height: size }}>
      <img src={lightSource} alt="" width={size} height={size} className="col-start-1 row-start-1 h-full w-full dark:hidden" />
      <img src={darkSource} alt="" width={size} height={size} className="hidden col-start-1 row-start-1 h-full w-full dark:block" />
    </span>
  );
}
