/**
 * The vinyl record: the Listen button in the dock. It spins while the line plays.
 *
 * Owner: A. Spec: docs/design/ui.md §5.3 (dock column), §6.
 */
import type { ReactNode } from "react";

export function Vinyl({ spinning = false, children }: { spinning?: boolean; children?: ReactNode }) {
  return <span className={`vinyl${spinning ? " spinning" : ""}`}>{children}</span>;
}
