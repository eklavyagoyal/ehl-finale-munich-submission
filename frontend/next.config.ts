import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker image (frontend/Dockerfile).
  output: "standalone",
  // Old routes from before the vehicle moved into the URL (/v/g60/...). Query strings pass through.
  async redirects() {
    const v = "/v/g60";
    return [
      { source: "/pipeline", destination: v, permanent: false },
      { source: "/requirements", destination: `${v}/decision`, permanent: false },
      { source: "/requirements/:id", destination: `${v}/decision/:id`, permanent: false },
      { source: "/requirements/:id/:tab", destination: `${v}/decision/:id/:tab`, permanent: false },
      { source: "/data", destination: "/sources", permanent: false },
      { source: "/history", destination: "/activity", permanent: false },
      { source: "/:stage(signals|experts|tasks)", destination: `${v}/:stage`, permanent: false },
      // Activity is vehicle-independent now and lives at /activity.
      { source: "/v/:vehicle/history", destination: "/activity", permanent: false },
      { source: "/v/:vehicle/activity", destination: "/activity", permanent: false },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
