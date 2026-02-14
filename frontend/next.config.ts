import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
      {
        source: "/output/:path*",
        destination: "http://127.0.0.1:8000/output/:path*",
      },
    ];
  },
};

export default nextConfig;
