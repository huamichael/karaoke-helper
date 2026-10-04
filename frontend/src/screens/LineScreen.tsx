/**
 * Line screen: the main loop, used by both modes.
 *
 * Listen to the line, record, send for grading, show the result, then retry or go
 * to the next line. States: idle, listening, ready, recording, grading, result
 * (and failed). The state rules live in logic/lineMachine.ts and
 * logic/practiceMachine.ts; this file wires them to audio, the API and the screen.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, docs/design/ui.md §5.2–5.4.
 */
import { LayoutGroup } from "motion/react";
import { useCallback, useEffect, useReducer, useRef, useState, type MouseEvent } from "react";
import { ApiError, submitAttempt, type Mode, type Song } from "../api/client";
import { playLine, playWord, preloadTrack, type Playback } from "../audio/player";
import { openMic, sessionMic, simulatedMic, startRecording, type Mic, type Recording } from "../audio/recorder";
import { Dock } from "../components/Dock";
import { KeyHints } from "../components/KeyHints";
import { LineRail } from "../components/LineRail";
import { LyricLine } from "../components/LyricLine";
import { LyricList, type LyricListHandle } from "../components/LyricList";
import { MicPrompt, type MicPromptState } from "../components/MicPrompt";
import { OptionsPill } from "../components/OptionsPill";
import type { Meter } from "../components/RecordButton";
import { toast } from "../components/Toast";
import { TopBar } from "../components/TopBar";
import { WordPractice } from "../components/WordPracticePanel";
import { useChrome } from "../hooks/useChrome";
import { useLatest } from "../hooks/useLatest";
import { actionsFor, practiceActionsFor, type DockActionId } from "../logic/actions";
import { canChangeLine, initSession, latestResult, sessionReducer } from "../logic/lineMachine";
import { createWheelStepper, type Step } from "../logic/lineSwipe";
import { canLeave, earnedMark, openPractice, practiceReducer, type Practice, type PracticeEvent } from "../logic/practiceMachine";
import { fillFractions, recordLimitMs, wordLimitMs } from "../logic/timing";

/** title: the song's title as shown (the theme's Hanzi when it has one). */
type Props = { song: Song; title: string; mode: Mode; onExit(): void };

let hinted = false;
const NONE: number[] = [];

const failure = (e: ApiError, line: boolean) =>
  `${e.message} Your recording is kept${line ? ", so you can send it again" : ""}.`;

export default function LineScreen({ song, title, mode, onExit }: Props) {
  const lines = song.lines;
  const [s, dispatch] = useReducer(sessionReducer, lines.length, initSession);
  const [practice, setPractice] = useState<Practice | null>(null);
  const [morph, setMorph] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  const [showPinyin, setShowPinyin] = useState(true);
  const [showTranslation, setShowTranslation] = useState(true);
  const [fill, setFill] = useState<number[] | null>(null);
  const [prompt, setPrompt] = useState<(MicPromptState & { then: "line" | "word" }) | null>(null);
  const [mic, setMic] = useState<Mic | null>(sessionMic.current);
  const [meter, setMeter] = useState<Meter | null>(null);
  const [entering, setEntering] = useState(true);
  const [railLit, setRailLit] = useState(false);

  const root = useRef<HTMLElement>(null);
  const list = useRef<LyricListHandle>(null);
  const playback = useRef<Playback | null>(null);
  const recording = useRef<Recording | null>(null);
  const request = useRef<AbortController | null>(null);
  const railTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const live = useLatest({ s, practice, prompt, open });
  const chrome = useChrome(open || !!practice);

  const i = s.lineIndex;
  const result = latestResult(s);
  const last = i === lines.length - 1;

  const pdispatch = useCallback((e: PracticeEvent) => setPractice((p) => p && practiceReducer(p, e)), []);

  // ---- mount, unmount ----
  useEffect(() => {
    preloadTrack(song.audio_url);
    const t = setTimeout(() => setEntering(false), 1700);
    const h = hinted ? 0 : setTimeout(() => toast("Swipe or press ↑ ↓ to change line. Double-click anywhere for every control.", 4600), 1200);
    hinted = true;
    return () => {
      clearTimeout(t);
      if (h) clearTimeout(h);
      playback.current?.stop();
      recording.current?.cancel();
      request.current?.abort();
    };
  }, [song.audio_url]);

  // Keyboard focus follows practice: Record on open, Sing the line again on success, the word on close.
  const practisedWord = useRef<number | null>(null);
  const practicePhase = practice?.phase ?? null, practiceWord = practice?.wordIndex ?? null;
  useEffect(() => {
    const focus = (sel: string) => setTimeout(() => root.current?.querySelector<HTMLElement>(sel)?.focus({ preventScroll: true }), 80);
    if (practiceWord != null) {
      practisedWord.current = practiceWord;
      if (practicePhase === "ready") focus(".dock .rec");
      else if (practicePhase === "success") focus(".dock .btn.primary");
    } else if (practisedWord.current != null) {
      focus(`.line.active .word[data-w="${practisedWord.current}"]`);
      practisedWord.current = null;
    }
  }, [practicePhase, practiceWord]);

  // ---- playback ----
  const stopPlayback = () => {
    playback.current?.stop();
    playback.current = null;
  };

  const listen = () => {
    const { s } = live.current;
    if (s.phase === "listening") return stopPlayback();
    if (!["idle", "ready", "result", "failed"].includes(s.phase)) return;
    const l = lines[s.lineIndex];
    dispatch({ type: "listen" });
    const pb = playLine(song.audio_url, l, (ms) => setFill(fillFractions(l, ms)));
    playback.current = pb;
    pb.done.then((how) => {
      if (playback.current === pb) playback.current = null;
      if (how === "stopped") setFill(null);
      else setTimeout(() => { if (!playback.current) setFill(null); }, 250);
      dispatch({ type: "listenEnd" });
    });
  };

  // ---- recording ----
  const ensureMic = (then: "line" | "word") => {
    if (sessionMic.current) return true;
    setPrompt({ stage: "ask", error: null, then });
    return false;
  };

  const begin = (limitMs: number, onAudio: (b: Blob) => void) => {
    stopPlayback();
    const m = sessionMic.current!;
    const rec = startRecording(m, limitMs);
    recording.current = rec;
    setMeter({ level: () => m.level(), elapsedMs: () => performance.now() - rec.startedAt, limitMs });
    rec.done.then((blob) => {
      if (recording.current === rec) recording.current = null;
      if (blob) onAudio(blob);
    });
  };

  const send = (audio: Blob, t: Parameters<typeof submitAttempt>[1], ok: (r: Awaited<ReturnType<typeof submitAttempt>>) => void, fail: (e: ApiError) => void) => {
    request.current?.abort();
    const ctl = new AbortController();
    request.current = ctl;
    submitAttempt(audio, t, ctl.signal).then(ok, (e: ApiError) => { if (e.code !== "cancelled") fail(e); });
  };

  const sendLine = (audio: Blob, lineIndex: number) =>
    send(audio, { target: "line", songId: song.id, lineIndex, mode },
      (r) => dispatch({ type: "graded", result: r }),
      (e) => dispatch({ type: "failed", message: failure(e, true) }));

  const startLine = () => {
    const at = live.current.s.lineIndex;
    dispatch({ type: "record" });
    begin(recordLimitMs(lines[at]), (blob) => {
      dispatch({ type: "recorded", audio: blob });
      sendLine(blob, at);
    });
  };

  const record = () => {
    const { s } = live.current;
    if (s.phase === "recording") return recording.current?.stop();
    if (s.phase !== "ready" && s.phase !== "result") return;
    if (ensureMic("line")) startLine();
  };

  const resend = () => {
    const { s } = live.current;
    if (s.phase !== "failed" || !s.pending) return;
    dispatch({ type: "resend" });
    sendLine(s.pending, s.lineIndex);
  };

  const retry = () => {
    const { phase } = live.current.s;
    if (phase === "failed") resend();
    else if (phase === "result") record();
  };

  // ---- changing line ----
  const goTo = (j: number, dir: Step = j > live.current.s.lineIndex ? 1 : -1) => {
    const { s, practice } = live.current;
    if (j === s.lineIndex) return;
    if (!canChangeLine(s, !!practice)) {
      list.current?.nudge(dir);
      if (s.phase === "recording") toast("Stop recording to change line.");
      return;
    }
    if (j < 0 || j >= lines.length) return list.current?.bounce(dir);
    stopPlayback();
    setFill(null);
    list.current?.flip(() => dispatch({ type: "goto", index: j }));
    setRailLit(true);
    clearTimeout(railTimer.current);
    railTimer.current = setTimeout(() => setRailLit(false), 900);
  };

  const exit = () => {
    stopPlayback();
    recording.current?.cancel();
    request.current?.abort();
    onExit();
  };

  const next = () => {
    const { s } = live.current;
    if (s.phase === "recording" || s.phase === "grading") return;
    if (s.lineIndex >= lines.length - 1) {
      exit();
      toast("That's the whole song. Pick it again any time.");
    } else goTo(s.lineIndex + 1, 1);
  };

  // ---- word practice ----
  const openWord = (k: number) => {
    const { s, practice } = live.current;
    if (practice || s.phase === "recording" || s.phase === "grading") return;
    stopPlayback();
    setFill(null);
    setMorph(k); // the lyric's word gets the shared layoutId first, so Motion can measure it
    requestAnimationFrame(() => setPractice(openPractice(s.lineIndex, k)));
  };

  const closePractice = (after?: () => void) => {
    const p = live.current.practice;
    if (!p) return;
    recording.current?.cancel();
    request.current?.abort();
    stopPlayback();
    if (earnedMark(p)) dispatch({ type: "practised", wordIndex: p.wordIndex });
    setPractice(null);
    after?.();
    setTimeout(() => setMorph((m) => (live.current.practice ? m : null)), 900);
  };

  const pListen = () => {
    const p = live.current.practice;
    if (!p) return;
    if (p.phase === "playing") return stopPlayback();
    if (!["ready", "result", "failed"].includes(p.phase)) return;
    pdispatch({ type: "listen" });
    const pb = playWord(lines[p.lineIndex].words[p.wordIndex]);
    playback.current = pb;
    pb.done.then(() => {
      if (playback.current === pb) playback.current = null;
      pdispatch({ type: "listenEnd" });
    });
  };

  const sendWord = (audio: Blob, p: Practice) =>
    send(audio, { target: "word", songId: song.id, lineIndex: p.lineIndex, wordIndex: p.wordIndex },
      (r) => pdispatch({ type: "graded", result: r }),
      (e) => pdispatch({ type: "failed", message: failure(e, false) }));

  const startWord = () => {
    const p = live.current.practice;
    if (!p) return;
    const l = lines[p.lineIndex];
    pdispatch({ type: "record" });
    begin(wordLimitMs(l, l.words[p.wordIndex]), (blob) => {
      pdispatch({ type: "recorded", audio: blob });
      sendWord(blob, p);
    });
  };

  const pRecord = () => {
    const p = live.current.practice;
    if (!p) return;
    if (p.phase === "recording") return recording.current?.stop();
    if (!["ready", "result", "playing", "success"].includes(p.phase)) return;
    if (ensureMic("word")) startWord();
  };

  const pResend = () => {
    const p = live.current.practice;
    if (!p || p.phase !== "failed" || !p.pending) return;
    pdispatch({ type: "resend" });
    sendWord(p.pending, p);
  };

  const singAgain = () => closePractice(() => dispatch({ type: "singAgain" }));

  // ---- the microphone prompt ----
  const takeMic = (m: Mic) => {
    sessionMic.current = m;
    setMic(m);
    setPrompt((p) => p && { ...p, stage: "test", error: null });
  };
  const allowMic = () =>
    openMic().then(takeMic, () =>
      setPrompt((p) => p && { ...p, error: "The microphone is blocked. Allow it from the icon left of the address bar." }));
  const startFromPrompt = () => {
    const then = live.current.prompt?.then;
    setPrompt(null);
    if (then === "line") startLine();
    else if (then === "word") startWord();
  };

  // ---- actions, keys, gestures ----
  const onAction = (id: DockActionId) => {
    switch (id) {
      case "listen": return listen();
      case "record": return record();
      case "retry": return retry();
      case "resend": return resend();
      case "next": return next();
      case "plisten": return pListen();
      case "precord": return pRecord();
      case "presend": return pResend();
      case "confident": return closePractice();
      case "keep": return pdispatch({ type: "keep" });
      case "sing": return singAgain();
      case "busy": return;
    }
  };

  const togglePinyin = () => list.current?.flip(() => setShowPinyin((v) => !v));
  const toggleTranslation = () => list.current?.flip(() => setShowTranslation((v) => !v));

  const onKey = (e: KeyboardEvent) => {
    const { s, practice, prompt, open } = live.current;
    const t = e.target as HTMLElement;
    if (t.matches?.("input, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if (prompt) {
      if (k === "Escape") setPrompt(null);
      return;
    }
    if (k === "Escape") {
      if (practice) closePractice();
      else if (open) setOpen(false);
      return;
    }
    if (t.closest?.("button, [role=button]") && (k === " " || k === "Enter")) return;
    if (practice) {
      if (k === " ") { e.preventDefault(); pRecord(); }
      else if (k === "l") pListen();
      else if (k === "Enter" && practice.phase === "success") { e.preventDefault(); singAgain(); }
      return;
    }
    if (k === " ") {
      e.preventDefault();
      if (s.phase === "idle") listen();
      else if (s.phase === "result") retry();
      else record();
    } else if (k === "Enter") {
      e.preventDefault();
      if (s.phase === "failed") resend();
      else next();
    } else if (k === "l") listen();
    else if (k === "r") retry();
    else if (k === "p") togglePinyin();
    else if (k === "e") setOpen((v) => !v);
    else if (k === "ArrowDown") { e.preventDefault(); goTo(s.lineIndex + 1, 1); }
    else if (k === "ArrowUp") { e.preventDefault(); goTo(s.lineIndex - 1, -1); }
  };
  const keyHandler = useLatest(onKey);
  const swipeHandler = useLatest((dir: Step) => goTo(live.current.s.lineIndex + dir, dir));
  // Stable callbacks for the memoised lyric lines.
  const lineHandlers = useLatest({ openWord, goTo });
  const onWord = useCallback((k: number) => lineHandlers.current.openWord(k), [lineHandlers]);
  const onLine = useCallback((j: number) => lineHandlers.current.goTo(j), [lineHandlers]);
  const onMorphDone = useCallback(() => { if (!live.current.practice) setMorph(null); }, [live]);

  useEffect(() => {
    const f = (e: KeyboardEvent) => keyHandler.current(e);
    document.addEventListener("keydown", f);
    return () => document.removeEventListener("keydown", f);
  }, [keyHandler]);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const stepper = createWheelStepper((dir) => { if (!live.current.practice) swipeHandler.current(dir); });
    const off = stepper.observe(el);
    return () => { off(); stepper.disconnect(); };
  }, [live, swipeHandler]);

  const onDoubleClick = (e: MouseEvent) => {
    if ((e.target as HTMLElement).closest("button, .word, .dock, .opts, .advice, .f-mid, .f-below")) return;
    setOpen((v) => !v);
  };

  // While practising, a click on the faded lyrics ends practice (not while recording or grading).
  const onLyricsClick = (e: MouseEvent) => {
    const p = live.current.practice;
    if (!p) return;
    e.stopPropagation();
    e.preventDefault();
    if (canLeave(p)) closePractice();
  };

  // ---- render ----
  const actions = practice
    ? practiceActionsFor(practice.phase, practice.attempts.length)
    : actionsFor(s.phase, result?.next_step ?? null, open, { last });
  const recordingNow = practice ? practice.phase === "recording" : s.phase === "recording";
  const cls = [
    "sing", open && "open", practice && "practising", chrome.on && "chrome-on",
    !chrome.on && !open && !practice && "idle", entering && "entering",
  ].filter(Boolean).join(" ");

  return (
    <section ref={root} className={cls} onPointerMove={(e) => { if (e.pointerType !== "touch") chrome.poke(); }} onDoubleClick={onDoubleClick}>
      <LayoutGroup>
        <LyricList
          ref={list}
          activeIndex={i}
          lineCount={lines.length}
          locked={!canChangeLine(s, !!practice)}
          className={[!showPinyin && "hide-py", !showTranslation && "hide-tr"].filter(Boolean).join(" ")}
          onTouchStep={(dir) => goTo(i + dir, dir)}
          onClickCapture={practice ? onLyricsClick : undefined}
        >
          {lines.map((l, k) => (
            <LyricLine
              key={k}
              line={l}
              index={k}
              activeIndex={i}
              // Only the active line gets values that change; the others keep equal props and skip re-rendering.
              phase={k === i ? s.phase : "idle"}
              result={latestResult(s, k)}
              fresh={k === i && !!result && s.fresh === result.attempt_id}
              practised={s.practised[k] ?? NONE}
              fill={k === i ? fill : null}
              note={k === i ? s.note : null}
              interactive={k === i && !practice && s.phase !== "recording" && s.phase !== "grading"}
              morphWord={k === i ? morph : null}
              awayWord={k === i ? practice?.wordIndex ?? null : null}
              onWord={onWord}
              onLine={onLine}
              onMorphDone={onMorphDone}
            />
          ))}
        </LyricList>
        {practice && <WordPractice line={lines[practice.lineIndex]} practice={practice} />}
      </LayoutGroup>

      <LineRail count={lines.length} active={i} lit={railLit} onPick={(j) => goTo(j)} />

      <TopBar
        backLabel={practice ? `Line ${practice.lineIndex + 1}` : "Songs"}
        onBack={() => (practice ? closePractice() : exit())}
        title={title}
        position={`${i + 1} / ${lines.length}`}
        badge={mode === "singing" ? "Singing accuracy" : "Spoken accuracy"}
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

      <KeyHints />
      <Dock
        actions={actions}
        spinning={s.phase === "listening"}
        recording={recordingNow}
        meter={meter}
        onAction={onAction}
        promptKey={prompt?.stage}
        prompt={prompt ? (
          <MicPrompt state={prompt} mic={mic} onAllow={allowMic}
            onSimulate={() => takeMic(simulatedMic())} onStart={startFromPrompt} onCancel={() => setPrompt(null)} />
        ) : undefined}
      />
    </section>
  );
}
