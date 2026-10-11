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
      { source: "/sources/:id", destination: `${v}/sources/:id`, permanent: false },
      { source: "/data", destination: `${v}/sources`, permanent: false },
      { source: "/history", destination: `${v}/activity`, permanent: false },
      { source: "/:stage(sources|processing|signals|experts|tasks|activity)", destination: `${v}/:stage`, permanent: false },
      { source: "/v/:vehicle/history", destination: "/v/:vehicle/activity", permanent: false },
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
