# Launch hydration review

Snapshot: 2,235 / 2,253 perfumes have sourced accords (99.2%). All 2,253 remain searchable. This pass added 504 accord profiles: 502 accepted public-page extracts and two individually reviewed source corrections/supplements. No additional Fragella requests were used; last confirmed balance remains 2,009.

## Remaining 18 accord gaps

These are a review queue, not accepted substitutions. Exact identities and editions must be established before accord inputs can be published.

| Perfume | House | Blocker / next action |
| --- | --- | --- |
| Blonde Maracuja Mood London | Mood London | Targeted Fragella query or alternative publisher; retain unavailable state until an exact identity and explicit accords are sourced. |
| Vanilla Skin | Phlur | Compare official Shobi identity and edition with source title: Vanilla Skin Fragrance Mist Phlur for women and men |
| James Bond 007 | James Bond 007 | Targeted Fragella query or alternative publisher; retain unavailable state until an exact identity and explicit accords are sourced. |
| No. 1 for Men | Clive Christian | Compare official Shobi identity and edition with source title: No. 1 Clive Christian for men |
| Just Cavalli for Her | Roberto Cavalli | Compare official Shobi identity and edition with source title: Just Cavalli Roberto Cavalli for women |
| G by G | Gucci | Compare official Shobi identity and edition with source title: Gucci by Gucci Eau de Parfum Gucci for women |
| REHAN - HAMIDI OUD | Hamidi Oud Perfumes | Readable source does not supply explicit accords in the retrieved section; inspect a second primary publisher or request a provider correction. |
| SULTAN - ARABIAN OUD | Arabian Oud | Compare official Shobi identity and edition with source title: Sultan Blend Arabian Oud for men |
| MAGNOLIA & MURE - L' OCCITANE | L'Occitane | Compare official Shobi identity and edition with source title: Magnolia & Mure L'Occitane en Provence for women |
| CITRUS VERBENA - L' OCCITANE | L'Occitane | Incomplete source extract; verify a complete original page or another publisher before importing. |
| Socal | Hollister | Readable source does not supply explicit accords in the retrieved section; inspect a second primary publisher or request a provider correction. |
| SALVADOR DALI fragrances | Salvador Dali | Compare official Shobi identity and edition with source title: Dali Parfum de Toilette Salvador Dali for women |
| (RED CUP) | Dolce & Gabbana | Compare official Shobi identity and edition with source title: Dolce&Gabbana Dolce&Gabbana for women |
| No 5 | Chanel | Compare official Shobi identity and edition with source title: Chanel N°5 (Vintage) Chanel for women |
| BURBERRY TOUCH | Burberry | Compare official Shobi identity and edition with source title: Touch for Women Burberry for women |
| Blu Mediterraneo - Fico di Amalfi | Acqua di Parma | Readable source does not supply explicit accords in the retrieved section; inspect a second primary publisher or request a provider correction. |
| Royal Blue | Romane | Inherited original identity is uncertified; reconcile official Shobi inspiration, house and edition first. |
| L Envol de Cartier | Cartier | Compare official Shobi identity and edition with source title: L'Envol de Cartier Eau de Parfum Cartier for men |

## Identity correction

Shobi 1172-ISS explicitly identifies Issey Miyake. Its inherited Fragrantica ID 79 is a Kenzo perfume; the correct original is ID 721. The incorrect bottle and Social Card notes have been withdrawn, not replaced with pyramid notes. The pre-import catalog and original receipts remain private. The exact correction and withdrawn note sequence are recorded in `contracts/reviewed-source-corrections.v1.json`. Historical inherited green/yellow metadata is retained for baseline accounting and does not recertify the withdrawn fields.

X Neroli limited edition is independently identified by the official Shobi listing and Parfumo’s matching house/name/2020 limited-edition entry. Its explicit accords and profile metrics retain Parfumo provenance and original 0–10 scales; no Fragrantica ID or Social Card notes are invented.

## What 100% can mean

Catalog presence is already 100%. Accord coverage can only reach 100% if a credible exact-edition source supplies explicit accords for every entry. Full optional-field coverage and universal Boost recommendations cannot be guaranteed: some publishers omit fields, and some valid accord sets contain no supported guide trigger. Notes, names and gender cannot substitute for accord evidence.

For the last entries: perform targeted cached API queries after identity reconciliation; consult exact original publisher/manufacturer pages; record an individually reviewed source binding; retain an honest unavailable state if no source supplies the field. A provider data-correction request can be prepared for the truly absent records, but has not been sent.

## Publication

Recovered fields use strict source-ID and title checks, plus individually pinned heading exceptions for spelling, title order and documented house labels. Unresolved editions stay held. Extraction reads neither user reviews nor search snippets as accord evidence. Existing populated fields are preserved, except the explicitly reviewed wrong-source withdrawal. Repeat imports and builds are deterministic. Collection remains manual; the site makes no API calls.

Run `.venv/bin/python -m pipeline.web_recovery` to review saved receipts, adding `--publish` only when publishing reviewed local evidence. Raw receipts and operational reports are ignored private files, never public artifacts. The maintained catalog contains the published source-backed values, so ordinary builds do not depend on these receipts.
