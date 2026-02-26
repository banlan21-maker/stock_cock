import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import AdBanner from "@/components/common/AdBanner";
import { AdProvider } from "@/context/AdProvider";
import { RewardProvider } from "@/context/RewardProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "주식콕 Stock Cock",
  description: "복잡한 주식 정보, 콕 집어 알려드려요",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-navy text-white min-h-screen`}
      >
        <AdProvider>
          <RewardProvider>
            <Header />
            <main className="pb-[var(--ad-banner-height)]">
              {children}
            </main>
            <AdBanner />
          </RewardProvider>
        </AdProvider>
      </body>
    </html>
  );
}
