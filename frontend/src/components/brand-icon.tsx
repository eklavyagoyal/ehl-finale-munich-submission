import { Globe, MessagesSquare, Newspaper } from "lucide-react";
import { createElement } from "react";

// Channel marks as simple inline SVGs (lucide has no brand logos); recognisable by shape, drawn monochrome.
export function ChannelMark({ channel, className = "size-4" }: { channel: string; className?: string }) {
  const svg = (children: React.ReactNode) => (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinejoin="round" aria-hidden>
      {children}
    </svg>
  );
  if (channel === "youtube")
    return svg(
      <>
        <rect x="2.5" y="5.5" width="19" height="13" rx="4" />
        <path d="M10 9.2v5.6l4.8-2.8z" fill="currentColor" stroke="none" />
      </>,
    );
  if (channel === "google_play") return svg(<path d="M5 3.5v17l9.5-8.5z M5 3.5l12.5 7.2-3 1.3 M5 20.5l12.5-7.2-3-1.3" />);
  if (channel === "app_store")
    return svg(
      <>
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <path d="M9.5 16.5l4.2-8.5 M14.5 16.5l-4.2-8.5 M7.5 13.5h9" strokeLinecap="round" />
      </>,
    );
  if (channel.startsWith("bmw"))
    return svg(
      <>
        <circle cx="12" cy="12" r="9.5" />
        <circle cx="12" cy="12" r="6" />
        <path d="M12 6v12 M6 12h12" />
        <path d="M12 6a6 6 0 0 1 6 6h-6z M12 18a6 6 0 0 1-6-6h6z" fill="currentColor" stroke="none" />
      </>,
    );
  const fallback = channel === "forum" ? MessagesSquare : channel === "editorial_review" ? Newspaper : Globe;
  return createElement(fallback, { className, strokeWidth: 1.6, "aria-hidden": true });
}
