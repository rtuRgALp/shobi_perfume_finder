# Architecture and operations

## Boundaries

The browser reads a release manifest and a compact search index, then fetches individual profiles only when opened. It never requests source HTML, OCR archives or operational audit reports. React handles presentation; pure functions handle search, filters and Boost classification. Shared design tokens control light/dark appearances. Native dialogs provide mobile focus trapping and Escape behavior.

The pipeline is independent of the frontend. `bootstrap` imports the agreed certified snapshot without executing inherited repair tools. `refresh` uses project-owned adapters. `build` validates and publishes versioned artifacts. Application deployment consumes a completed artifact rather than running data repair inside the browser.

## Identity and evidence

An original perfume owns independent enrichment fields and one or more Shobi listings. Stable original IDs currently use the first imported Shobi product ID (`shobi-<id>`); they must remain stable if a code or URL changes. Known duplicate codes are retained as aliases. New cross-listings may be joined only with exact same-original evidence.

Fragrantica hydration checks the canonical page ID and normalized exact name/brand/edition before accepting fields. Normalization removes punctuation and accents, not edition words. Brand reorganizations or renamed perfumes therefore enter review rather than silently remapping. The existing certified identity is retained while that review is pending.

Evidence states are `verified` (independently observed source hydration), `provider` (external assessments that may include model estimates), `inherited` (supplied certified evidence), `missing` and `conflicting`. Fragella's general confidence label does not establish field-level observed provenance, so its values remain `provider` even when confidence is high. Provenance, confidence states and rule versions are retained in data contracts and project documentation; the shopping interface omits audit panels, provider caveats and per-field evidence notices. It presents the perfume information, Boost amounts and concise unavailable states. Fragella assessments may include estimates. Boost rule `original-v1` is inherited project guidance, not a measured performance guarantee. Catalog green/yellow status remains the inherited strict identity/card certification; independent profile enrichment never promotes that status. In particular, page-derived or provider note pyramids cannot certify ordered Social Card Main Notes.

New listings without approved mappings are quarantined in `data/reports/refresh.json`. To resolve a review, inspect the exact official product, original identity/edition and source ID; update the maintained profile and evidence in `data/catalog/profiles.json` through a reviewed change. A genuinely new original needs a full schema-valid profile and a stable original/listing association. Set its `addedDate` to the first observed publication date, not a scrape retry date. Do not copy an unrelated profile's notes, sources, validation checks or status. Run data tests and `build` before publication.

The six inherited yellow records remain searchable. New records require demonstrated wearable-perfume scope and exact identity evidence before publication; optional enrichment can be missing. Preserve the imported exclusions and explicit same-original duplicate proofs. The reference universal recovery database remains untouched.

## Source adapters and failure behavior

Fragrantica's legacy and current accord markup and note-pyramid markup are parsed separately. Only explicitly present values are hydrated. Descriptions use the factual opening sentence rather than reproducing the entire article. Numeric ratings keep the source scale and vote count; missing or client-only performance data stays null. Never derive longevity/sillage from review prose.

HTTP retrieval is bounded to known hosts, cached for seven days, delayed between requests, retried at most twice, and stopped per host after three consecutive failures. Forbidden or rate-limited responses do not trigger bypass attempts. Missing page sections retain existing data. Full source pages remain private cache artifacts.

The explicit Fragella launch collector uses its own private response cache and append-only reservation ledger. It reserves each attempt durably before network access and caps the entire collection at 4,980 new attempts. Bounded workers share a two-starts-per-second limiter. Failed/interrupted requests are not automatically retried, and authentication/quota errors stop further scheduling. Restarting collection reuses successful cached queries; the ledger is never reset by deployment. Search responses already contain full profile data, so redundant per-record detail requests are avoided.

Fragella resolution uses exact name variants from the inherited identity and established source URL, explicit brand aliases, concentration/gender conflict checks, and inherited-note corroboration. Search order and fuzzy similarity never approve an identity. Contradictory duplicate records and one provider ID shared by distinct original source IDs enter review. Publication fills empty fields only and reports provider disagreements with retained published values. Numeric ratings retain their Bayesian source scale; longevity and sillage keep descriptive labels without a fabricated numeric conversion. Known identity, Main Notes, certification and assets are untouched. Stable approved provider mappings live in `data/catalog/fragella-mappings.json`; operational evidence stays private.

Shobi listing collection follows same-path pagination, rejects empty/malformed pages and bounds page traversal. The existing listing must agree on product ID and code before its official URL can change. Absence from a collection never automatically deletes a perfume. Best-seller ranks change only after the full rank collection succeeds.

## Publication and recovery

Profiles validate against the JSON Schema before any public pointer changes. Canonical serialization produces a content-addressed release ID from profiles, the public projection and Boost rules. The builder writes an isolated staging directory, promotes it, then atomically replaces `current.json`. The release date derives from input evidence, so clean builds with identical inputs produce identical public data. Invalid inputs leave the active pointer untouched.

`previous.json` retains the prior valid manifest and its profiles. `python -m pipeline.cli rollback` swaps the two pointers. Rebuild and redeploy after rollback; do not immediately regenerate from the newer catalog snapshot unless intentionally restoring it. HTTP cache and release artifacts are separate from the maintained source catalog.

The deployment workflow publishes a fixed catalog snapshot. There is no scheduled source collection or rehydration. Pushes and ordinary manual deployments validate and build the existing data without provider requests; deploying application changes does not refresh the catalog. The explicit manual `refresh` option defaults to off and, when enabled, runs the original source adapters with a 200-profile ceiling. Fragella's trial and launch collector remain separate and are never invoked by deployment. Provider hydration prepares the launch snapshot and is not an ongoing runtime dependency.

Maintained attempt history supports resuming explicit collection batches without unresolved profiles starving later records. `data/catalog/first-seen.json` records successfully observed listing dates for reviewed additions. Review items and source failures are downloadable workflow artifacts; a successful deployment does not imply every upstream field is available. Workflow failures prevent the deployment job. Full-profile coverage remains a goal, not a publication gate. Current and previous snapshots remain available for reproducibility and rollback.

## Verification

Unit checks cover exact parser identity, structural changes, absent sections, aliases, deterministic releases, rollback and preservation under source failure. Frontend tests validate every public profile and cover filter composition, URL serialization and Boost rules. Browser tests exercise desktop/mobile discovery, favorites, deep links, filtering, broken images and retry states.

Automated accessibility checks and visual inspection complement keyboard tests. These establish a baseline; a complete WCAG conformance claim requires a broader human audit.

The fixed launch snapshot has no recently-added facet, active chip or card badge. Historical first-seen dates remain pipeline metadata; legacy `recent` URL parameters are ignored.

## Field-level recovery

`pipeline.web_recovery` checks accords, pyramid, description, rating, longevity and sillage independently. Published accords never suppress recovery of other missing fields. Receipts are reconciled newest first across all available observations, so a truncated latest extract cannot hide useful older evidence. A source without an accord section can still supply a pyramid or rating after exact ID/heading checks.

Existing populated values remain unchanged. Partial pyramids can be completed only by a complete source agreeing with every retained layer; conflicting candidate layers remain in review. Notes without explicit top/heart/base grouping are not assigned layers. Extraction stops before designer recommendations and user reviews. Main Notes are never synthesized from a pyramid. Per-field and per-layer gaps are recorded in private recovery reports. Release coverage distinguishes any available pyramid from a complete three-layer pyramid.

This recovery is an explicit snapshot operation, not a scheduled refresh or runtime API dependency. Cached approved API records are reused before considering further requests; identity ambiguity is not waived to fill a missing field.
