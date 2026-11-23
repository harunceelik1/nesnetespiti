import * as React from "react";
import { cn } from "@/lib/utils";

/** shadcn Tabs/ToggleGroup görünümünde, yerel düğmelerle çalışan seçim grubu. */
function Segmented({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("inline-flex w-full items-center rounded-md border border-input p-0.5 text-muted-foreground", className)} {...props} />;
}

function segmentClass(selected: boolean, className?: string) {
  return cn(
    "inline-flex h-8 flex-1 cursor-pointer items-center justify-center gap-1.5 whitespace-nowrap rounded-[3px] px-3 text-sm font-medium outline-none transition-all",
    "focus-visible:ring-[3px] focus-visible:ring-ring/50 has-[:focus-visible]:ring-[3px] has-[:focus-visible]:ring-ring/50",
    "disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4",
    selected ? "bg-foreground text-background" : "hover:bg-muted hover:text-foreground",
    className,
  );
}

export { Segmented, segmentClass };
