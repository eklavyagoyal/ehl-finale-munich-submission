import { notFound } from "next/navigation";

import { VEHICLE } from "@/lib/routes";

// Everything inside a vehicle is filtered to it. Only the active vehicle exists for now.
export default async function VehicleLayout({ children, params }: LayoutProps<"/v/[vehicle]">) {
  const { vehicle } = await params;
  if (vehicle.toLowerCase() !== VEHICLE) notFound();
  return children;
}
