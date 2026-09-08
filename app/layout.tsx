import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ragled",
  description: "RAG interface for geographic and temporal data exploration"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="it" className="dark">
      <body>{children}</body>
    </html>
  );
}
