import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { display, body, mono } from "@/lib/fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "Earnings AI | Advanced Multi-Agent Analytics",
  description: "Next-generation earnings predictions through autonomous agent debate.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${display.variable} ${body.variable} ${mono.variable}`}
        suppressHydrationWarning
      >
        <body className="antialiased" suppressHydrationWarning>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
