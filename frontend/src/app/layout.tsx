import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import type { Metadata } from "next";
import { cookies } from "next/headers";

import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ACTOR_COOKIE, sanitizePm } from "@/lib/actor";

import "./globals.css";

export const metadata: Metadata = {
  title: "Parallax",
  description: "Requirements cockpit for the next BMW 5 Series",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const pm = sanitizePm((await cookies()).get(ACTOR_COOKIE)?.value);
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <TooltipProvider>
          <SidebarProvider>
            <AppSidebar initialPm={pm} />
            <SidebarInset>
              <main className="flex min-w-0 flex-1 flex-col px-6 pb-10 md:px-10">{children}</main>
            </SidebarInset>
          </SidebarProvider>
        </TooltipProvider>
        <Toaster position="bottom-right" />
      </body>
    </html>
  );
}
