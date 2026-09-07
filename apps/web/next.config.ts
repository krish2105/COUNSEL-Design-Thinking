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
  /* Compression off, because it silently un-streams every SSE endpoint.
   *
   * This server proxies /api/* to the FastAPI service, and several of those
   * routes are text/event-stream: the debate turns, scoring, the memo, and the
   * Define and Ideate stages. Next compresses a proxied response whenever the
   * client asks for it, and a browser always asks — so it answered
   * text/event-stream with Content-Encoding: gzip, and gzip buffers.
   *
   * Measured in a real browser: response headers at 0.01s, then the whole body,
   * every frame at once, at 33.60s. The same request under curl streamed frame
   * by frame, because curl does not request gzip by default — which is why
   * every hand test of every stream in this project looked correct while no
   * stream had ever actually streamed to a browser.
   *
   * The API already sends `Content-Encoding: identity` (services/api/core/
   * stream.py). Next strips it and re-compresses regardless, so this is the
   * only lever that works.
   *
   * The cost is small and worth naming: responses this server emits are no
   * longer gzipped. The pages are a few kB of HTML over a static-asset pipeline
   * Vercel already compresses at its edge, and the API responses being proxied
   * are JSON measured in kilobytes. Streaming that works is worth more than
   * bytes saved on a payload this size.
   */
  compress: false,

  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};

export default nextConfig;
