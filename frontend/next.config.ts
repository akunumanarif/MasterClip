import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    console.log("Rewrites called. BACKEND_URL:", process.env.BACKEND_URL);
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
