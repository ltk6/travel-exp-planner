import { describe, it, expect } from "vitest";
import { ACTIVITY_TYPE_META, metaForActivityType } from "./activity-types";

describe("ACTIVITY_TYPE_META", () => {
  it("covers all 9 backend activity_type values", () => {
    const required = [
      "food",
      "adventure",
      "culture",
      "nightlife",
      "shopping",
      "relaxation",
      "nature",
      "photography",
      "experience",
    ] as const;
    for (const t of required) {
      expect(ACTIVITY_TYPE_META[t]).toBeDefined();
      expect(ACTIVITY_TYPE_META[t].label).toBeTruthy();
      expect(ACTIVITY_TYPE_META[t].classes).toMatch(/bg-/);
    }
  });

  it("Vietnamese labels are non-empty and look like Vietnamese (no English)", () => {
    expect(ACTIVITY_TYPE_META.food.label).toBe("Ẩm thực");
    expect(ACTIVITY_TYPE_META.adventure.label).toBe("Phiêu lưu");
    expect(ACTIVITY_TYPE_META.nightlife.label).toBe("Về đêm");
  });
});

describe("metaForActivityType", () => {
  it("returns matching meta for a known type", () => {
    expect(metaForActivityType("nature").label).toBe("Thiên nhiên");
  });

  it("returns fallback for unknown / null / undefined", () => {
    expect(metaForActivityType("totally-made-up").label).toBe("Khác");
    expect(metaForActivityType(undefined).label).toBe("Khác");
    expect(metaForActivityType(null).label).toBe("Khác");
    expect(metaForActivityType("").label).toBe("Khác");
  });
});
