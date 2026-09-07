/* A distinct voice per mandate, offline and free.
 *
 * The Web Speech API uses the operating system's own voices — on macOS that is
 * the same synthesiser behind `say`. No key, no cloud call, and no audio ever
 * leaves the machine, which is the only version of this feature compatible with
 * the project's constraints.
 *
 * Assignment is DETERMINISTIC. The CFO must sound like the CFO in every session
 * and in every replay, or the voice becomes noise rather than identity — so the
 * available voices are sorted by name and dealt out by seat index, rather than
 * picked by whatever order the OS happens to enumerate them in.
 *
 * Off by default. A page that starts talking when you open it is a page people
 * close.
 */

import { SEATS, type Seat } from "./chamber";

export type VoiceMap = Partial<Record<Seat, SpeechSynthesisVoice>>;

export function speechAvailable(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/** Voices arrive asynchronously in most browsers; this resolves once they have. */
export function loadVoices(timeoutMs = 2000): Promise<SpeechSynthesisVoice[]> {
  if (!speechAvailable()) return Promise.resolve([]);
  const existing = window.speechSynthesis.getVoices();
  if (existing.length) return Promise.resolve(existing);

  return new Promise((resolve) => {
    const done = () => resolve(window.speechSynthesis.getVoices());
    window.speechSynthesis.addEventListener("voiceschanged", done, { once: true });
    setTimeout(done, timeoutMs);
  });
}

/** Deal voices to seats: sorted, then by index, so the mapping never drifts. */
export function assignVoices(voices: SpeechSynthesisVoice[], lang = "en"): VoiceMap {
  if (!voices.length) return {};
  const preferred = voices.filter((v) => v.lang.toLowerCase().startsWith(lang.toLowerCase()));
  const pool = (preferred.length >= SEATS.length ? preferred : voices)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name));

  return Object.fromEntries(
    SEATS.map((seat, i) => [seat, pool[i % pool.length]]),
  ) as VoiceMap;
}

/** Pitch and rate nudged per seat so two seats sharing a voice still differ. */
function timbre(seat: Seat): { pitch: number; rate: number } {
  const i = SEATS.indexOf(seat);
  return { pitch: 0.85 + i * 0.07, rate: 0.98 + (i % 3) * 0.04 };
}

export function speak(seat: Seat, text: string, voices: VoiceMap, lang = "en"): void {
  if (!speechAvailable() || !text.trim()) return;
  const utterance = new SpeechSynthesisUtterance(text.slice(0, 900));
  const voice = voices[seat];
  if (voice) utterance.voice = voice;
  utterance.lang = voice?.lang ?? lang;
  const { pitch, rate } = timbre(seat);
  utterance.pitch = pitch;
  utterance.rate = rate;
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking(): void {
  if (speechAvailable()) window.speechSynthesis.cancel();
}
