import type { Perfume } from "../../data/contracts";

export const filterKeys = [
  "brand",
  "gender",
  "season",
  "note",
  "accord",
] as const;
export type FilterKey = (typeof filterKeys)[number];
export type Filters = Record<FilterKey, string[]>;
export type CatalogQuery = Filters & {
  q: string;
  sort: "brand" | "name" | "best";
  saved: boolean;
};
export const emptyQuery = (): CatalogQuery => ({
  q: "",
  sort: "brand",
  saved: false,
  brand: [],
  gender: [],
  season: [],
  note: [],
  accord: [],
});
export const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
export function parseQuery(params: URLSearchParams): CatalogQuery {
  return {
    ...emptyQuery(),
    q: (params.get("q") || "").slice(0, 200),
    sort: ["brand", "name", "best"].includes(params.get("sort") || "")
      ? (params.get("sort") as CatalogQuery["sort"])
      : "brand",
    saved: params.get("saved") === "1",
    ...(Object.fromEntries(
      filterKeys.map((key) => [key, [...new Set(params.getAll(key))]]),
    ) as Filters),
  };
}
export function serializeQuery(query: CatalogQuery) {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.sort !== "brand") params.set("sort", query.sort);
  if (query.saved) params.set("saved", "1");
  filterKeys.forEach((key) =>
    query[key].forEach((value) => params.append(key, value)),
  );
  const suffix = params.toString();
  return suffix ? "?" + suffix : "";
}
export function values(p: Perfume, key: FilterKey): string[] {
  return key === "brand"
    ? [p.brand]
    : key === "gender"
      ? p.gender
        ? [p.gender]
        : []
      : key === "season"
        ? p.seasons
        : key === "note"
          ? p.mainNotes.map((n) => n.name)
          : p.accords;
}
const collator = new Intl.Collator("en", {
  sensitivity: "base",
  numeric: true,
});
export function selectPerfumes(
  perfumes: Perfume[],
  query: CatalogQuery,
  favorites: Set<string>,
) {
  const tokens = normalize(query.q).split(" ").filter(Boolean);
  return perfumes
    .filter((p) => {
      if (query.saved && !favorites.has(p.code)) return false;
      const text = normalize(
        [p.name, ...(p.nameAliases || []), p.brand, p.code, ...p.aliases].join(
          " ",
        ),
      );
      if (!tokens.every((t) => text.includes(t))) return false;
      return filterKeys.every(
        (key) =>
          !query[key].length ||
          (key === "note" || key === "accord"
            ? query[key].every((v) => values(p, key).includes(v))
            : query[key].some((v) => values(p, key).includes(v))),
      );
    })
    .sort((a, b) => {
      if (query.sort === "best") {
        const diff =
          (a.bestSellerRank ?? Infinity) - (b.bestSellerRank ?? Infinity);
        if (diff && !Number.isNaN(diff)) return diff;
      }
      return (
        (query.sort === "name"
          ? collator.compare(a.name, b.name)
          : collator.compare(a.brand, b.brand)) ||
        collator.compare(a.name, b.name) ||
        collator.compare(a.id, b.id)
      );
    });
}
