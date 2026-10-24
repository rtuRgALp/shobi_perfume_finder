import { describe, expect, it } from "vitest";
import {
  emptyQuery,
  parseQuery,
  selectPerfumes,
  serializeQuery,
} from "./query";
import type { Perfume } from "../../data/contracts";

const perfume = (patch: Partial<Perfume> = {}): Perfume => ({
  id: "shobi-1",
  name: "Néroli",
  brand: "Example",
  code: "10-EX",
  aliases: ["11-EX"],
  image: null,
  gender: "unisex",
  seasons: ["summer"],
  mainNotes: [
    { name: "Neroli", icon: null },
    { name: "Citrus", icon: null },
  ],
  accords: ["citrus"],
  validationStatus: "green",
  addedDate: "2026-10-19",
  bestSellerRank: null,
  ...patch,
});
describe("catalog queries", () => {
  it("round trips shareable filters and ignores invalid sorts", () => {
    const q = {
      ...emptyQuery(),
      q: "Maison & Co",
      brand: ["A & B"],
      note: ["Neroli", "Citrus"],
      saved: true,
    };
    expect(parseQuery(new URLSearchParams(serializeQuery(q)))).toEqual(q);
    expect(parseQuery(new URLSearchParams("sort=evil")).sort).toBe("brand");
  });
  it("searches aliases, normalized accents, brands and codes", () => {
    for (const q of ["neroli", "11 EX", "example", "10-EX"])
      expect(
        selectPerfumes([perfume()], { ...emptyQuery(), q }, new Set()),
      ).toHaveLength(1);
  });
  it("searches established full names without changing listing codes or favorites", () => {
    const p = perfume({ name: "Avent", nameAliases: ["Aventus"] });
    expect(
      selectPerfumes(
        [p],
        { ...emptyQuery(), q: "Aventus", saved: true },
        new Set([p.code]),
      ),
    ).toEqual([p]);
    expect(
      selectPerfumes(
        [p],
        { ...emptyQuery(), q: "Aventus", saved: true },
        new Set(),
      ),
    ).toEqual([]);
  });
  it("composes saved scope with brand, search and notes", () => {
    const q = {
      ...emptyQuery(),
      saved: true,
      brand: ["Example"],
      note: ["Neroli", "Citrus"],
      q: "neroli",
    };
    expect(
      selectPerfumes(
        [perfume(), perfume({ id: "shobi-2", code: "12-EX" })],
        q,
        new Set(["10-EX"]),
      ),
    ).toHaveLength(1);
    expect(
      selectPerfumes([perfume()], { ...q, note: ["Rose"] }, new Set(["10-EX"])),
    ).toHaveLength(0);
  });
  it("sorts ranked products first with a stable unranked fallback", () => {
    const rows = [
      perfume(),
      perfume({ id: "shobi-2", name: "Alpha", bestSellerRank: 2 }),
      perfume({ id: "shobi-3", name: "Zulu", bestSellerRank: 1 }),
    ];
    expect(
      selectPerfumes(rows, { ...emptyQuery(), sort: "best" }, new Set()).map(
        (p) => p.name,
      ),
    ).toEqual(["Zulu", "Alpha", "Néroli"]);
  });
});
