import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required by the Dockerfile: emits .next/standalone with a minimal server.
  output: "standalone",
};

export default nextConfig;
