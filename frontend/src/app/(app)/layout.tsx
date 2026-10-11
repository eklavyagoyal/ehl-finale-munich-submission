import { cookies } from "next/headers";

import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { ACTOR_COOKIE, sanitizePm } from "@/lib/actor";
import { authEnabled, readSession, SESSION_COOKIE } from "@/lib/session";

// The sidebar is always there: the data section (independent of vehicles) and the vehicles with their stages.
export default async function AppLayout({ children }: LayoutProps<"/">) {
  const jar = await cookies();
  const signedIn = authEnabled() ? readSession(jar.get(SESSION_COOKIE)?.value)?.pm : undefined;
  const pm = signedIn ?? sanitizePm(jar.get(ACTOR_COOKIE)?.value);
  return (
    <SidebarProvider>
      <AppSidebar initialPm={pm} signedIn={!!signedIn} />
      <SidebarInset>
        <main className="flex min-w-0 flex-1 flex-col px-6 pb-10 md:px-10">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
