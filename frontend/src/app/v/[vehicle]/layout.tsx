import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { ACTOR_COOKIE, sanitizePm } from "@/lib/actor";
import { VEHICLE } from "@/lib/routes";
import { authEnabled, readSession, SESSION_COOKIE } from "@/lib/session";

// Everything inside a vehicle: stage sidebar plus the page. Only the active vehicle exists for now.
export default async function VehicleLayout({ children, params }: LayoutProps<"/v/[vehicle]">) {
  const { vehicle } = await params;
  if (vehicle.toLowerCase() !== VEHICLE) notFound();
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
