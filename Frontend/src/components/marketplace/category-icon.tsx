import type { SVGProps } from "react";
import {
  CarIcon,
  HealthIcon,
  HeartIcon,
  PlaneIcon,
  ShieldCheckIcon,
} from "@/components/icons";

/**
 * Renders the glyph for a category `icon` key (set by the backend seed:
 * heart/health/car/plane), falling back to the shield for anything unmapped.
 *
 * Written as an explicit switch rather than a lookup that returns a component:
 * assigning a component to a variable and rendering `<Icon/>` trips the
 * `react-hooks/static-components` rule.
 */
export function CategoryIcon({
  iconKey,
  ...props
}: SVGProps<SVGSVGElement> & { iconKey?: string }) {
  switch (iconKey) {
    case "heart":
      return <HeartIcon {...props} />;
    case "health":
      return <HealthIcon {...props} />;
    case "car":
      return <CarIcon {...props} />;
    case "plane":
      return <PlaneIcon {...props} />;
    default:
      return <ShieldCheckIcon {...props} />;
  }
}
