import { describe, expect, it } from "vitest";
import { pickVoice } from "./voice";

const v = (name: string, lang: string) => ({ name, lang });

// The Chinese voices Chrome on macOS lists, in its own order (Eddy comes first).
const MAC = [
  v("Eddy (Chinese (China mainland))", "zh-CN"), v("Eddy (Chinese (Taiwan))", "zh-TW"),
  v("Flo (Chinese (China mainland))", "zh-CN"), v("Grandma (Chinese (China mainland))", "zh-CN"),
  v("Grandpa (Chinese (China mainland))", "zh-CN"), v("Li-Mu", "zh-CN"), v("Meijia", "zh-TW"),
  v("Reed (Chinese (China mainland))", "zh-CN"), v("Rocko (Chinese (China mainland))", "zh-CN"),
  v("Sandy (Chinese (China mainland))", "zh-CN"), v("Shelley (Chinese (China mainland))", "zh-CN"),
  v("Sinji", "zh-HK"), v("Tingting", "zh-CN"), v("Yu-shu", "zh-CN"), v("Samantha", "en-US"),
];

describe("pickVoice", () => {
  it("never picks a novelty voice such as Eddy, which reads Mandarin like fake Chinese", () => {
    expect(pickVoice(MAC)?.name).toBe("Tingting");
  });
  it("prefers Microsoft's Xiaoxiao, the voice of the word clips, where the browser has it", () => {
    expect(pickVoice([...MAC, v("Microsoft Xiaoxiao Online (Natural) - Chinese (Mainland)", "zh-CN")])?.name).toContain("Xiaoxiao");
  });
  it("takes Chrome's Google Mandarin voice when the system has no good one", () => {
    expect(pickVoice([v("Eddy (Chinese (China mainland))", "zh-CN"), v("Google 普通话（中国大陆）", "zh-CN")])?.name).toBe("Google 普通话（中国大陆）");
  });
  it("falls back to any mainland voice that is not a novelty one, then other Mandarin", () => {
    expect(pickVoice([v("Eddy (Chinese (China mainland))", "zh-CN"), v("Some Voice", "zh_CN")])?.name).toBe("Some Voice");
    expect(pickVoice([v("Eddy (Chinese (Taiwan))", "zh-TW"), v("Meijia", "zh-TW")])?.name).toBe("Meijia");
  });
  it("leaves the choice to the browser when only novelty voices exist", () => {
    expect(pickVoice([v("Eddy (Chinese (China mainland))", "zh-CN"), v("Samantha", "en-US")])).toBeNull();
    expect(pickVoice([])).toBeNull();
  });
});
