/**
 * The song screen's header: the wordmark, one line on what the app does, the four
 * steps, and the sound switch for the preview and the vinyl ambience.
 *
 * Owner: A. Spec: docs/design/ui.md §4.1, §5.1.
 */
import { SoundOffIcon, SoundOnIcon } from "../icons";
import { Vinyl } from "../Vinyl";

export function HomeHeader({ sound, onSound }: { sound: boolean; onSound(): void }) {
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
      <button className="sound" aria-pressed={sound} onClick={onSound}>
        {sound ? <SoundOnIcon /> : <SoundOffIcon />}{sound ? "Sound on" : "Sound off"}
      </button>
    </header>
  );
}
