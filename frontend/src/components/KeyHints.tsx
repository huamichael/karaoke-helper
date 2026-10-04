/**
 * The row of keyboard hints above the dock, shown while the controls are open.
 * The line screen's by default; Karaoke passes its own.
 *
 * Owner: A. Spec: docs/design/ui.md §4.3, §5.3.3 ("Keyboard"), §5.6.
 */
export type KeyHint = [keys: string[], label: string];

export const LINE_KEYS: KeyHint[] = [
  [["Space"], "record"],
  [["L"], "listen"],
  [["R"], "retry"],
  [["Enter"], "next"],
  [["↑", "↓"], "change line"],
  [["P"], "pinyin"],
  [["F"], "full screen"],
  [["E"], "or double-click: hide controls"],
];

export const KARAOKE_KEYS: KeyHint[] = [
  [["Space"], "play or pause"],
  [["↑", "↓"], "change line"],
  [["→"], "skip to the singing"],
  [["R"], "start again"],
  [["P"], "pinyin"],
  [["F"], "full screen"],
  [["E"], "or double-click: hide controls"],
];

export function KeyHints({ keys = LINE_KEYS }: { keys?: KeyHint[] }) {
  return (
    <div className="keys" aria-hidden>
      {keys.map(([ks, label]) => (
        <span key={label}>{ks.map((k) => <kbd key={k}>{k}</kbd>)}{label}</span>
      ))}
    </div>
  );
}
