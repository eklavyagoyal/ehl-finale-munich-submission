import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { Fragment } from "react";

export interface Crumb {
  label: string;
  href?: string;
}

// The only header: a breadcrumb row at the top edge, page actions on the right.
export function PageHeader({ crumbs, children }: { crumbs: Crumb[]; children?: React.ReactNode }) {
  return (
    <div className="flex min-h-12 flex-wrap items-center gap-3 py-2">
      <nav aria-label="Breadcrumb" className="flex min-w-0 flex-wrap items-center gap-1.5 text-[13px] text-muted-foreground">
        {crumbs.map((crumb, index) => {
          const last = index === crumbs.length - 1;
          return (
            <Fragment key={`${crumb.label}-${index}`}>
              {index > 0 && <ChevronRight className="size-3.5 text-muted-foreground/60" aria-hidden />}
              {crumb.href && !last ? (
                <Link href={crumb.href} className="hover:text-foreground">
                  {crumb.label}
                </Link>
              ) : (
                <span className={last ? "font-medium text-foreground" : undefined}>{crumb.label}</span>
              )}
            </Fragment>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-2">{children}</div>
    </div>
  );
}
