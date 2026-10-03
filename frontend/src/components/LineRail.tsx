/**
 * The line rail: one short tick per line on the right edge. Click a tick to go to that line.
 *
 * Owner: A. Spec: docs/design/ui.md §4.3 ("Line rail"), §5.3.2.
 */
export function LineRail({ count, active, lit, onPick }: { count: number; active: number; lit: boolean; onPick(i: number): void }) {
  return (
    <nav className={`rail${lit ? " lit" : ""}`} aria-label="Lines">
      {Array.from({ length: count }, (_, k) => (
        <button key={k} className={k === active ? "on" : undefined} aria-label={`Line ${k + 1}`} aria-current={k === active || undefined} onClick={() => onPick(k)}>
          <i />
        </button>
      ))}
    </nav>
  );
}
