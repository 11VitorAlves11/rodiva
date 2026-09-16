import type { ButtonHTMLAttributes } from "react";

import { cx } from "../../lib/cx";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-copper text-white hover:bg-copper-dark",
  secondary: "border border-line text-ink hover:bg-sunken",
  ghost: "text-brand hover:bg-sunken",
  // Solid red would lose its contrast against the dark ground, so destructive
  // actions read as tinted text rather than a filled button.
  danger: "text-danger hover:bg-danger-soft",
};

const sizes: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2.5 text-sm",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

export function Button({ variant = "primary", size = "md", className, type = "button", ...rest }: Props) {
  return (
    <button
      type={type}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...rest}
    />
  );
}
