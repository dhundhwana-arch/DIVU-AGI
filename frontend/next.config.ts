import type { NextConfig } from "next";

const API_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The browser always calls relative /api/* URLs; Next proxies them to the FastAPI backend.
  // This keeps the app deployable behind any hostname (including sandbox previews) and means
  // no CORS configuration is required for first-party traffic.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_TARGET}/api/:path*`,
      },
      {
        source: "/health/:path*",
        destination: `${API_TARGET}/health/:path*`,
      },
    ];
  },
};

export default nextConfig;
