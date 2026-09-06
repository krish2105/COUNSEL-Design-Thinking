import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Newsreader, Noto_Naskh_Arabic, Noto_Serif_Devanagari } from "next/font/google";
import { Masthead } from "@/components/Masthead";
import { Providers } from "@/components/Providers";
import "../styles/globals.css";

/* Fraunces carries the chamber's voice — its WONK axis is what stops the display
 * face reading as a stock serif. Newsreader sets the record because it is drawn
 * for continuous reading at optical sizes. Plex Mono carries hashes, offsets and
 * scores. Noto covers the other two scripts so one record reads as one document. */
const display = Fraunces({
  subsets: ["latin"],
  variable: "--f-display",
  axes: ["SOFT", "WONK", "opsz"],
  display: "swap",
});
const body = Newsreader({ subsets: ["latin"], variable: "--f-body", display: "swap" });
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--f-mono",
  display: "swap",
});
const arabic = Noto_Naskh_Arabic({ subsets: ["arabic"], variable: "--f-arabic", display: "swap" });
const devanagari = Noto_Serif_Devanagari({
  subsets: ["devanagari"],
  variable: "--f-devanagari",
  display: "swap",
});

export const metadata: Metadata = {
  title: "COUNSEL",
  description: "Five mandates argue a real decision. The record outlives the argument.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      dir="ltr"
      suppressHydrationWarning
      className={`${display.variable} ${body.variable} ${mono.variable} ${arabic.variable} ${devanagari.variable}`}
    >
      <body>
        <Providers>
          <Masthead />
          <main id="record">{children}</main>
          <footer className="colophon">
            <span>Zero paid inference. Free, licensed sources only.</span>
            <span>No agent can publish or execute anything.</span>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
