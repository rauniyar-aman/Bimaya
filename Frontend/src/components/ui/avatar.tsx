import { cn } from "@/lib/cn";

type AvatarSize = "sm" | "md" | "lg";
type AvatarShape = "circle" | "square";

/** Box and text sizing per named size. */
const SIZES: Record<AvatarSize, string> = {
  sm: "h-8 w-8 text-xs",
  md: "h-12 w-12 text-sm",
  lg: "h-20 w-20 text-xl",
};

/** Corner rounding per shape: round for people, softened square for logos. */
const SHAPES: Record<AvatarShape, string> = {
  circle: "rounded-full",
  square: "rounded-lg",
};

interface AvatarProps {
  /** Image URL to show. When absent, the initials fallback is rendered. */
  src?: string | null;
  /** Initials (or a short label) shown when there is no image. */
  fallback: string;
  /** Accessible name for the image. Falls back to the initials. */
  alt?: string;
  size?: AvatarSize;
  /** `circle` (default) for user avatars; `square` for company logos. */
  shape?: AvatarShape;
  className?: string;
}

/**
 * A round avatar: the uploaded picture when one exists, otherwise the user's
 * initials on the brand colour. Kept free of any user type so it can back both
 * customer avatars and provider logos (pass `shape="square"` for a logo). Uses a
 * plain `<img>` — the source is an absolute backend media URL, not a bundled
 * asset.
 */
export function Avatar({
  src,
  fallback,
  alt,
  size = "md",
  shape = "circle",
  className,
}: AvatarProps) {
  const base = cn(
    "inline-flex shrink-0 items-center justify-center overflow-hidden",
    SIZES[size],
    SHAPES[shape],
    className,
  );

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={alt ?? fallback}
        className={cn(base, "border border-line object-cover")}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className={cn(base, "bg-brand-500 font-semibold text-white")}
    >
      {fallback}
    </span>
  );
}
