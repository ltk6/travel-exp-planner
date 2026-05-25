import { describe, it, expect } from "vitest";
import {
  optionKey,
  parseKey,
  allKeysForQuestion,
  categoryKeysFor,
  specificKeysForSection,
  deriveTags,
  countAnswered,
} from "./questionnaire-helpers";
import { QUESTIONNAIRE_CONFIG } from "./questionnaire-config";

describe("optionKey / parseKey", () => {
  it("round-trips a category option", () => {
    const k = optionKey("q1_landscape", "cat", "⛰️ Địa hình", "Núi cao");
    expect(k).toBe("q1_landscape::cat::⛰️ Địa hình::Núi cao");
    expect(parseKey(k)).toEqual({
      qId: "q1_landscape",
      kind: "cat",
      section: "⛰️ Địa hình",
      option: "Núi cao",
    });
  });

  it("round-trips a specifics option", () => {
    const k = optionKey("q5_activities", "spec", "🥾 Phiêu lưu trên cạn", "Trekking");
    expect(parseKey(k)?.kind).toBe("spec");
    expect(parseKey(k)?.option).toBe("Trekking");
  });

  it("returns null for malformed keys", () => {
    expect(parseKey("bogus")).toBeNull();
    expect(parseKey("a::b::c")).toBeNull();
    expect(parseKey("a::wrong::b::c")).toBeNull();
  });
});

describe("allKeysForQuestion / categoryKeysFor / specificKeysForSection", () => {
  it("Q1 returns category + specifics keys", () => {
    const keys = allKeysForQuestion("q1_landscape");
    expect(keys.length).toBeGreaterThan(0);
    expect(keys.some((k) => k.includes("::cat::"))).toBe(true);
    expect(keys.some((k) => k.includes("::spec::"))).toBe(true);
  });

  it("Q2 has only category keys (no specifics)", () => {
    const cat = categoryKeysFor("q2_companion");
    const all = allKeysForQuestion("q2_companion");
    expect(cat.length).toBe(all.length); // no specifics
    expect(cat).toContain("q2_companion::cat::👥 Thành phần::Một mình");
  });

  it("Q5 has only specifics (no categories)", () => {
    const cat = categoryKeysFor("q5_activities");
    expect(cat).toHaveLength(0);
    const trekking = specificKeysForSection("q5_activities", "🥾 Phiêu lưu trên cạn");
    expect(trekking).toContain("q5_activities::spec::🥾 Phiêu lưu trên cạn::Trekking");
  });

  it("unknown question id returns empty array (no throw)", () => {
    expect(allKeysForQuestion("not-a-question")).toEqual([]);
    expect(categoryKeysFor("not-a-question")).toEqual([]);
    expect(specificKeysForSection("not-a-question", "any")).toEqual([]);
  });
});

describe("deriveTags", () => {
  it("returns empty for empty selection", () => {
    expect(deriveTags([])).toEqual([]);
  });

  it("collects tags from a single category option", () => {
    const k = optionKey("q1_landscape", "cat", "⛰️ Địa hình", "Núi cao");
    expect(deriveTags([k])).toEqual(["mountain"]);
  });

  it("collects tags from multiple selections in order", () => {
    const k1 = optionKey("q1_landscape", "cat", "⛰️ Địa hình", "Núi cao");
    const k2 = optionKey("q1_landscape", "cat", "🌊 Sông & Biển", "Bãi biển");
    expect(deriveTags([k1, k2])).toEqual(["mountain", "beach"]);
  });

  it("dedupes shared tags (Q6 budget+backpacking and Q2)", () => {
    // "Tiết kiệm / Bụi" emits ["budget", "backpacking"]; "Phượt bụi" also emits ["backpacking"]
    const budget = optionKey("q6_style", "spec", "💰 Ngân sách & Nhịp độ", "Tiết kiệm / Bụi");
    const phuotBui = optionKey("q6_style", "spec", "⏱️ Thời lượng & Dịp đặc biệt", "Phượt bụi");
    const tags = deriveTags([budget, phuotBui]);
    expect(tags).toContain("budget");
    expect(tags).toContain("backpacking");
    expect(tags.filter((t) => t === "backpacking")).toHaveLength(1);
  });

  it("ignores unknown selected keys gracefully", () => {
    expect(deriveTags(["totally::made::up::key"])).toEqual([]);
  });
});

describe("countAnswered", () => {
  it("returns 0 for empty selection", () => {
    expect(countAnswered([])).toBe(0);
  });

  it("counts each question with at least one selection exactly once", () => {
    const k1 = optionKey("q1_landscape", "cat", "⛰️ Địa hình", "Núi cao");
    const k1b = optionKey("q1_landscape", "cat", "🌊 Sông & Biển", "Bãi biển");
    const k2 = optionKey("q2_companion", "cat", "👥 Thành phần", "Một mình");
    expect(countAnswered([k1, k1b, k2])).toBe(2);
  });

  it("returns total when every question answered", () => {
    const keys = QUESTIONNAIRE_CONFIG.map((q) => allKeysForQuestion(q.id)[0]);
    expect(countAnswered(keys)).toBe(QUESTIONNAIRE_CONFIG.length);
  });
});
