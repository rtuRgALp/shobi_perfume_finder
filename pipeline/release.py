"""Build immutable releases, then atomically change the current pointer."""
import os
import shutil
from .model import DATA, PUBLIC, ROOT, digest, read, validate_profiles, write
from .display_names import restore_display_names
from .listing_urls import clean_listing_urls


def index_record(p):
    listings = p["listings"]
    return {k: p[k] for k in ["id", "name", "brand", "image", "gender", "seasons", "mainNotes", "validationStatus"]} | {
        "code": listings[0]["code"],
        "nameAliases": p.get('nameAliases', []),
        "aliases": [c for r in listings for c in [r["code"]] + r["aliases"] if c != listings[0]["code"]],
        "accords": p["accords"] if p["evidence"]["accords"]["status"] in {"verified", "provider"} else [],
        "addedDate": min((r["addedDate"] for r in listings if r["addedDate"]), default=None),
        "bestSellerRank": min((r["bestSellerRank"] for r in listings if r["bestSellerRank"]), default=None),
    }


def build(profiles=None, public=PUBLIC, data=DATA):
    profiles = profiles if profiles is not None else read(data / "catalog/profiles.json")
    profiles = sorted(clean_listing_urls(restore_display_names(profiles)), key=lambda p: p["id"])
    validate_profiles(profiles)
    rules = read(ROOT / 'contracts/boost-rules.v1.json')
    index = {"schemaVersion": 1, "perfumes": [index_record(p) for p in profiles]}
    release_id = digest({'schemaVersion': 1, 'profiles': profiles, 'boostRules': rules, 'index': index})
    releases = public / "data/releases"
    target = releases / release_id
    pointer = public / "data/current.json"
    old = read(pointer) if pointer.exists() else None
    if old and old["releaseId"] == release_id:
        print("Release unchanged:", release_id)
        return old
    staging = releases / (".staging-" + release_id)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        write(staging / "index.json", index)
        for p in profiles:
            write(staging / "profiles" / (p["id"] + ".json"), p)
        coverage = {k: sum(bool(p[k]) and p["evidence"][k]["status"] in {"verified", "provider"} for p in profiles)
                    for k in ["accords", "description", "rating", "longevity", "sillage"]}
        coverage["mainNotes"] = sum(bool(p["mainNotes"]) for p in profiles)
        coverage['pyramid'] = sum(any(p['pyramid'].values()) and p['evidence']['pyramid']['status'] in {'verified', 'provider'} for p in profiles)
        coverage['completePyramids'] = sum(all(p['pyramid'].values()) and p['evidence']['pyramid']['status'] in {'verified', 'provider'} for p in profiles)
        coverage['partialPyramids'] = coverage['pyramid'] - coverage['completePyramids']
        for level in ('top', 'heart', 'base'):
            coverage['pyramid' + level.capitalize()] = sum(bool(p['pyramid'][level]) and p['evidence']['pyramid']['status'] in {'verified', 'provider'} for p in profiles)
        triggers = set(rules['heavy'] + rules['light'])
        coverage['verifiedAccords'] = sum(p['evidence']['accords']['status'] == 'verified' and bool(p['accords']) for p in profiles)
        coverage['providerAccords'] = sum(p['evidence']['accords']['status'] == 'provider' and bool(p['accords']) for p in profiles)
        coverage['boostRecommendations'] = sum(p['evidence']['accords']['status'] in {'verified', 'provider'} and
            bool(p['evidence']['accords']['source']) and any(rules['vocabulary'].get(a.strip().lower()) in triggers for a in p['accords']) for p in profiles)
        # Derive the release date from input evidence, not the build clock. This
        # keeps clean builds byte-identical, including their manifest.
        evidence_dates = [e['retrievedAt'] for p in profiles for e in p['evidence'].values() if e['retrievedAt']]
        generated_at = max(evidence_dates, default='2026-10-19T00:00:00+00:00')
        manifest = {"schemaVersion": 1, "releaseId": release_id,
            "generatedAt": generated_at,
            "basePath": "data/releases/" + release_id + "/", "index": "index.json", "profilePath": "profiles/",
            "count": len(profiles), "coverage": coverage,
            "validation": {s: sum(p["validationStatus"] == s for p in profiles) for s in ["green", "yellow", "red"]}}
        write(staging / "manifest.json", manifest)
        if target.exists():
            shutil.rmtree(staging)
            manifest = read(target / "manifest.json")
        else:
            os.replace(staging, target)
        pointer.parent.mkdir(parents=True, exist_ok=True)
        if old:
            write(public / "data/previous.json", old)
        tmp = pointer.with_suffix(".tmp")
        write(tmp, manifest)
        os.replace(tmp, pointer)
        # Retain current and previous releases; do not accumulate full catalogs forever.
        keep = {release_id, old["releaseId"] if old else release_id}
        for child in releases.iterdir():
            if child.is_dir() and child.name not in keep:
                shutil.rmtree(child)
        write(data / "reports/coverage.json", manifest)
        print("Published release", release_id, "with", len(profiles), "perfumes")
        return manifest
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def rollback(public=PUBLIC):
    current = read(public / "data/current.json")
    previous = read(public / "data/previous.json")
    if not (public / previous["basePath"] / "manifest.json").is_file():
        raise ValueError("Previous release files are missing")
    tmp = public / "data/current.tmp"
    write(tmp, previous)
    os.replace(tmp, public / "data/current.json")
    write(public / "data/previous.json", current)
    print("Rolled back to", previous["releaseId"])
