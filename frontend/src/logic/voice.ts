/**
 * Which browser voice speaks Mandarin when a word has no clip (or a line has no
 * track). Setting only lang = "zh-CN" lets Chrome on macOS take the first match,
 * Eddy, one of Apple's novelty voices, which sounds like fake Chinese. So pick by
 * name: Microsoft's Xiaoxiao (the voice of the word clips, in Edge), then
 * Tingting (macOS, works offline), Chrome's Google 普通话, Li-Mu, Yu-shu, then
 * any other mainland voice, then any other Mandarin one. Null: let the browser choose.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Spoken reference in Word practice").
 */

const NOVELTY = /^(eddy|flo|grandma|grandpa|reed|rocko|sandy|shelley)\b/i;
const PREFERRED = [/xiaoxiao/i, /ting-?ting/i, /google.*(普通话|mandarin)/i, /li-?mu/i, /yu-?shu/i];
const CHINESE = /^(zh|cmn)/i;
const MAINLAND = /^(zh|cmn)[-_](cn|hans)/i;
const CANTONESE = /[-_](hk|yue)/i;

export function pickVoice<V extends { name: string; lang: string }>(voices: V[]): V | null {
  const usable = voices.filter((v) => CHINESE.test(v.lang) && !NOVELTY.test(v.name) && !CANTONESE.test(v.lang));
  for (const re of PREFERRED) {
    const hit = usable.find((v) => re.test(v.name));
    if (hit) return hit;
  }
  return usable.find((v) => MAINLAND.test(v.lang)) ?? usable[0] ?? null;
}
