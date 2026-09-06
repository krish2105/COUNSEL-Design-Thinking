import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "COUNSEL",
  description: "Five mandates argue a real decision. The record outlives the argument.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
