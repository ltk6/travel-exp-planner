import { QUESTIONNAIRE_CONFIG } from "./questionnaire-config";

/**
 * Builds a reverse map: English tag (returned by backend) → Vietnamese label
 * (from the questionnaire option that produced it). Used for displaying
 * `metadata.tags` on location/activity cards in Vietnamese.
 *
 * Backend tags are lowercase English strings with spaces (e.g. "local market",
 * "trekking"). When the same tag appears under multiple questionnaire options,
 * the FIRST occurrence wins.
 */
const TAG_TO_LABEL_VI: Record<string, string> = (() => {
  const map: Record<string, string> = {};
  for (const q of QUESTIONNAIRE_CONFIG) {
    for (const sec of Object.values(q.categories ?? {})) {
      for (const [label, tags] of Object.entries(sec)) {
        for (const t of tags) {
          if (!map[t]) map[t] = label;
        }
      }
    }
    for (const sec of Object.values(q.specifics ?? {})) {
      for (const [label, tags] of Object.entries(sec)) {
        for (const t of tags) {
          if (!map[t]) map[t] = label;
        }
      }
    }
  }
  return map;
})();

export function labelForTag(tag: string): string {
  return TAG_TO_LABEL_VI[tag] ?? tag;
}
