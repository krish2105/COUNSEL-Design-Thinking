import type { NextConfig } from "next";

/* Where the API lives.
 *
 * NEXT_PUBLIC_API_URL wins, so any environment can override it. Otherwise the
 * default depends on where this is running: Vercel sets VERCEL=1 during the
 * build, and there the API is the deployed Render service; anywhere else it is
 * a local uvicorn on :8000.
 *
 * The production URL is committed on purpose. It is not a secret — it is a
 * public endpoint anyone can curl — and hard-coding the default means a fresh
 * clone deploys and works without a dashboard step that is easy to forget and
 * silently breaks every request when it is.
 */
const RENDER_API = "https://counsel-api-ileh.onrender.com";

const API =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.VERCEL ? RENDER_API : "http://localhost:8000");

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};

export default nextConfig;
