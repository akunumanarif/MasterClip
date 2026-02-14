import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/:path*`,
      },
      {
        source: "/output/:path*",
        destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/output/:path*`,
      },
    ];
  },
};

export default nextConfig;
