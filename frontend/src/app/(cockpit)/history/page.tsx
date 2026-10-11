import { redirect } from "next/navigation";

// History left the sidebar; decisions are part of Activity.
export default function HistoryRedirect() {
  redirect("/activity");
}
