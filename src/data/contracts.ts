import { z } from "zod";

const httpsUrl = z
  .string()
  .url()
  .refine((v) => v.startsWith("https://"));
const assetPath = z
  .string()
  .regex(/^assets\/[a-zA-Z0-9_./-]+$/)
  .nullable();
export const evidenceSchema = z.object({
  source: httpsUrl.nullable(),
  status: z.enum([
    "verified",
    "provider",
    "inherited",
    "missing",
    "conflicting",
  ]),
  retrievedAt: z.string().nullable(),
  note: z.string().nullable(),
});
const noteSchema = z.object({ name: z.string(), icon: assetPath });
const metricSchema = z
  .object({
    value: z.number(),
    scale: z.string(),
    votes: z.number().int().nonnegative().nullable(),
  })
  .nullable();
const performanceSchema = metricSchema.or(
  z.object({ label: z.string().min(1), scale: z.string(), votes: z.null() }),
);
const listingSchema = z.object({
  id: z.string().regex(/^\d+$/),
  code: z.string().min(1),
  aliases: z.array(z.string()),
  originalId: z.string(),
  url: httpsUrl.refine((v) => new URL(v).hostname === "leparfum.com.gr"),
  status: z.enum(["active", "unavailable", "unknown"]),
  addedDate: z.string().nullable(),
  bestSellerRank: z.number().int().positive().nullable(),
});
export const perfumeSchema = z.object({
  id: z.string().regex(/^shobi-\d+$/),
  name: z.string().min(1),
  nameAliases: z.array(z.string()).optional(),
  brand: z.string().min(1),
  image: assetPath,
  gender: z.string().nullable(),
  seasons: z.array(z.string()),
  mainNotes: z.array(noteSchema),
  accords: z.array(z.string()),
  validationStatus: z.enum(["green", "yellow", "red"]),
  code: z.string(),
  aliases: z.array(z.string()),
  addedDate: z.string().nullable(),
  bestSellerRank: z.number().int().positive().nullable(),
});
export const profileSchema = perfumeSchema
  .omit({ code: true, aliases: true, addedDate: true, bestSellerRank: true })
  .extend({
    schemaVersion: z.literal(1),
    edition: z.string().nullable(),
    fragranticaId: z.string().regex(/^\d+$/).nullable(),
    fragranticaUrl: httpsUrl.nullable(),
    imageEvidence: evidenceSchema,
    pyramid: z.object({
      top: z.array(z.string()),
      heart: z.array(z.string()),
      base: z.array(z.string()),
    }),
    description: z.string().nullable(),
    rating: metricSchema,
    longevity: performanceSchema,
    sillage: performanceSchema,
    evidence: z.record(z.string(), evidenceSchema),
    validationIssues: z.array(z.string()),
    validationChecks: z.record(z.string(), z.boolean()),
    listings: z.array(listingSchema).min(1),
  });
export const catalogSchema = z.object({
  schemaVersion: z.literal(1),
  perfumes: z.array(perfumeSchema),
});
export const manifestSchema = z.object({
  schemaVersion: z.literal(1),
  releaseId: z.string().regex(/^[a-f0-9]{16}$/),
  generatedAt: z.string(),
  basePath: z.string().regex(/^data\/releases\/[a-f0-9]{16}\/$/),
  index: z.literal("index.json"),
  profilePath: z.literal("profiles/"),
  count: z.number().int(),
  coverage: z.record(z.string(), z.number()),
  validation: z.record(z.string(), z.number()),
});
export type Perfume = z.infer<typeof perfumeSchema>;
export type Profile = z.infer<typeof profileSchema>;
export type Evidence = z.infer<typeof evidenceSchema>;
export type Manifest = z.infer<typeof manifestSchema>;
