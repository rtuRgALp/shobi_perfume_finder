# Launch snapshot

Prepared October 24, 2026 (America/New_York). Release **823a65d4a5f9c6af** is a fixed reference snapshot. Collection and rehydration are not scheduled; ordinary builds, deployments and browsing make no provider API calls.

## Published coverage

| Information | Perfumes |
| --- | ---: |
| Searchable catalog | 2,253 |
| Certified ordered Main Notes | 2,246 |
| Accords | 2,235 |
| Essence Boost guidance | 2,220 |
| Available note pyramid | 2,115 |
| Rating | 2,112 |
| Longevity assessment | 1,714 |
| Sillage assessment | 1,714 |
| Available description | 540 |

The inherited certification counts remain **2,247 green and six yellow**. All 25 duplicate code aliases and listing associations are preserved. One inherited Issey Miyake record pointed to Kenzo: its source mapping was corrected and the mismatched bottle, season and ordered Main Notes were withdrawn. All other inherited ordered Main Notes remain unchanged; the reviewed exception preserves its previous note sequence in the correction record. Reviewed corrections expand the display names “Avent” to “Aventus” and “Rouge 540” to “Baccarat Rouge 540”; their established original source IDs are unchanged and the old names remain searchable. Established full names and accepted provider title variants are searchable without changing favorite codes.

Of the accord-bearing profiles, 579 retain independently observed source evidence and 1,656 use explicitly labeled Fragella assessments. Provider assessments may include model estimates; high provider confidence is not treated as independently verified provenance. That distinction remains in the underlying evidence and project notes; the shopping interface omits provenance notices and audit panels. Numeric ratings retain their Bayesian source scale and do not invent vote counts. Descriptive performance labels remain descriptive. Provider note pyramids never replace Main Notes. Fifteen accord-bearing profiles have no recognized Boost trigger and therefore show the unavailable state.

## Collection and identity review

Every catalog perfume was considered in an initial pass, followed by focused fallback searches for 758 unresolved profiles. There were **2,986 new attempted requests**, with successful queries cached for reuse. The provider-confirmed total account usage is **2,991 successful requests**, including the earlier 20-request trial, leaving **2,009 of 5,000** available. Failed requests and cache reuse explain why attempts and billed usage differ. No further collection is running.

The final resolver accepts **1,711 current provider mappings**. Its rules require exact name variants, documented brand aliases, nonconflicting explicit concentrations, and independent note corroboration. Seventy-three audience-label discrepancies were individually reviewed; these exceptions cannot override source IDs, name, brand, concentration or note checks. Known contradictory provider records are excluded. Previous valid published values are retained when a candidate update becomes ambiguous, so coverage is not identical to the current mapping count.

**542 profiles remained in the provider-specific identity/data review after API collection.** The subsequent independent public-source recovery added 504 accord profiles without paid API calls. Only **18 catalog perfumes now lack sourced accords**; the provider review count is historical and is not the current enrichment gap. See [hydration review](hydration-review.md) for the remaining entries and next actions.

In the provider-specific review, some searches did not yield an exact identity; others exposed inconsistent note data, audience/edition differences or contradictory duplicate records. This does not prove those perfumes are absent from the provider's database. Their existing information remains published and searchable. No fuzzy ranking was promoted into an identity match to increase coverage.

Detailed candidates, raw responses, quota evidence and review reports remain private under ignored `data/raw/fragella-snapshot/` and `data/reports/`. Approved stable provider mappings are maintained in `data/catalog/fragella-mappings.json`. The current and preceding complete releases remain available for rollback; the pre-import maintained catalog is also backed up privately.

## Verification

- 48 pipeline tests and 11 frontend tests passed.
- 21 desktop/mobile browser checks passed; the desktop copy of the mobile-only filter test is intentionally skipped.
- Automated accessibility checks passed for browse, dark appearance, details and the mobile filter sheet.
- Production deep links and assets work beneath a GitHub Pages repository subdirectory.
- A 360px detail inspection showed no horizontal overflow or browser errors and made no API/audit-archive requests.
- The production build succeeds, repeated data builds are deterministic, and the API key is absent from public data and the bundle.

This is a locally prepared production artifact. Hosting still requires configuring the GitHub repository and Pages deployment.

Display punctuation repair: 91 source-attested perfume labels restore apostrophes missing in the inherited display names, including “King's Harem”. Corrections are pinned to stable original IDs and house names in `contracts/display-name-corrections.v1.json`; old labels remain searchable aliases. The release builder reapplies these reviewed corrections without changing listing codes, notes or favorites.

## Pyramid recovery follow-up

The field-level pass filled 366 additional complete pyramids, bringing complete three-layer coverage to **2,113 / 2,253 (93.8%)**. Two other profiles have partial, explicitly published layer information; 138 have no published pyramid in this snapshot. In total 412 profiles gained missing fields, including 305 descriptions and 87 ratings. Main Notes, names, codes, aliases, favorites identifiers, existing profile values and accords were preserved.

All 504 eligible missing-pyramid identities were revisited through exact original source pages. Among the remaining gaps, 116 readable original pages explicitly provide ungrouped “Fragrance Notes”, which were not turned into a pyramid. Other cases include incomplete extracts, partial layer listings and identity/edition holds. A source publishing one note list does not establish a layered composition. Known API candidates were rechecked; no additional approved fields were available from cache, and conflicting audience/edition candidates stayed held. This pass made no new paid API requests, leaving the last confirmed balance of 2,009 unchanged by our work.

Interlude 53 Man now contains its explicitly sourced top, heart and base layers. The maintained field evidence points to the exact original profile. Raw observations, pre-pass backup and per-field operational reports remain private.

## Shopping-link and punctuation follow-up

An additional 45 display corrections include Angels' Share, Angels' Share On The Rocks, and missed French elisions and English contractions. Previous display labels remain searchable aliases. All 2,253 shopping links now omit inherited product-option fragments, so the finder does not request a preset bottle size or essence amount. Import, refresh and release generation apply the same URL cleanup; the retailer may still add its own option state after navigation.
