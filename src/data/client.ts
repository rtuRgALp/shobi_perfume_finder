import {
  catalogSchema,
  manifestSchema,
  profileSchema,
  type Manifest,
  type Profile,
} from "./contracts";

export const publicUrl = (path: string) => `${import.meta.env.BASE_URL}${path}`;
async function get(path: string, signal?: AbortSignal) {
  const response = await fetch(publicUrl(path), {
    signal,
    cache: path === "data/current.json" ? "no-cache" : "default",
  });
  if (!response.ok)
    throw new Error(
      "The fragrance library could not be loaded. Please try again.",
    );
  return response.json();
}
export async function loadCatalog(signal?: AbortSignal) {
  const manifest = manifestSchema.parse(await get("data/current.json", signal));
  const catalog = catalogSchema.parse(
    await get(manifest.basePath + manifest.index, signal),
  );
  if (manifest.count !== catalog.perfumes.length)
    throw new Error("The library is updating. Please try again.");
  return { manifest, perfumes: catalog.perfumes };
}
const profiles = new Map<string, Profile>();
export async function loadProfile(
  id: string,
  manifest: Manifest,
  signal?: AbortSignal,
) {
  if (!/^shobi-\d+$/.test(id))
    throw new Error("This fragrance could not be found.");
  const key = manifest.releaseId + id;
  if (profiles.has(key)) return profiles.get(key)!;
  const profile = profileSchema.parse(
    await get(manifest.basePath + manifest.profilePath + id + ".json", signal),
  );
  if (profile.id !== id) throw new Error("This fragrance could not be found.");
  profiles.set(key, profile);
  return profile;
}
