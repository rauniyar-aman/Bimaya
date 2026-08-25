import Image from "next/image";
import { cn } from "@/lib/cn";

const RATIO = 2172 / 724; // intrinsic aspect ratio of the wordmark (3:1)

interface LogoProps {
  /** Rendered height in px; width scales to keep the 3:1 ratio. */
  height?: number;
  priority?: boolean;
  className?: string;
}

export function Logo({ height = 40, priority = false, className }: LogoProps) {
  const width = Math.round(height * RATIO);
  return (
    <Image
      src="/bimaya-logo.png"
      alt="Bimaya — Online Insurance Made Easy"
      width={width}
      height={height}
      priority={priority}
      className={cn("w-auto", className)}
    />
  );
}
