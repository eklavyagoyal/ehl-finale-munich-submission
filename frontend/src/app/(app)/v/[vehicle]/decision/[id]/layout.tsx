import { Suspense } from "react";

import { LoadingRows } from "@/components/states";
import { RequirementProvider } from "@/components/requirement/context";
import { RequirementShell } from "@/components/requirement/shell";

export default async function RequirementLayout({ children, params }: LayoutProps<"/v/[vehicle]/decision/[id]">) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingRows rows={3} />}>
      <RequirementProvider id={decodeURIComponent(id)}>
        <RequirementShell>{children}</RequirementShell>
      </RequirementProvider>
    </Suspense>
  );
}
