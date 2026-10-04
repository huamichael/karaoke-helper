/**
 * Karaoke screen: sing along to the song without its singer. Nothing is recorded
 * or graded.
 *
 * The instrumental (song.instrumental_url, made by the pipeline with Demucs) plays
 * from the start, and the lyric list follows it line by line: the line being sung
 * sits in the centre and fills character by character at the pace the original
 * singer sang it (logic/timing.ts), and the next line takes over just before it is
 * due (logic/subtitle.ts). During an intro or a break the line waiting shows how
 * long until it, then a count-in, and the dock offers to skip ahead
 * (logic/karaoke.ts). Without an instrumental the original track plays; without
 * any track the lyric runs on a silent clock.
 *
 * Owner: A. Spec: docs/design/ui.md §5.6, docs/tasks/frontend.md ("Karaoke screen").
 */
import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import type { Song } from "../api/client";
import { karaokeTrack, type KaraokeTrack } from "../audio/player";
import { Dock } from "../components/Dock";
import { KARAOKE_KEYS, KeyHints } from "../components/KeyHints";
import { LineRail } from "../components/LineRail";
import { LyricLine } from "../components/LyricLine";
import { LyricList, type LyricListHandle } from "../components/LyricList";
import { OptionsPill } from "../components/OptionsPill";
import { toast } from "../components/Toast";
import { TopBar } from "../components/TopBar";
import { useChrome } from "../hooks/useChrome";
import { useLatest } from "../hooks/useLatest";
import { karaokeActionsFor, type DockActionId } from "../logic/actions";
import { startOf, waiting } from "../logic/karaoke";
import { createWheelStepper, type Step } from "../logic/lineSwipe";
import { subtitleIndex } from "../logic/subtitle";
import { fillFractions, fillSpan } from "../logic/timing";

/** title: the song's title as shown (the theme's Hanzi when it has one). */
type Props = { song: Song; title: string; onExit(): void };

/** The song starts once the lyrics have risen in. */
const START_DELAY_MS = 900;
/** Without any track, the silent clock stops this long after the last line. */
const SILENT_TAIL_MS = 2_000;

let hinted = false;
const NONE: number[] = [];
const noop = () => {};
/** A fill, to tell whether it changed since the last frame. */
const keyOf = (f: number[]) => f.map((x) => x.toFixed(3)).join(",");

export default function KaraokeScreen({ song, title, onExit }: Props) {
  const lines = song.lines;
  const spans = useMemo(() => lines.map(fillSpan), [lines]);
  const [active, setActive] = useState(0);
  const [fill, setFill] = useState<number[]>(() => lines[0]?.syllables.map(() => 0) ?? []);
  const [cue, setCue] = useState<string | null>(null);
  const [skipTo, setSkipTo] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [open, setOpen] = useState(false);
  const [showPinyin, setShowPinyin] = useState(true);
  const [showTranslation, setShowTranslation] = useState(true);
  const [entering, setEntering] = useState(true);
  const [railLit, setRailLit] = useState(false);

  const root = useRef<HTMLElement>(null);
  const list = useRef<LyricListHandle>(null);
  const track = useRef<KaraokeTrack | null>(null);
  const shown = useRef(0);
  const fillKey = useRef("");
  const ended = useRef(false);
  const railTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const live = useLatest({ playing, open, skipTo });
  const chrome = useChrome(open);

  // ---- the song ----
  useEffect(() => {
    const last = lines[lines.length - 1];
    const tr = karaokeTrack([song.instrumental_url, song.audio_url], (last?.end_ms ?? 0) + SILENT_TAIL_MS, {
      onPlaying: setPlaying,
      onEnded: () => {
        ended.current = true;
        toast("That's the whole song. Play it again, or pick another.", 3600);
      },
      onFallback: (to) =>
        toast(to === "next"
          ? "This song's instrumental isn't on this computer, so the original track plays, singer and all."
          : "This song's track isn't on this computer. The lyrics run without music.", 5200),
    });
    track.current = tr;
    if (!song.instrumental_url) toast("This song has no instrumental yet, so the original track plays, singer and all.", 5200);
    const go = setTimeout(() => tr.play(), START_DELAY_MS);
    const t = setTimeout(() => setEntering(false), 1700);
    const h = hinted ? 0 : setTimeout(() => toast("Sing along. Space plays and pauses, ↑ ↓ change line. Double-click for every control.", 4600), 1400);
    hinted = true;
    return () => {
      clearTimeout(go);
      clearTimeout(t);
      if (h) clearTimeout(h);
      tr.dispose();
      track.current = null;
    };
  }, [song, lines]);

  /** Show line k, filled as it is at track time t: the list moves to it on the line spring. */
  const show = useCallback((k: number, t: number) => {
    const f = fillFractions(lines[k], t);
    fillKey.current = keyOf(f);
    shown.current = k;
    const mutate = () => { setActive(k); setFill(f); };
    if (list.current) list.current.flip(mutate);
    else mutate();
  }, [lines]);

  // Every frame: which line shows, how far it has filled, and the cue during a break. Each renders only
  // when it changes, so the long instrumental stretches cost nothing.
  useEffect(() => {
    let raf = requestAnimationFrame(function frame() {
      const tr = track.current;
      if (tr && lines.length) {
        const t = tr.timeMs();
        const k = subtitleIndex(spans, t);
        if (k !== shown.current) show(k, t);
        else {
          const f = fillFractions(lines[k], t), key = keyOf(f);
          if (key !== fillKey.current) { fillKey.current = key; setFill(f); }
        }
        const w = waiting(spans, k, t);
        setCue(w.cue);
        setSkipTo(w.skipTo);
      }
      raf = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(raf);
  }, [lines, spans, show]);

  // ---- controls ----
  const togglePlay = () => {
    const tr = track.current;
    if (!tr) return;
    if (live.current.playing) return tr.pause();
    if (ended.current) { ended.current = false; tr.seek(0); }
    tr.play();
  };

  const restart = () => {
    const tr = track.current;
    if (!tr) return;
    ended.current = false;
    tr.seek(0);
    show(0, 0);
    tr.play();
  };

  const skip = () => {
    const to = live.current.skipTo;
    if (to != null) track.current?.seek(to);
  };

  const jump = (j: number, dir: Step = j > shown.current ? 1 : -1) => {
    const tr = track.current;
    if (!tr || j === shown.current) return;
    if (j < 0 || j >= lines.length) return list.current?.bounce(dir);
    const at = startOf(spans, j);
    ended.current = false;
    tr.seek(at);
    show(j, at);
    setRailLit(true);
    clearTimeout(railTimer.current);
    railTimer.current = setTimeout(() => setRailLit(false), 900);
  };

  const exit = () => {
    track.current?.dispose();
    onExit();
  };

  const onAction = (id: DockActionId) => {
    if (id === "kplay") togglePlay();
    else if (id === "krestart") restart();
    else if (id === "kskip") skip();
  };

  const togglePinyin = () => list.current?.flip(() => setShowPinyin((v) => !v));
  const toggleTranslation = () => list.current?.flip(() => setShowTranslation((v) => !v));
  // E and a double-click switch the whole top layer, as on the line screen.
  const toggleControls = () => {
    const next = !live.current.open;
    setOpen(next);
    if (next) chrome.show();
    else chrome.hide();
  };
  const onDoubleClick = (e: MouseEvent) => {
    if ((e.target as HTMLElement).closest("button, .dock, .opts")) return;
    toggleControls();
  };

  const onKey = (e: KeyboardEvent) => {
    const t = e.target as HTMLElement;
    if (t.matches?.("input, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if (k === "Escape") { if (live.current.open) setOpen(false); return; }
    if (t.closest?.("button, [role=button]") && (k === " " || k === "Enter")) return;
    if (k === " ") { e.preventDefault(); togglePlay(); }
    else if (k === "ArrowDown") { e.preventDefault(); jump(shown.current + 1, 1); }
    else if (k === "ArrowUp") { e.preventDefault(); jump(shown.current - 1, -1); }
    else if (k === "ArrowRight") { e.preventDefault(); skip(); }
    else if (k === "r") restart();
    else if (k === "p") togglePinyin();
    else if (k === "e") toggleControls();
  };
  const keyHandler = useLatest(onKey);
  const swipeHandler = useLatest((dir: Step) => jump(shown.current + dir, dir));
  const lineHandler = useLatest(jump);
  const onLine = useCallback((j: number) => lineHandler.current(j), [lineHandler]);

  useEffect(() => {
    const f = (e: KeyboardEvent) => keyHandler.current(e);
    document.addEventListener("keydown", f);
    return () => document.removeEventListener("keydown", f);
  }, [keyHandler]);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const stepper = createWheelStepper((dir) => swipeHandler.current(dir));
    const off = stepper.observe(el);
    return () => { off(); stepper.disconnect(); };
  }, [swipeHandler]);

  // ---- render ----
  const cls = ["sing", "karaoke", open && "open", chrome.on && "chrome-on", !chrome.on && !open && "idle", entering && "entering"]
    .filter(Boolean).join(" ");

  return (
    <section ref={root} className={cls} onPointerMove={(e) => { if (e.pointerType !== "touch") chrome.poke(); }} onDoubleClick={onDoubleClick}>
      <LyricList
        ref={list}
        activeIndex={active}
        lineCount={lines.length}
        locked={false}
        className={[!showPinyin && "hide-py", !showTranslation && "hide-tr"].filter(Boolean).join(" ")}
        onTouchStep={(dir) => jump(active + dir, dir)}
      >
        {lines.map((l, k) => (
          <LyricLine
            key={k}
            line={l}
            index={k}
            activeIndex={active}
            phase="idle"
            result={null}
            fresh={false}
            practiced={NONE}
            // Only the active line gets values that change; the others keep equal props and skip re-rendering.
            fill={k === active ? fill : null}
            note={null}
            cue={k === active ? cue : null}
            interactive={false}
            morphWord={null}
            awayWord={null}
            onWord={noop}
            onLine={onLine}
            onMorphDone={noop}
          />
        ))}
      </LyricList>

      <LineRail count={lines.length} active={active} lit={railLit} onPick={(j) => jump(j)} />

      <TopBar
        backLabel="Songs"
        onBack={exit}
        title={title}
        position={`${active + 1} / ${lines.length}`}
        badge="Karaoke"
        onHover={chrome.setOver}
      >
        <OptionsPill
          open={open}
          showPinyin={showPinyin}
          showTranslation={showTranslation}
          onToggleOpen={() => setOpen((v) => !v)}
          onTogglePinyin={togglePinyin}
          onToggleTranslation={toggleTranslation}
        />
      </TopBar>

      <KeyHints keys={KARAOKE_KEYS} />
      <Dock actions={karaokeActionsFor(playing, skipTo != null, open)} spinning={playing} recording={false} meter={null} onAction={onAction} />
    </section>
  );
}
