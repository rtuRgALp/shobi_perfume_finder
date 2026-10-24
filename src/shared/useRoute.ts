import { useSyncExternalStore } from "react";
import {
  parseQuery,
  serializeQuery,
  type CatalogQuery,
} from "../features/catalog/query";

const subscribe = (fn: () => void) => {
  window.addEventListener("hashchange", fn);
  return () => window.removeEventListener("hashchange", fn);
};
export function useRoute() {
  const hash = useSyncExternalStore(
    subscribe,
    () => window.location.hash || "#/",
  );
  const [path, search = ""] = hash.slice(1).split("?");
  let detailId: string | null = null;
  try {
    detailId = path.startsWith("/perfume/")
      ? decodeURIComponent(path.slice(9))
      : null;
  } catch {
    detailId = "invalid";
  }
  return { detailId, query: parseQuery(new URLSearchParams(search)) };
}
export function navigate(query: CatalogQuery, id?: string, replace = false) {
  const hash =
    "#" +
    (id ? "/perfume/" + encodeURIComponent(id) : "/") +
    serializeQuery(query);
  if (window.location.hash === hash) return;
  // Updating filters is state navigation, not a fragment jump. Fragment navigation
  // dismisses native dialogs in Chromium, which would close the mobile sheet.
  if (replace) history.replaceState(null, "", hash);
  else history.pushState(null, "", hash);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
export const detailHref = (id: string, query: CatalogQuery) =>
  "#/perfume/" + encodeURIComponent(id) + serializeQuery(query);
