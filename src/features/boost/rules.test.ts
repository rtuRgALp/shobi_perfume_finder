import { describe, expect, it } from "vitest";
import { recommendBoost } from "./rules";
import type { Evidence } from "../../data/contracts";
const evidence: Evidence = {
  source: "https://www.fragrantica.com/p/1",
  status: "verified",
  retrievedAt: "2026-10-23",
  note: null,
};
describe("Essence Boost Guide", () => {
  it("preserves original light amounts", () => {
    expect(recommendBoost(["citrus", "aquatic"], evidence)).toMatchObject({
      available: true,
      classification: "Fresh / light",
      amounts: ["1ml", "2ml", "3ml"],
    });
  });
  it("heavy wins over light and exposes the triggering accords", () => {
    expect(
      recommendBoost(["citrus", "woody", "warm spicy"], evidence),
    ).toMatchObject({
      available: true,
      classification: "Heavy / gourmand",
      matchedAccords: ["woody", "warm spicy"],
      amounts: ["2ml", "3–4ml", "5ml"],
    });
  });
  it("requires source-backed evidence and an explicitly recognized accord", () => {
    for (const status of ["missing", "conflicting", "inherited"] as const)
      expect(recommendBoost(["woody"], { ...evidence, status }).available).toBe(
        false,
      );
    expect(recommendBoost([], evidence).available).toBe(false);
    expect(
      recommendBoost(["sweet", "vanilla", "mystery"], evidence).available,
    ).toBe(false);
    expect(
      recommendBoost(["woody"], { ...evidence, source: null }).available,
    ).toBe(false);
  });
  it("maps reviewed floral vocabulary without inferring from note names", () => {
    expect(recommendBoost(["white floral"], evidence)).toMatchObject({
      available: true,
      classification: "Fresh / light",
    });
    expect(recommendBoost(["jasmine"], evidence).available).toBe(false);
  });
  it("distinguishes provider assessments from verified observations", () => {
    expect(
      recommendBoost(["woody"], { ...evidence, status: "provider" }),
    ).toMatchObject({
      available: true,
      provenance: "provider",
      amounts: ["2ml", "3–4ml", "5ml"],
    });
    expect(recommendBoost(["woody"], evidence)).toMatchObject({
      provenance: "verified",
    });
  });
});
