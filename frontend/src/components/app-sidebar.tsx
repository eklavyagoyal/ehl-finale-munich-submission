"use client";

import { Activity, ChevronsUpDown, History, Inbox, ListChecks } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { PM_OPTIONS, writePmCookie } from "@/lib/actor";
import { refreshAll, useRequirements, useTasks } from "@/lib/api/hooks";
import { humanize } from "@/lib/format";

export function AppSidebar({ initialPm }: { initialPm: string }) {
  const pathname = usePathname();
  const { data: tasks } = useTasks();
  const { data: requirements } = useRequirements();
  const [pm, setPm] = useState(initialPm);

  const items = [
    { href: "/tasks", label: "My tasks", icon: Inbox, count: tasks?.length },
    { href: "/requirements", label: "Requirements", icon: ListChecks, count: requirements?.length },
    { href: "/activity", label: "Activity", icon: Activity },
    { href: "/history", label: "History", icon: History },
  ];

  function switchPm(name: string) {
    writePmCookie(name);
    setPm(name);
    void refreshAll();
  }

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
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" aria-label="Switch product manager">
                  <span className="flex size-8 items-center justify-center rounded-full bg-muted text-xs font-medium uppercase">
                    {pm.slice(0, 2)}
                  </span>
                  <span className="flex flex-col leading-tight">
                    <span className="font-medium">{humanize(pm)}</span>
                    <span className="text-xs text-muted-foreground">Product manager · 5 Series</span>
                  </span>
                  <ChevronsUpDown className="ml-auto" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-56">
                <DropdownMenuLabel className="text-xs text-muted-foreground">Act as</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {PM_OPTIONS.map((name) => (
                  <DropdownMenuItem key={name} onSelect={() => switchPm(name)}>
                    pm:{name}
                    {name === pm && <span className="ml-auto text-xs text-muted-foreground">active</span>}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
