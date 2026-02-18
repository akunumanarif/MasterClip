import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const isProd = process.env.NODE_ENV === "production";
    const backendUrl = process.env.BACKEND_URL || (isProd ? "http://backend:8000" : "http://127.0.0.1:8000");
    console.log(`Rewrites called. NODE_ENV: ${process.env.NODE_ENV}, BACKEND_URL: ${process.env.BACKEND_URL}, Resolved: ${backendUrl}`);

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/output/:path*",
        destination: `${backendUrl}/output/:path*`,
      },
      {
        source: "/clips/:path*",
        destination: `${backendUrl}/clips/:path*`,
      },
    ];
  },
};

export default nextConfig;
