import type { HTMLAttributes, ReactNode } from "react";

export default function Card({
  children,
  className = "",
  interactive = false,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { children: ReactNode; interactive?: boolean }) {
  return (
    <div
      className={`rounded-xl border border-border bg-surface p-4 shadow-sm shadow-black/[0.03] ${
        interactive ? "transition-all duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:shadow-md" : ""
      } ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
