import { cookies } from "next/headers";

import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { ACTOR_COOKIE, sanitizePm } from "@/lib/actor";
import { authEnabled } from "@/lib/session";

export default async function CockpitLayout({ children }: { children: React.ReactNode }) {
  const pm = sanitizePm((await cookies()).get(ACTOR_COOKIE)?.value);
  return (
    <SidebarProvider>
      <AppSidebar initialPm={pm} canSignOut={authEnabled()} />
      <SidebarInset>
        <main className="flex min-w-0 flex-1 flex-col px-6 pb-10 md:px-10">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
