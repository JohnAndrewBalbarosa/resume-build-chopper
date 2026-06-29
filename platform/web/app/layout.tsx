import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PyTorch FEU Tech Campus Platform",
  description: "Community intelligence hub prototype for PyTorch FEU Tech Campus."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
