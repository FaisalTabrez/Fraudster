// The Fraudster mark from the brand kit (brand/logo/fraudster-mark.svg): a speech bubble with a
// pause sign in a brand-green rounded square. Decorative; the wordmark text beside it names the app.
export function LogoMark({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" aria-hidden="true" focusable="false">
      <rect width="56" height="56" rx="16" fill="#1F4D43" />
      <path
        d="M18 13h20a6 6 0 0 1 6 6v13a6 6 0 0 1-6 6H24l-8 6v-6.4A6 6 0 0 1 12 32V19a6 6 0 0 1 6-6z"
        fill="#F4F2EC"
      />
      <rect x="22.5" y="19.5" width="4" height="12" rx="1.5" fill="#1F4D43" />
      <rect x="29.5" y="19.5" width="4" height="12" rx="1.5" fill="#1F4D43" />
    </svg>
  );
}
