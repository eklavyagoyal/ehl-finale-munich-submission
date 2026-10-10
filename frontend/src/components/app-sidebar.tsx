"use client";

import { Activity, Database, History, Inbox, ListChecks } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { SettingsDialog } from "@/components/settings-dialog";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useRequirements, useTasks } from "@/lib/api/hooks";
import { humanize } from "@/lib/format";

export function AppSidebar({ initialPm, signedIn }: { initialPm: string; signedIn: boolean }) {
  const pathname = usePathname();
  const { data: tasks } = useTasks();
  const { data: requirements } = useRequirements();
  const [pm, setPm] = useState(initialPm);

  const items = [
    { href: "/tasks", label: "My tasks", icon: Inbox, count: tasks?.length },
    { href: "/requirements", label: "Requirements", icon: ListChecks, count: requirements?.length },
    { href: "/data", label: "Data", icon: Database },
    { href: "/activity", label: "Activity", icon: Activity },
    { href: "/history", label: "History", icon: History },
  ];

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/tasks">
                <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground">
                  P
                </span>
                <span className="flex flex-col leading-tight">
                  <span className="font-semibold">Parallax</span>
                  <span className="text-xs text-muted-foreground">Requirements cockpit</span>
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname.startsWith(item.href)} tooltip={item.label}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.label}</span>
                    </Link>
                  </SidebarMenuButton>
                  {item.count !== undefined && <SidebarMenuBadge>{item.count}</SidebarMenuBadge>}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <div className="flex items-center gap-2 p-1 group-data-[collapsible=icon]:justify-center">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium uppercase">
            {pm.slice(0, 2)}
          </span>
          <span className="flex min-w-0 flex-1 flex-col text-sm leading-tight group-data-[collapsible=icon]:hidden">
            <span className="truncate font-medium">{humanize(pm)}</span>
            <span className="truncate text-xs text-muted-foreground">Product manager · 5 Series</span>
          </span>
          <span className="group-data-[collapsible=icon]:hidden">
            <SettingsDialog pm={pm} onPmChange={setPm} signedIn={signedIn} />
          </span>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
