/**
 * The song screen's header: the wordmark, one line on what the app does, and the
 * four steps. (Sound on and off is the cap on the tonearm's pivot: SoundCap.)
 *
 * Owner: A. Spec: docs/design/ui.md §4.1, §5.1.
 */
import { Vinyl } from "../Vinyl";

export function HomeHeader() {
  return (
    <header className="h-top">
      <div>
        <div className="wordmark"><Vinyl />Karaoke Helper</div>
        <p className="h-tag">Learn Mandarin by singing the songs you love.</p>
        <ol className="steps">
          <li><b>1</b>Listen to a line</li>
          <li><b>2</b>Sing it back</li>
          <li><b>3</b>See every word</li>
          <li><b>4</b>Practise the ones you missed</li>
        </ol>
      </div>
    </header>
  );
}
