import { QUESTIONNAIRE_CONFIG } from "./questionnaire-config";

export type OptionKind = "cat" | "spec";

export function optionKey(qId: string, kind: OptionKind, section: string, option: string): string {
  return `${qId}::${kind}::${section}::${option}`;
}

/** Walk config and collect all keys grouped by question. */
export function allKeysForQuestion(qId: string): string[] {
  const q = QUESTIONNAIRE_CONFIG.find((x) => x.id === qId);
  if (!q) return [];
  const keys: string[] = [];
  for (const [section, opts] of Object.entries(q.categories ?? {})) {
    for (const opt of Object.keys(opts)) keys.push(optionKey(qId, "cat", section, opt));
  }
  for (const [section, opts] of Object.entries(q.specifics ?? {})) {
    for (const opt of Object.keys(opts)) keys.push(optionKey(qId, "spec", section, opt));
  }
  return keys;
}

export function categoryKeysFor(qId: string): string[] {
  const q = QUESTIONNAIRE_CONFIG.find((x) => x.id === qId);
  if (!q) return [];
  const keys: string[] = [];
  for (const [section, opts] of Object.entries(q.categories ?? {})) {
    for (const opt of Object.keys(opts)) keys.push(optionKey(qId, "cat", section, opt));
  }
  return keys;
}

export function specificKeysForSection(qId: string, section: string): string[] {
  const q = QUESTIONNAIRE_CONFIG.find((x) => x.id === qId);
  if (!q) return [];
  const opts = q.specifics?.[section];
  if (!opts) return [];
  return Object.keys(opts).map((opt) => optionKey(qId, "spec", section, opt));
}

/** Derive deduped tag list from selected keys. */
export function deriveTags(selectedKeys: string[]): string[] {
  const selected = new Set(selectedKeys);
  const tags: string[] = [];
  const seen = new Set<string>();

  for (const q of QUESTIONNAIRE_CONFIG) {
    for (const [section, opts] of Object.entries(q.categories ?? {})) {
      for (const [opt, tagList] of Object.entries(opts)) {
        if (selected.has(optionKey(q.id, "cat", section, opt))) {
          for (const t of tagList) {
            if (!seen.has(t)) {
              seen.add(t);
              tags.push(t);
            }
          }
        }
      }
    }
    for (const [section, opts] of Object.entries(q.specifics ?? {})) {
      for (const [opt, tagList] of Object.entries(opts)) {
        if (selected.has(optionKey(q.id, "spec", section, opt))) {
          for (const t of tagList) {
            if (!seen.has(t)) {
              seen.add(t);
              tags.push(t);
            }
          }
        }
      }
    }
  }
  return tags;
}

/** Count questions that have at least one selected option. */
export function countAnswered(selectedKeys: string[]): number {
  const selected = new Set(selectedKeys);
  let answered = 0;
  for (const q of QUESTIONNAIRE_CONFIG) {
    const keys = allKeysForQuestion(q.id);
    if (keys.some((k) => selected.has(k))) answered += 1;
  }
  return answered;
}

export function parseKey(
  key: string,
): { qId: string; kind: OptionKind; section: string; option: string } | null {
  const parts = key.split("::");
  if (parts.length !== 4) return null;
  const [qId, kind, section, option] = parts;
  if (kind !== "cat" && kind !== "spec") return null;
  return { qId, kind, section, option };
}
