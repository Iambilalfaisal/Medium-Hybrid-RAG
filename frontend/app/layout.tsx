import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Medium Hybrid RAG",
  description: "Hybrid search + reranked RAG over the Medium Articles dataset",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-zinc-50 text-zinc-900">
        <nav className="flex items-center gap-6 border-b border-zinc-200 bg-white px-6 py-3">
          <span className="font-semibold">Medium Hybrid RAG</span>
          <Link href="/chat" className="text-sm text-zinc-600 hover:text-zinc-900">
            Chat
          </Link>
          <Link href="/admin" className="text-sm text-zinc-600 hover:text-zinc-900">
            Admin
          </Link>
          <Link href="/eval" className="text-sm text-zinc-600 hover:text-zinc-900">
            Eval Dashboard
          </Link>
        </nav>
        <main className="flex flex-1 flex-col">{children}</main>
      </body>
    </html>
  );
}
