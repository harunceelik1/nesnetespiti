import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Open Vocabulary Detection",
  description: "Natural language object detection workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
