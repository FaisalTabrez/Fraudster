import type { ReactNode } from "react";

// The 24x24 stroke icons from the Fraudster brand kit (brand/icons). They are drawn in a single
// ink colour and inherit `currentColor`, so a parent sets the tint. Decorative: callers put the
// meaning in adjacent text, never in the icon alone.
export type IconName =
  | "verdict-scam"
  | "verdict-promotional"
  | "verdict-no-warning"
  | "verdict-unable"
  | "demo-data"
  | "coverage-partial"
  | "coverage-unavailable"
  | "check-ran"
  | "check-not-applicable"
  | "check-not-run"
  | "not-opened"
  | "privacy-lock"
  | "input-message"
  | "input-link"
  | "input-conversation"
  | "remove";

const icons: Record<IconName, { width?: number; body: ReactNode }> = {
  "verdict-scam": {
    body: (
      <>
        <path d="M8 2h8l6 6v8l-6 6H8l-6-6V8z" />
        <path d="M12 7v6M12 16.5v.5" />
      </>
    ),
  },
  "verdict-promotional": {
    body: (
      <>
        <path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8z" />
        <circle cx="7" cy="7" r="1.5" />
      </>
    ),
  },
  "verdict-no-warning": { body: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /> },
  "verdict-unable": {
    body: (
      <>
        <circle cx="12" cy="12" r="10" strokeDasharray="3 3" />
        <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17v.5" />
      </>
    ),
  },
  "demo-data": { body: <path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2h12.4a1.5 1.5 0 0 0 1.3-2L14 9V3" /> },
  "coverage-partial": {
    body: (
      <>
        <path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
        <path d="M12 9v4M12 17v.5" />
      </>
    ),
  },
  "coverage-unavailable": {
    body: (
      <>
        <circle cx="12" cy="12" r="10" />
        <path d="M4.9 4.9l14.2 14.2" />
      </>
    ),
  },
  "check-ran": {
    width: 2.2,
    body: (
      <>
        <circle cx="12" cy="12" r="10" />
        <path d="M8 12.5l2.5 2.5L16 9.5" />
      </>
    ),
  },
  "check-not-applicable": { width: 2.2, body: <path d="M6 12h12" /> },
  "check-not-run": { width: 2.2, body: <circle cx="12" cy="12" r="9" strokeDasharray="2.5 3" /> },
  "not-opened": { body: <path d="M2 12s3.5-7 10-7c2 0 3.7.6 5.1 1.5M22 12s-3.5 7-10 7c-2 0-3.7-.6-5.1-1.5M3 3l18 18" /> },
  "privacy-lock": {
    body: (
      <>
        <rect x="4" y="10" width="16" height="11" rx="2" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      </>
    ),
  },
  "input-message": { body: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /> },
  "input-link": {
    body: (
      <>
        <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
        <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
      </>
    ),
  },
  "input-conversation": {
    body: (
      <>
        <path d="M17 9h2a2 2 0 0 1 2 2v9l-3-3h-6a2 2 0 0 1-2-2v-1" />
        <path d="M3 5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H7l-4 4z" />
      </>
    ),
  },
  remove: { body: <path d="M6 6l12 12M18 6L6 18" /> },
};

export function Icon({ name, size = 20, className = "" }: { name: IconName; size?: number; className?: string }) {
  const { width = 2, body } = icons[name];
  return (
    <svg
      className={`fr-ico ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {body}
    </svg>
  );
}
