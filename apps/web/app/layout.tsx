import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReelPilot AI — Turn comments into your next Reel",
  description:
    "Find repeated audience questions and create evidence-backed Reel content packs.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
