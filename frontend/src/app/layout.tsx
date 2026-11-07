import type { Metadata, Viewport } from "next";
import "./globals.css";
import { BrandHeader } from "@/components/BrandHeader";
import { BrandFooter } from "@/components/BrandFooter";

export const metadata: Metadata = {
  title: "DIVU AI — Beyond Conversations. Towards Intelligence.",
  description:
    "DIVU AI is a modular AI agent platform created by Divyesh Bambhaniya: multi-model routing, memory, RAG, agents, tools and an internal developer studio.",
  applicationName: "DIVU AI",
  authors: [{ name: "DIVYESH BAMBHANIYA" }],
};

export const viewport: Viewport = {
  themeColor: "#05060a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <div className="flex min-h-screen flex-col">
          <BrandHeader />
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
            {children}
          </main>
          <BrandFooter />
        </div>
      </body>
    </html>
  );
}
