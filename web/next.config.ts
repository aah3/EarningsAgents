import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  output: "standalone",   // enables minimal Docker image via multi-stage build
};

export default withSentryConfig(nextConfig, {
  // Source map upload is skipped automatically when SENTRY_AUTH_TOKEN is unset
  // (e.g. local dev) — only takes effect once a Sentry org/project is wired up.
  silent: true,
});
