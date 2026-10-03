/**
 * Entry point: self-hosted fonts, the stylesheet, and the app.
 *
 * Owner: A. Spec: docs/design/ui.md §3.2 ("Self-host both fonts").
 */
import "@fontsource/instrument-sans/400.css";
import "@fontsource/instrument-sans/500.css";
import "@fontsource/instrument-sans/600.css";
import "@fontsource/instrument-sans/700.css";
import "@fontsource/noto-serif-sc/200.css";
import "@fontsource/noto-serif-sc/700.css";
import "@fontsource/noto-serif-sc/900.css";
import "./styles/index.css";

import { MotionConfig } from "motion/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

// reducedMotion="user": with prefers-reduced-motion, Motion's moves (the word to the centre,
// the dock's width) happen without movement, like the CSS ones (ui.md §3.3).
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <App />
    </MotionConfig>
  </StrictMode>,
);
