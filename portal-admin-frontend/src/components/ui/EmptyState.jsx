import React from "react";
import { cn } from "../../lib/utils";
import { SearchX } from "lucide-react";

export function EmptyState({ icon: Icon = SearchX, title, description, action, className }) {
  return (
    <div className={cn("flex flex-col items-center justify-center p-8 text-center animate-fade-in-up", className)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-medium tracking-tight text-foreground">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
