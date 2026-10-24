import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { catalogSchema, manifestSchema, profileSchema } from "./contracts";
describe("pipeline/frontend contract compatibility", () => {
  it("validates the entire produced catalog and all on-demand profiles", () => {
    const manifest = manifestSchema.parse(
      JSON.parse(readFileSync("public/data/current.json", "utf8")),
    );
    const index = catalogSchema.parse(
      JSON.parse(
        readFileSync("public/" + manifest.basePath + manifest.index, "utf8"),
      ),
    );
    expect(index.perfumes.length).toBe(manifest.count);
    expect(index.perfumes.length).toBeGreaterThanOrEqual(2253);
    index.perfumes.forEach((p) => {
      const profile = profileSchema.parse(
        JSON.parse(
          readFileSync(
            "public/" +
              manifest.basePath +
              manifest.profilePath +
              p.id +
              ".json",
            "utf8",
          ),
        ),
      );
      expect(profile.id).toBe(p.id);
      expect(profile.mainNotes).toEqual(p.mainNotes);
    });
  });
});
