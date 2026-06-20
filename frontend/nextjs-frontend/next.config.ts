import type { NextConfig } from "next";

const backendBaseUrl = process.env.BACKEND_INTERNAL_URL ?? "http://python-ai-core:8000";

const nextConfig: NextConfig = {
  experimental: {
    proxyClientMaxBodySize: "500mb",
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendBaseUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
