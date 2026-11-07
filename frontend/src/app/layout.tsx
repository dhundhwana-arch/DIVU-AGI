import type { Metadata, Viewport } from "next";
import "./globals.css";
import { BrandHeader } from "@/components/BrandHeader";
import { BrandFooter } from "@/components/BrandFooter";
import { ServiceWorkerRegistrar } from "@/components/ServiceWorkerRegistrar";

const TITLE = "DIVU AI — Beyond Conversations. Towards Intelligence.";
const DESCRIPTION =
  "DIVU AI is a modular AI agent platform created by Divyesh Bambhaniya: multi-model routing, memory, retrieval, autonomous agents, tools and an internal developer studio. Installable on your home screen.";

export const metadata: Metadata = {
  metadataBase: new URL("https://divu.ai"),
  title: {
    default: TITLE,
    template: "%s · DIVU AI",
  },
  description: DESCRIPTION,
  applicationName: "DIVU AI",
  authors: [{ name: "DIVYESH BAMBHANIYA" }],
  creator: "DIVYESH BAMBHANIYA",
  keywords: [
    "DIVU AI",
    "AI platform",
    "AI agents",
    "multi-model routing",
    "RAG",
    "developer studio",
    "Divyesh Bambhaniya",
  ],
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.png", sizes: "64x64", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
    shortcut: ["/favicon.png"],
  },
  appleWebApp: {
    capable: true,
    title: "DIVU AI",
    statusBarStyle: "black-translucent",
  },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    siteName: "DIVU AI",
    type: "website",
    images: [{ url: "/og-cover.png", width: 1200, height: 630, alt: "DIVU AI" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: ["/og-cover.png"],
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#05060a",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
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
        <ServiceWorkerRegistrar />
      </body>
    </html>
  );
}
