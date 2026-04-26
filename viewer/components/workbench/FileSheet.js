import { cn } from "../../lib/cn";

export default function FileSheet({
  open,
  title,
  isDesktop,
  width,
  bodyClassName,
  children
}) {
  if (!open) {
    return null;
  }

  const sheetStyle = isDesktop
    ? { width: `${Math.max(0, Number(width) || 0)}px` }
    : { width: "min(24rem, calc(100vw - 0.75rem))" };

  return (
    <aside
      className="cad-glass-surface pointer-events-auto relative z-30 flex h-full shrink-0 max-w-[calc(100vw-0.75rem)] flex-col border-l border-sidebar-border text-sidebar-foreground"
      style={sheetStyle}
      aria-label={title}
    >
      <div className={cn("min-h-0 flex-1 overflow-y-auto", bodyClassName)}>
        {children}
      </div>
    </aside>
  );
}
