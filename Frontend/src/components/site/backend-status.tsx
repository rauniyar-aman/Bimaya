"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

type State = "checking" | "online" | "offline";

export function BackendStatus({ className }: { className?: string }) {
  const [state, setState] = useState<State>("checking");
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .health()
      .then((res) => {
        if (!active) return;
        setState("online");
        setVersion(res.version);
      })
      .catch(() => {
        if (active) setState("offline");
      });
    return () => {
      active = false;
    };
  }, []);

  const view = {
    checking: { dot: "bg-slate-300", text: "text-muted", label: "Checking API…" },
    online: {
      dot: "bg-success-500",
      text: "text-success-700",
      label: version ? `API connected · v${version}` : "API connected",
    },
    offline: { dot: "bg-slate-400", text: "text-muted", label: "API offline" },
  }[state];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 text-xs font-medium",
        view.text,
        className,
      )}
    >
      <span className="relative flex h-2 w-2">
        {state === "online" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success-400 opacity-60" />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", view.dot)} />
      </span>
      {view.label}
    </span>
  );
}
