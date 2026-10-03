import { describe, expect, it } from "vitest";
import type { SongTheme } from "../theme/songThemes";
import { buildEntries } from "./songList";

const pal = { c0: "#000", c1: "#111", c2: "#222", c3: "#333", accent: "#fff" };
const themes: Record<string, SongTheme> = {
  demo: { palette: pal },
  molihua: { palette: pal, title: "茉莉花", artist: "鳳飛飛" },
  yueliang: { palette: pal, title: "月亮代表我的心", artist: "鄧麗君" },
  untitled: { palette: pal },
};

describe("buildEntries", () => {
  it("lists the backend's songs first, in its order, ready to sing", () => {
    const e = buildEntries([{ id: "demo", title: "两只老虎", artist: "Traditional", line_count: 2 }], themes);
    expect(e[0]).toMatchObject({ id: "demo", title: "两只老虎", artist: "Traditional", playable: true });
  });
  it("adds themed songs the backend does not serve yet, as coming soon", () => {
    const e = buildEntries([{ id: "demo", title: "两只老虎", artist: "Traditional", line_count: 2 }], themes);
    expect(e.map((x) => [x.id, x.playable])).toEqual([["demo", true], ["molihua", false], ["yueliang", false]]);
    expect(e[1]).toMatchObject({ title: "茉莉花", artist: "鳳飛飛" });
  });
  it("makes a themed song playable once the backend serves it", () => {
    const e = buildEntries([{ id: "molihua", title: "茉莉花", artist: "Jiangsu folk song", line_count: 7 }], themes);
    expect(e.filter((x) => x.id === "molihua")).toHaveLength(1);
    expect(e[0]).toMatchObject({ id: "molihua", playable: true, artist: "鳳飛飛" });
  });
  it("gives a song without a theme the fallback palette", () => {
    const e = buildEntries([{ id: "new", title: "新歌", artist: "Someone", line_count: 3 }], {});
    expect(e[0].theme.palette.c0).toBeTruthy();
    expect(e[0].artist).toBe("Someone");
  });
});
