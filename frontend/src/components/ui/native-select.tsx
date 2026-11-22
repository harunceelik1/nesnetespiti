import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/** shadcn NativeSelect: yerel <select>; klavye, mobil ve testlerde tarayıcı davranışı korunur. */
function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <div className="relative w-full">
      <select data-slot="native-select" className={cn(
        "h-10 w-full appearance-none rounded-md border border-input bg-background pl-3 pr-9 text-sm shadow-xs outline-none disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
        className)} {...props} />
      <ChevronDown aria-hidden="true" className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}

export { NativeSelect };
