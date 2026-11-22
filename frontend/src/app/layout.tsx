import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Açık Sözlük Nesne Tespiti",
  description: "Metinle veya örnekle, eğitimde görülmemiş nesneleri bulan tespit arayüzü",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
