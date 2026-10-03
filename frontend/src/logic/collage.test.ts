import { describe, expect, it } from "vitest";
import { SCRAPS, scrapBox, scrapPhotoSize, tornMask } from "./collage";

describe("scrapBox", () => {
  const g = { cx: 516.96, cy: 450, R: 504 };

  it("places each scrap on the rim at its angle, at the design's size when R = 504", () => {
    const wide = SCRAPS[0], t = (wide.a * Math.PI) / 180;
    const b = scrapBox(wide, g);
    expect(b.w).toBe(196);
    expect(b.h).toBe(124);
    expect(b.x + b.w / 2).toBeCloseTo(g.cx + g.R * wide.r * Math.cos(t));
    expect(b.y + b.h / 2).toBeCloseTo(g.cy + g.R * wide.r * Math.sin(t));
  });
  it("scales with the record", () => {
    expect(scrapBox(SCRAPS[1], { ...g, R: 252 }).h).toBeCloseTo(69);
  });
  it("cuts three different shapes: a wide taped piece, a narrow strip and a round cut", () => {
    expect(SCRAPS.map((s) => [s.w > s.h, !!s.tape])).toEqual([[true, true], [false, false], [true, false]]);
    expect(SCRAPS[2].poly.length).toBe(30);
  });
});

describe("scrapPhotoSize", () => {
  it("enlarges the background's cover crop by the scrap's zoom, so the detail is a little larger", () => {
    // background: the photo covers 106% of a 1440×900 window
    const [w, h] = scrapPhotoSize([2000, 1000], 1440, 900, 1.5);
    const cover = Math.max((1440 * 1.06) / 2000, (900 * 1.06) / 1000);
    expect(w).toBeCloseTo(2000 * cover * 1.5);
    expect(h).toBeCloseTo(1000 * cover * 1.5);
  });
});

describe("tornMask", () => {
  it("is an SVG data URL with a turbulence-torn circle", () => {
    const m = tornMask(4, 476, 26);
    expect(m.startsWith('url("data:image/svg+xml;utf8,')).toBe(true);
    const svg = decodeURIComponent(m.slice('url("data:image/svg+xml;utf8,'.length, -2));
    expect(svg).toContain("seed='4'");
    expect(svg).toContain("r='476'");
    expect(svg).toContain("scale='26'");
  });
});
