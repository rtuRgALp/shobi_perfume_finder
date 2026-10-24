export const FAVORITES_KEY = "shobi-favorites";
export function readFavorites(): Set<string> {
  try {
    const parsed: unknown = JSON.parse(
      localStorage.getItem(FAVORITES_KEY) || "[]",
    );
    return new Set(
      Array.isArray(parsed)
        ? parsed.filter(
            (v): v is string => typeof v === "string" && v.length < 100,
          )
        : [],
    );
  } catch {
    return new Set();
  }
}
export function saveFavorites(favorites: Set<string>) {
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
    return true;
  } catch {
    return false;
  }
}
