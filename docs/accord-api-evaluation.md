# Accord API evaluation

Evaluated October 23, 2026 (America/New_York). This is research, not a production provider switch. No account was created, no subscription purchased, and no benchmark result was imported into the public catalog.

**Subsequent launch work:** the user supplied a key and upgraded to Basic. The completed launch collection now publishes explicitly labeled provider assessments for corroborated identities. See [the launch snapshot report](launch-snapshot.md) for final coverage, request usage and remaining review items. The trial findings below are retained as historical research; the statements about no paid subscription/import describe that initial evaluation stage.

## Recommendation

The **Fragella free-trial benchmark is complete**: 20 successful requests returned 194 candidate records. The trial exposes useful accord data but also identity, concentration and duplicate-record problems. It supports a further controlled evaluation, not automatic production adoption. Confirm permission for our static JSON distribution and clarify field-level predicted-versus-observed provenance before adopting it.

**10ML is a viable secondary source with a curated ID crosswalk.** Its documented API is operational and free, but direct fuzzy lookup is unsafe for automatic hydration. The search endpoint exposes separate concentrations and is the better way to discover candidates.

**FragDB is the strongest documented alternative for batch collection and persistent caching**, with a higher minimum spend. This is an architectural fit assessment, not a measured accuracy result. Its provider-supplied terms still need clarification for public JSON files and data committed to an open-source repository.

## Live 10ML pilot

The repeatable script is `tools/evaluate_accord_api.py`. It uses 16 deliberately chosen catalog perfumes, two records without a Fragrantica ID, and 22 seeded-random records. The sample deliberately includes abbreviated names, new releases and concentration variants; it is not statistically representative of the entire catalog.

| Method                        | Observation                                                                                                                                        |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Initial direct name lookup    | 20 of 40 requests returned a perfume with accords; this includes wrong perfume/edition suggestions. Seventeen returned 404 and three returned 400. |
| Search-first, same 40 records | 25 returned at least one candidate; only 11 had one name/house match with accords after normalizing EDP/EDT/Extrait wording.                       |
| Chanel queries                | Three returned an explicit out-of-scope error. A follow-up using the full “Bleu de Chanel” name and the search endpoint also returned that error.  |
| Production acceptance         | Zero: candidate matches were not approved or imported.                                                                                             |

Concrete direct-lookup failures recorded in the raw captures:

- `Philosykos Eau de Parfum` returned `Philosykos EDT`, even with the provider's `exact` flag set. Search correctly exposed both EDT and EDP IDs.
- `Baccarat Rouge 540 Extrait de Parfum` returned the EDP. Search exposed the Extrait as a separate ID.
- Kylie Cosmetics `Vanilla Dew` returned Estée Lauder `Youth-Dew` despite the requested house.
- Amouage `Sunshine Man` returned `Sunshine Woman`.

Name equality does not establish an edition when our input name omits concentration or year. Therefore the 11 normalized matches are candidates for review, not 11 verified mappings. Approved spelling/brand aliases could improve recall; they must not erase edition or gender differences.

Requests used the documented REST API, a one-second delay, and a private response cache. Specifications, terms, connectivity results and both pilot reports are retained under ignored `data/raw/accord-api-evaluation/`. To reproduce the search pass with cached successful responses:

```sh
.venv/bin/python tools/evaluate_accord_api.py --search
```

`--refresh` re-requests responses. The script stops on rate limiting and never updates production data.

## Provider comparison

### 10ML

No account or key is required. Its editorial profiles contain explicit accord lists and provider IDs. Its service terms request attribution and allow fair-use limits, but do not explicitly address bulk storage and public redistribution. The MIT license on its client repository should not be assumed to license the hosted dataset. [Provider repository](https://github.com/10ml-com/perfume-finder-mcp), [API specification](https://mcp.10ml.com/openapi.json), [service terms](https://mcp.10ml.com/terms).

### Fragella

The provider advertises 100,000+ fragrances. Published plans include 20 free requests per month and a $12/month Basic tier with 5,000 requests. Its documentation describes missing notes/accords being predicted by machine learning, with a general confidence field; that is distinct from an observed source value. Its terms restrict large-scale caching unless the plan permits it. The authenticated 20-request trial is described below. [Pricing and methodology](https://api.fragella.com/), [documentation](https://api.fragella.com/docs.html), [terms](https://api.fragella.com/terms-of-use.html).

## Authenticated Fragella trial

Run `.venv/bin/python -m pipeline.fragella_trial --dry-run` to preview the 20-record stress sample without making requests. Omit `--dry-run` to execute it. The key is read from `FRAGELLA_API_KEY` in the environment or ignored `.env.local`; `.env.example` documents the setting. Never add a `VITE_` prefix. No key is sent to the frontend, printed, or included in reports.

Results and a persistent request ledger are private under ignored `data/raw/fragella-trial/`. A local process lock prevents overlapping runs. The entire trial, across reruns, is capped at 20 attempted fragrance requests, including failures and interruptions. Successful responses are reused; failed/interrupted requests are not silently retried. Do not delete the ledger to bypass the cap. `--limit` allows a smaller sample, not a fresh quota.

The completed run used all 20 attempts successfully, returning 194 candidates, all with nonempty accord lists. **That does not mean 20 matched perfumes.** Seven searches returned a normalized name-and-brand candidate; that deliberately strict check does not approve identities and can miss legitimate naming aliases. One of those seven, `Bleu-De-Chanel`, declares year 2010 and `OilType: Eau de Cologne` despite its high confidence. A separate 2010 record has no concentration. The responses also label `bleu-de-chanel-parfum-chanel-for-men` as `Eau de Parfum`. A provider confidence label is not proof of edition correctness.

Manual screening found plausible identity candidates in 15 searches, including cases requiring explicit brand/name aliases. This is candidate discovery, not 75% verified coverage and not a representative estimate for the catalog. No plausible identity appeared in the returned first page for `Avent`, `Vanilla Dew`, `Reb'l Fleur`, `X NEROLI LIMITED EDITION - CLIVE CHRISTIAN`, or `Blonde Maracuja Mood London`. That can reflect query wording, ranking, or missing coverage; it does not prove absence from the provider's database. `Avent` is an inherited abbreviated name and would benefit from an evidence-backed canonical-name crosswalk before a larger pass. Search is limited to ten results per page; this trial did not spend requests on second pages.

Other examples demonstrate why ranking cannot establish identity: `Sauvage` put four unrelated/different records before the 2015 Dior EDT; `Lira` ranked a 2025 Vexo Paris perfume ahead of Xerjoff. Philosykos results included EDT, limited-edition EDP and the 2012 EDP. All 194 returned candidates remain unapproved; production profiles and inherited Main Notes were not changed. Candidate accord provenance is explicitly `unspecified-may-be-predicted`. The report preserves provider IDs, names, years, concentrations, confidence, accord lists and original strength labels for review.

Seven focused tests cover response shapes, identity/edition conflicts, credential handling, private caching, persistent budgets, failed-request behavior and dry runs. Together with the existing pipeline tests, 22 tests passed.

## One-time hydration and the Basic request budget

The product decision is a **fixed snapshot for launch and future reference**, without scheduled rehydration or a freshness requirement. The static application runs from that published snapshot without visitor-time API calls. Ordinary deployment also makes no provider requests. The pipeline remains available for an explicit future collection if requested; it is not an ongoing service dependency. That technical capability does not establish permission to retain and redistribute provider data after a subscription ends.

For 2,253 originals:

| Request strategy | Requests | Remainder from 5,000 |
| --- | ---: | ---: |
| One search per original, using the returned full profile | 2,253 | 2,747 |
| One search plus one separate detail request per original | 4,506 | 494 |

Search responses already include accords and profile information, so a separate detail request is generally redundant. The more efficient approach is one search per original, manual review of ambiguous matches, and bounded fallback queries for the remaining records. The request budget is plausible for an initial pass; it cannot guarantee exact matches or complete hydration. Prior account usage may reduce the actual available budget. Check the dashboard before a paid run.

The initial procurement assessment identified storage/publication questions: Section 3.3 of the provider's terms restricts storing large portions to avoid fresh API access unless the plan explicitly permits it, and separately restricts standalone redistribution. Basic's public pricing does not resolve those permissions. The user's chosen use is a fixed launch/reference snapshot, with no freshness requirement or visitor-time API requests. That intent is recorded here without asserting that it circumvents access to fresh data or that an API subscription itself grants an open-data redistribution license. The user subsequently supplied Basic access and authorized the snapshot collection documented above.

### FragDB

The basic API level includes accord names and strengths at $0.005 per record. Retrieving 2,253 records would cost approximately $11.27 in record usage **if all were matched**, but the published minimum top-up is $100, with a $100 minimum spend per 180 days and cryptocurrency payments. Batches support up to 100 IDs and the provider permits indefinite caching, while restricting redistribution as a dataset/feed. Full-catalog testing needs a paid key; its free test key serves only five samples. No authenticated accuracy benchmark was performed. [API and pricing](https://fragdb.net/api), [usage terms](https://fragdb.net/legal).

## Other candidates checked

- **Scento:** its public API responded successfully, but the tested portrait exposes notes, its own family taxonomy and character words rather than the explicit accord field needed by our existing Boost rules. It could help other profile fields. [Developer documentation](https://www.scento.com/developers).
- **ScentVerdict:** its current documentation says it removed the traditional accord charts in favor of its ScentPrism model. Adopting that would require a different classification method. [ScentPrism documentation](https://scentverdict.com/scentprism).
- **The Preservation Network's fragrance API:** the documented search URL returned HTML for an unrelated astronomy service in the live probe, so its published interface was not usable for this evaluation. [Published documentation](https://fragrances.thepreservationnetwork.org/docs.html).

## Acceptance criteria for the next trial

Use Fragella's 20 free requests for a deliberately difficult subset: exact concentration pairs, flankers, obscure brands, recent additions and unresolved names. Compare returned identity, year, concentration and accord vocabulary against existing evidence. Retain provider IDs only for approved matches. Keep predictions/editorial assessments separately labeled from inherited Social Card certification.

Any selected provider should hydrate accords behind our existing pipeline, with credentials confined to local/CI settings. Keep Shobi identity and inherited Main Notes intact. Check that its agreement supports a website whose data is delivered as downloadable JSON; public open-source data redistribution and ordinary application display are separate questions.
