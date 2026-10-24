# Shobi Perfume Finder

A calm, searchable guide to Shobi perfume inspirations. React, TypeScript and Vite power a static application; a separate Python pipeline owns catalog import, source hydration, evidence and publication.

## Run locally

Requires Node.js 22+, pnpm 11.25 and Python 3.12+.

```sh
pnpm install
pnpm dev
```

The supplied certified catalog and referenced images are already included. No source requests or reference repositories are required to browse or build.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r pipeline/requirements.txt
pnpm test
python -m unittest discover -s pipeline/tests -v
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

`python -m pipeline.cli bootstrap` is a one-time import from the supplied MarvvRed reference tree. It resets enrichment, so use `build` or `refresh` for normal work. `build` is deterministic for identical catalog inputs and does not fetch sources. `rollback` swaps the current and previous release pointers.

## Application structure

- `src/features`: discovery/filtering, details, favorites and pure Essence Boost rules.
- `src/data`: validated public contracts, catalog loading and on-demand profile requests.
- `pipeline`: import, cached source adapters, exact identity checks, hydration and atomic release generation.
- `contracts/profile.schema.json`: versioned producer contract. Frontend compatibility tests validate every generated profile.
- `data/catalog`: maintained original profiles, Shobi listings, duplicate aliases and inherited certification evidence.
- `public/data`: compact discovery index, on-demand profiles and release manifests. The current and previous releases are retained.

URLs use hash routes and work beneath a GitHub Pages repository subdirectory. Search, filters, sorting and saved scope are shareable; favorites remain local to the browser. Existing `shobi-favorites` values and documented duplicate codes are recognized on the same browser origin. A new hosting origin cannot read another site's local storage.

## Data and recommendations

The baseline contains **2,253 perfumes: 2,247 green and six intentionally yellow**, plus 25 documented duplicate-code aliases. Main Notes retain their certified Social Card order. Note pyramids are independently sourced fields and never replace Main Notes.

Every enrichment field carries its own source, retrieval time and evidence state. Missing descriptions, accords, rating, longevity and sillage remain unavailable; neither the interface nor the pipeline invents them. Community measurements describe the original perfume, not Shobi's interpretation. Main accords in the legacy original database are not imported as verified facts.

The Essence Boost Guide preserves the original recommendation amounts and makes its rules explicit. Heavy triggers take precedence over light triggers; only reviewed accord vocabulary with source-backed evidence can produce guidance. Fragella assessments have a separate `provider` evidence state and are never relabeled as verified observations. Provenance and limitations remain in the data and project notes; shopping pages focus on the fragrance information and recommendation. Missing, conflicting and unrecognized accord inputs produce an unavailable state. The guide is an inherited heuristic, not measured performance advice.

## Launch snapshot hydration

The prepared launch snapshot contains accords for **2,235 fragrances** and Essence Boost guidance for **2,220**, across the complete 2,253-perfume catalog. Complete note pyramids are available for **2,113 perfumes**. See [the launch snapshot report](docs/launch-snapshot.md) for coverage, provenance, verification and unresolved mappings.

The Fragella collector is an explicit preparation step, separate from deployment:

```sh
python -m pipeline.fragella_snapshot collect
python -m pipeline.fragella_resolve
# Inspect data/reports/fragella-resolution.json before publishing.
python -m pipeline.fragella_resolve --publish
```

Set `FRAGELLA_API_KEY` in the environment or ignored `.env.local`. Collection is resumable, uses at most six concurrent requests at two starts per second by default, and shares a persistent ceiling of 4,980 new attempts across the entire launch collection and its fallback passes. A process lock prevents overlapping collectors. Authentication/quota failures stop further work. Do not delete the private ledger to obtain a fresh budget. Existing successful responses are reused without network access.

The identity resolver requires exact normalized names, documented brand aliases, nonconflicting explicit concentration and gender, and corroboration from inherited Main Notes. Known display prefixes and the ampersands omitted by established source URLs are handled explicitly. Reviewed regional note synonyms are used only to corroborate identity, never to infer Boost classification or rewrite Main Notes. Individually reviewed audience exceptions are pinned to original and provider IDs and cannot waive the other identity checks. The resolver rejects fuzzy matches, conflicting duplicates, and provider IDs that would merge distinct mapped originals. Unresolved identities remain searchable with their existing fields. Approved mappings are retained by stable provider ID. Provider performance labels retain their descriptive scale; ratings retain the provider's Bayesian scale and do not invent vote counts. Existing enrichment, images, identity associations, Main Notes and certification are preserved; reviewed abbreviated display names retain their old search aliases. Raw responses and review reports stay outside public assets.

## Snapshot publication and deployment

The launch catalog is a fixed snapshot, intended as a reference into the future. There is no scheduled collection or rehydration. Ordinary builds and deployments use the maintained snapshot and do not fetch fragrance data or consume provider API requests. Website hosting does not require an ongoing provider API subscription for technical operation.

Push this project to a GitHub repository and enable **Settings → Pages → Build and deployment → Source: GitHub Actions**. No Fragella key or other repository secrets are required to deploy the prepared snapshot. The relative asset base and hash routes support a repository subdirectory without changes to `vite.config.ts`. `release.yml` validates and publishes the existing snapshot on pushes to `main` or manual dispatch. The manual `refresh` option defaults to **off**. Explicitly enabling it runs the existing source collectors for at most 200 originals; it does not invoke the Fragella trial or a production Fragella adapter. Permit workflow catalog writes only if using that optional manual collection. Local collection is also explicit: `python -m pipeline.cli refresh --limit 200`.

The workflow tests and builds before deployment, retains the previous release, uploads operational reports, and checks the deployed entry point. During an explicit collection, source access failures retain known data. New or contradictory identities enter the review report rather than being guessed. Attempt history prevents unresolved profiles from starving later batches. Raw HTML caches and operational archives are excluded from site assets.

The earlier Fragella trial is a separate process with a persistent 20-request ceiling. The launch collector above has its own budget and reuses available research candidates for resolution. See [accord API evaluation](docs/accord-api-evaluation.md) for the provider assessment and initial trial results.

Source availability is outside this project's control. The implementation was exercised against live Fragrantica HTML and source-access failures. Shobi retrieval failed from the development environment; its adapter has fixture coverage, but successful full live Shobi collection remains to be verified. The refresh report records the precise coverage and failures for each run.

See [architecture and operations](docs/architecture.md) for evidence rules, review and recovery.

## Credits and license

Fork lineage: [smellyCat-deep/shobi_inspiration](https://github.com/smellyCat-deep/shobi_inspiration), the original application and Essence Boost Guide; [MarvvRed/Shobi_Inspiration](https://github.com/MarvvRed/Shobi_Inspiration), catalog certification, local assets and discovery enhancements. This project independently rebuilds the application and data tooling while preserving that attribution.

Licensed under **GPL-3.0-only**. See [LICENSE](LICENSE). Product names and marks belong to their owners. Independent project, not affiliated with Shobi, Fragrantica or the original perfume brands.
