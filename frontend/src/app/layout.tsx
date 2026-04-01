import type { Metadata } from "next";
import { Syne, Syne_Mono, Cormorant_Garamond } from "next/font/google";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/layout/AppShell";
import "./globals.css";
import "./sift-v2.css";

const syne = Syne({ variable: "--font-sans", subsets: ["latin"] });
const syneMono = Syne_Mono({
  variable: "--font-sift-mono",
  subsets: ["latin"],
  weight: "400",
});
const cormorant = Cormorant_Garamond({
  variable: "--font-sift-serif",
  subsets: ["latin"],
  weight: ["300", "400", "600"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Sift — AI Deep Research Engine",
  description:
    "Research any topic with AI-powered multi-source search and streaming cited answers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${syne.variable} ${syneMono.variable} ${cormorant.variable} antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider delay={300}>
            <AppShell>{children}</AppShell>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
