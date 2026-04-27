import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",   // enables minimal Docker image via multi-stage build
};

export default nextConfig;
