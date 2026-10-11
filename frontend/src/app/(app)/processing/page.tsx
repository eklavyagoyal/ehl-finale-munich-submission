"use client";

import { PageHeader } from "@/components/page-header";
import { ProcessingFlowChart } from "@/components/processing-flow";
import { ErrorState, LoadingRows } from "@/components/states";
import { useOverviewFlow } from "@/lib/api/hooks";
import { fmtCount } from "@/lib/format";

// Data › Processing: everything that came in, before any vehicle. Streams flow into "not relevant"
// (triage) or to the vehicle they are about.
export default function GlobalProcessingPage() {
  const { data, error, isLoading } = useOverviewFlow();
  return (
    <>
      <PageHeader crumbs={[{ label: "Processing" }]} vehicle={false} />
      <p className="mt-1 text-[13px] text-muted-foreground">Where does each record belong?</p>
      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && (
        <div className="mt-8 flex max-w-6xl flex-col gap-3">
          <ProcessingFlowChart flow={data} />
          {data.unchecked_online ? (
            <p className="text-[11px] text-muted-foreground">{fmtCount(data.unchecked_online)} online reviews not triaged yet; they flow on as if relevant.</p>
          ) : null}
          {data.note && <p className="max-w-3xl text-[11px] text-muted-foreground">{data.note}</p>}
        </div>
      )}
    </>
  );
}
