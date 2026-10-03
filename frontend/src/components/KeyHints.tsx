/**
 * The row of keyboard hints above the dock, shown while the controls are open.
 *
 * Owner: A. Spec: docs/design/ui.md §4.3, §5.3.3 ("Keyboard").
 */
export function KeyHints() {
  return (
    <div className="keys" aria-hidden>
      <span><kbd>Space</kbd>record</span>
      <span><kbd>L</kbd>listen</span>
      <span><kbd>R</kbd>retry</span>
      <span><kbd>Enter</kbd>next</span>
      <span><kbd>↑</kbd><kbd>↓</kbd>change line</span>
      <span><kbd>P</kbd>pinyin</span>
      <span><kbd>F</kbd>full screen</span>
      <span><kbd>E</kbd>or double-click: hide controls</span>
    </div>
  );
}
