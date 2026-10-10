import { redirect } from "next/navigation";

// The data view became Sources.
export default function DataRedirect() {
  redirect("/sources");
}
