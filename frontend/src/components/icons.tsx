/**
 * The app's few icons, as inline SVG (from the prototype).
 *
 * Owner: A.
 */
const stroke = { fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" } as const;

export const MicIcon = () => (
  <svg viewBox="0 0 24 24" {...stroke}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
);
export const PlayIcon = () => <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z" /></svg>;
export const StopIcon = () => <svg viewBox="0 0 24 24" fill="currentColor"><rect x="6.5" y="6.5" width="11" height="11" rx="2" /></svg>;
export const RetryIcon = () => <svg viewBox="0 0 24 24" {...stroke}><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4h4" /></svg>;
export const CloseIcon = () => <svg viewBox="0 0 24 24" {...stroke} strokeWidth={2.2}><path d="M6 6l12 12M18 6L6 18" /></svg>;
export const CheckIcon = () => <svg viewBox="0 0 24 24" {...stroke} strokeWidth={3.2}><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>;
export const BackIcon = () => <svg viewBox="0 0 24 24" {...stroke}><path d="M15 6l-6 6 6 6" /></svg>;
export const SoundOnIcon = () => (
  <svg viewBox="0 0 24 24" {...stroke}><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" /></svg>
);
export const SoundOffIcon = () => <svg viewBox="0 0 24 24" {...stroke}><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M17 9l5 6M22 9l-5 6" /></svg>;
