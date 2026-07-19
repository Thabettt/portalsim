import React from "react";
import { cn } from "../../lib/utils";

const Badge = React.forwardRef(({ className, variant = "default", ...props }, ref) => {
  const baseStyles = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2";
  
  const variants = {
    default: "border-transparent bg-primary text-primary-foreground",
    secondary: "border-transparent bg-secondary text-secondary-foreground",
    destructive: "border-transparent bg-destructive text-destructive-foreground",
    outline: "text-foreground",
    success: "border-transparent bg-emerald-500/15 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400",
    warning: "border-transparent bg-amber-500/15 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
    danger: "border-transparent bg-red-500/15 text-red-700 dark:bg-red-500/10 dark:text-red-400",
  };

  return (
    <div ref={ref} className={cn(baseStyles, variants[variant], className)} {...props} />
  );
});

Badge.displayName = "Badge";

export { Badge };
