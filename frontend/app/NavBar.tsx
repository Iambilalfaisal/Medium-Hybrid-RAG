"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/chat", label: "Chat" },
  { href: "/admin", label: "Admin" },
  { href: "/eval", label: "Eval Dashboard" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-10 flex items-center gap-1 border-b border-border bg-surface/80 px-6 py-3 backdrop-blur-md">
      <div className="mr-4 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-xs font-bold text-white">
          M
        </span>
        <span className="font-semibold tracking-tight">Medium Hybrid RAG</span>
      </div>

      {LINKS.map((link) => {
        const active = pathname?.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`relative rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              active ? "text-accent" : "text-text-muted hover:text-text"
            }`}
          >
            {link.label}
            {active && <span className="absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-accent" />}
          </Link>
        );
      })}
    </nav>
  );
}
