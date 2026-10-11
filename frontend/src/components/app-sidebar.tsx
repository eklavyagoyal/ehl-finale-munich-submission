"use client";

import { Activity, Car, Database, LayoutDashboard, Workflow } from "lucide-react";
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
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import { useRequirements, useVehicles } from "@/lib/api/hooks";
import { humanize } from "@/lib/format";
import { STAGES } from "@/lib/stages";
import { V } from "@/lib/routes";

export function AppSidebar({ initialPm, signedIn }: { initialPm: string; signedIn: boolean }) {
  const pathname = usePathname();
  const { data: requirements } = useRequirements();
  const { data: vehicles } = useVehicles();
  const [pm, setPm] = useState(initialPm);

  // Data: independent of vehicles. Vehicles: the active one opens its stages; the others are coming.
  const data = [
    { href: "/", label: "Overview", icon: LayoutDashboard, active: pathname === "/" },
    { href: "/sources", label: "Sources", icon: Database, active: pathname.startsWith("/sources") },
    { href: "/processing", label: "Processing", icon: Workflow, active: pathname.startsWith("/processing") },
  ];
  const cars = (vehicles?.items ?? []).filter((v) => v.entity_id !== "brand");

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
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
          <SidebarGroupLabel>Data</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {data.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={item.active} tooltip={item.label}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.label}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Vehicles</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {cars.map((v) =>
                v.status === "active" ? (
                  <SidebarMenuItem key={v.entity_id}>
                    <SidebarMenuButton asChild isActive={pathname === V} tooltip={`${v.code} · ${v.name}`}>
                      <Link href={V}>
                        <Car />
                        <span className="truncate">
                          {v.code} <span className="text-muted-foreground">· {v.name.replace(/^BMW /, "")}</span>
                        </span>
                      </Link>
                    </SidebarMenuButton>
                    <SidebarMenuSub>
                      {STAGES.map((stage) => (
                        <SidebarMenuSubItem key={stage.key}>
                          <SidebarMenuSubButton asChild isActive={pathname.startsWith(stage.href)}>
                            <Link href={stage.href}>
                              <span>{stage.title}</span>
                              {stage.key === "decision" && requirements && (
                                <span className="ml-auto text-xs text-muted-foreground tabular-nums">{requirements.length}</span>
                              )}
                            </Link>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  </SidebarMenuItem>
                ) : (
                  <SidebarMenuItem key={v.entity_id}>
                    <SidebarMenuButton disabled tooltip={`${v.name}: coming`} className="opacity-50">
                      <Car />
                      <span className="truncate">{v.code}</span>
                      <span className="ml-auto text-[11px]">coming</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ),
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={pathname.startsWith("/activity")} tooltip="Activity">
                  <Link href="/activity">
                    <Activity />
                    <span>Activity</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
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
