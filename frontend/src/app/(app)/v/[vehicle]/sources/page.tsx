import { SourcesPage } from "@/components/sources-page";

// Sources of one vehicle: only its own records; everything else sits under "Not about the G60".
export default function VehicleSourcesPage() {
  return <SourcesPage vehicle />;
}
