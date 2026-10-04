/**
 * Per-song design data, keyed by song id. Not part of the API.
 *
 * Each song has a five-colour palette, and may have a photograph (Unsplash
 * License, in public/photos), an album cover (copyrighted: public/covers, which
 * git ignores), the recording's artist, album and year, how the title splits over
 * two lines on the song screen, and where the collage scraps look into the photo.
 *
 * A theme with a title but no matching song from the backend shows on the record
 * as "Coming soon" (docs/design/ui.md §5.1).
 *
 * Owner: A. Spec: docs/design/ui.md §3.1, §5.1, §9 question 7.
 */
export type Palette = { c0: string; c1: string; c2: string; c3: string; accent: string };

export type SongTheme = {
  palette: Palette;
  /** The title in Hanzi, as shown; wins over the backend's, which may be romanised. */
  title?: string;
  /** The title over two staggered lines: 茉莉 / 花. */
  split?: [string, string?];
  titlePinyin?: string;
  titleEnglish?: string;
  blurb?: string;
  photo?: string;
  photoCredit?: { name: string; url: string };
  cover?: string;
  artist?: string;
  album?: string;
  year?: string;
  /** Where each collage scrap looks into the photo (CSS background-position), one per scrap. */
  focus?: [string, string, string];
};

export const FALLBACK_PALETTE: Palette = { c0: "#15141f", c1: "#3b3f6b", c2: "#6b4a6a", c3: "#2f5a5a", accent: "#ece8ff" };

export const SONG_THEMES: Record<string, SongTheme> = {
  demo: {
    palette: { c0: "#1f160e", c1: "#8a4b1f", c2: "#f0c27a", c3: "#5a3a22", accent: "#f7d9a8" },
    split: ["两只", "老虎"],
    titlePinyin: "liǎng zhī lǎo hǔ",
    titleEnglish: "Two Tigers",
    blurb: "A children's round sung to the tune of Frère Jacques. Short words, one per note: the easiest place to start.",
    artist: "Traditional",
  },
  "jasmine-flower": {
    title: "茉莉花",
    palette: { c0: "#0f231a", c1: "#2f6b4f", c2: "#d9e4c4", c3: "#5f9c7a", accent: "#f4f1d6" },
    split: ["茉莉", "花"],
    titlePinyin: "mò lì huā",
    titleEnglish: "Jasmine Flower",
    blurb: "A Jiangsu folk song, as 鳳飛飛 sang it in 1971. Slow, with one syllable per note, so every word is easy to hear.",
    photo: "/photos/molihua.jpg",
    photoCredit: { name: "Irina Iriser", url: "https://unsplash.com/photos/vB4_CtsfaZ0" },
    cover: "/covers/molihua.jpg",
    focus: ["72% 22%", "46% 38%", "30% 72%"],
    artist: "鳳飛飛",
    album: "鳳飛飛 金賞輯 3",
    year: "1971",
  },
  "yi-jian-mei": {
    title: "一剪梅",
    palette: { c0: "#1d1222", c1: "#7a2f4f", c2: "#e7b8c6", c3: "#4a3a6b", accent: "#f8d3de" },
    split: ["一剪", "梅"],
    titlePinyin: "yì jiǎn méi",
    titleEnglish: "A Spray of Plum Blossoms",
    blurb: "Fei Yu-ching's ballad. Long held notes that test how cleanly you finish each word.",
    photo: "/photos/yijianmei.jpg",
    photoCredit: { name: "yamasa-n", url: "https://unsplash.com/photos/SPEUTg0phCg" },
    cover: "/covers/yijianmei.jpg",
    focus: ["34% 30%", "52% 64%", "68% 58%"],
    artist: "費玉清",
    album: "清韻悠揚 精選（一）",
    year: "1983",
  },
  "yue-liang-dai-biao-wo-de-xin": {
    title: "月亮代表我的心",
    palette: { c0: "#161230", c1: "#3b2f78", c2: "#f2cf7a", c3: "#6b4fa0", accent: "#f7dd99" },
    split: ["月亮代表", "我的心"],
    titlePinyin: "yuè liàng dài biǎo wǒ de xīn",
    titleEnglish: "The Moon Represents My Heart",
    blurb: "Teresa Teng's best-known love song, sung all over the world.",
    photo: "/photos/yueliang.jpg",
    photoCredit: { name: "Laura Cleffmann", url: "https://unsplash.com/photos/gRT7o73xua0" },
    cover: "/covers/yueliang.jpg",
    focus: ["42% 40%", "58% 52%", "50% 47%"],
    artist: "鄧麗君",
    album: "島國之情歌 第四集 香港之戀",
    year: "1977",
  },
};

export const themeFor = (songId: string): SongTheme => SONG_THEMES[songId] ?? { palette: FALLBACK_PALETTE };

/** Crossfade every colour on the page: the five are registered with @property, so they animate. */
export function applyPalette(p: Palette) {
  const root = document.documentElement.style;
  for (const [k, v] of Object.entries(p)) root.setProperty(`--${k}`, v);
}
