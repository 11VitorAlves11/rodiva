import { cn } from "../../lib/cn";
import type { Tag } from "../../lib/api/types";

/**
 * A tag's colour is chosen by the member, so it cannot be trusted to contrast
 * with anything: filling the chip with it would leave the label unreadable for
 * half the palette, and differently so in each theme. The chip therefore keeps
 * the semantic surface and text tokens, and the colour identifies the tag as a
 * dot — legible in light and dark whatever was picked.
 */
export function TagChip({
  tag,
  onRemove,
  removeLabel,
  className,
}: {
  tag: Tag;
  onRemove?: () => void;
  removeLabel?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-sunken px-2 py-0.5 text-xs font-semibold text-ink",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="size-2 shrink-0 rounded-full ring-1 ring-inset ring-black/10"
        style={{ backgroundColor: tag.color }}
      />
      {tag.name}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={removeLabel ?? tag.name}
          className="-mr-0.5 rounded-full px-1 text-ink-muted transition-colors hover:text-danger"
        >
          ×
        </button>
      )}
    </span>
  );
}
