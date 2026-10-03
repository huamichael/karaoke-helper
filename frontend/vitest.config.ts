/**
 * Unit tests for the pure logic modules (src/logic). They run in Node; no DOM.
 *
 * Owner: A.
 */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
