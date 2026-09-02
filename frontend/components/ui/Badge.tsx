import type { ReactNode } from "react";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

const TONE_STYLES: Record<Tone, string> = {
  neutral: "bg-surface-2 text-text-muted",
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
};

export default function Badge({
  children,
  tone = "neutral",
  pulse = false,
}: {
  children: ReactNode;
  tone?: Tone;
  pulse?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium tracking-wide ${TONE_STYLES[tone]}`}
    >
      {pulse && <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-current" />}
      {children}
    </span>
  );
}
