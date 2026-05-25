import { describe, it, expect } from "vitest";
import { labelForTag } from "./tag-map";

describe("labelForTag", () => {
  it("maps known English tags to Vietnamese labels", () => {
    expect(labelForTag("mountain")).toBe("Núi cao");
    expect(labelForTag("beach")).toBe("Bãi biển");
    expect(labelForTag("trekking")).toBe("Trekking"); // matches questionnaire option directly
    expect(labelForTag("luxury")).toBe("Sang trọng");
  });

  it("returns the tag unchanged when not in the questionnaire vocabulary", () => {
    expect(labelForTag("some-untracked-tag")).toBe("some-untracked-tag");
    expect(labelForTag("")).toBe("");
  });
});
