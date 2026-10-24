"""Incremental hydration, safe source reconciliation and review queues."""
import copy
import datetime as dt
from urllib.parse import parse_qs, urlparse
from .model import DATA, PUBLIC, evidence, read, validate_profiles, write
from .release import build
from .sources import Client, SourceError, normalized, parse_fragrantica, parse_shobi


def hydrate(profile, fields, metadata):
    result = copy.deepcopy(profile)
    for key in ["accords", "pyramid", "description", "rating", "longevity", "sillage"]:
        if key in fields and fields[key] not in (None, [], ""):
            result[key] = fields[key]
            result["evidence"][key] = evidence(metadata["source"], "verified", metadata["retrievedAt"], "Exact mapped original; independently hydrated field")
    validate_profiles([result])
    return result


def collect_listing_pages(client, url, max_pages=150):
    queue, visited, pages = [url], set(), []
    while queue:
        page = queue.pop(0)
        if page in visited:
            continue
        if len(visited) >= max_pages:
            raise SourceError("Pagination exceeded collection limit; incomplete snapshot rejected")
        html, _ = client.get(page)
        rows, next_pages = parse_shobi(html, url)
        if not visited and len(rows) >= 24 and not next_pages:
            raise SourceError('Full first page has no pagination evidence; incomplete collection rejected')
        visited.add(page)
        page_number = int(parse_qs(urlparse(page).query).get('page', ['1'])[0])
        pages.append((page_number, rows))
        queue.extend(p for p in next_pages if p not in visited and p not in queue)
    # Pagination often links directly to the final page; discovery order is not
    # rank order. Reassemble numerically before assigning best-seller positions.
    products = {}
    for _, rows in sorted(pages, key=lambda item: item[0]):
        for row in rows:
            products.setdefault(row['id'], row)
    return list(products.values())


def reconcile_listings(profiles, live, review):
    by_id = {r["id"]: (p, r) for p in profiles for r in p["listings"]}
    for row in live:
        existing = by_id.get(row["id"])
        if not existing:
            review.append({"kind": "unresolved-listing", "listing": row, "reason": "Needs exact original mapping and wearable scope review"})
            continue
        profile, listing = existing
        known_codes = [listing["code"]] + listing["aliases"]
        if row["code"] not in known_codes:
            review.append({"kind": "listing-conflict", "id": profile["id"], "listing": row})
            continue
        if row.get('declaredOriginal'):
            declared = normalized(row['declaredOriginal'])
            identities = [profile['name'], profile['name'] + ' ' + profile['brand'], profile['brand'] + ' ' + profile['name']]
            if declared not in {normalized(v) for v in identities}:
                review.append({'kind': 'listing-identity-conflict', 'id': profile['id'], 'listing': row})
                continue
        # Product ID and code agree. Preserve mapped original and update only official URL.
        listing["url"] = row["url"]
        listing["status"] = "active"
    # Absence from one collection never proves a known perfume was discontinued.


def refresh(limit=None, client=None, data=DATA, public=PUBLIC):
    profiles = read(data / "catalog/profiles.json")
    client = client or Client(data / "raw/http")
    report = {"startedAt": dt.datetime.now(dt.timezone.utc).isoformat(), "hydrated": 0, "review": [], "failures": []}
    observations_path = data / 'catalog/first-seen.json'
    observations = read(observations_path) if observations_path.exists() else {}
    state_path = data / 'catalog/hydration-state.json'
    state = read(state_path) if state_path.exists() else {}
    for kind, url in [("catalog", "https://leparfum.com.gr/en/perfumes"), ("best-sellers", "https://leparfum.com.gr/en/best-sales")]:
        try:
            rows = collect_listing_pages(client, url)
            write(data / "raw" / (kind + ".json"), rows)
            if kind == "catalog":
                for row in rows:
                    observations.setdefault(row['id'], report['startedAt'][:10])
                reconcile_listings(profiles, rows, report["review"])
            else:
                ranks = {r["id"]: rank for rank, r in enumerate(rows, 1)}
                # Missing rank is unavailable, not a guessed popularity signal.
                for p in profiles:
                    for listing in p["listings"]:
                        listing["bestSellerRank"] = ranks.get(listing["id"])
        except SourceError as error:
            report["failures"].append({"source": kind, "error": str(error)})
    # Track attempts as well as successes. Otherwise a full batch of unresolved
    # identities would be retried forever and starve every later perfume.
    order = sorted(range(len(profiles)), key=lambda i: (
        state.get(profiles[i]['id'], {}).get('lastAttempt') or profiles[i]['evidence']['accords']['retrievedAt'] or '',
        profiles[i]['id']))
    attempted = 0
    for i in order:
        p = profiles[i]
        if not p["fragranticaId"] or not p["fragranticaUrl"]:
            report["review"].append({"kind": "missing-original-source", "id": p["id"]})
            continue
        if limit is not None and attempted >= limit:
            break
        if client.failures.get("www.fragrantica.com", 0) >= 3:
            report["failures"].append({"source": "fragrantica", "error": "Circuit open; remaining profiles retained without requests"})
            break
        attempted += 1
        state[p['id']] = {'lastAttempt': report['startedAt'], 'error': None}
        try:
            html, meta = client.get(p["fragranticaUrl"])
            fields = parse_fragrantica(html, p, meta["source"])
            profiles[i] = hydrate(p, fields, meta)
            report["hydrated"] += 1
        except (SourceError, ValueError) as error:
            state[p['id']]['error'] = str(error)
            report["review"].append({"kind": "profile-review", "id": p["id"], "error": str(error)})
    report["attempted"] = attempted
    validate_profiles(profiles)
    # Build first: invalid refreshes cannot replace current release or persisted catalog.
    manifest = build(profiles, public=public, data=data)
    write(data / "catalog/profiles.json", profiles)
    write(state_path, state)
    if observations:
        write(observations_path, observations)
    report["releaseId"] = manifest["releaseId"]
    write(data / "reports/refresh.json", report)
    print("Hydrated", report["hydrated"], "profiles;", len(report["review"]), "review items;", len(report["failures"]), "source failures")
    return report
