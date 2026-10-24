"""Versioned public contracts and deterministic serialization."""
import hashlib
import json
from pathlib import Path

VERSION = 1
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = ROOT / "public"


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encode(value), encoding="utf-8")


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()[:16]


def evidence(source, status="verified", retrieved_at=None, note=None):
    return {"source": source, "status": status, "retrievedAt": retrieved_at, "note": note}


def validate_profiles(profiles):
    import jsonschema
    schema = read(ROOT / "contracts/profile.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    exclusions_path = DATA / 'catalog/catalog-scope-exclusions.json'
    excluded = {c.casefold() for c in read(exclusions_path)['codes']} if exclusions_path.exists() else set()
    seen, codes = set(), set()
    for profile in profiles:
        validator.validate(profile)
        if profile["id"] in seen:
            raise ValueError("Duplicate original identity: " + profile["id"])
        seen.add(profile["id"])
        for listing in profile["listings"]:
            if listing['originalId'] != profile['id']:
                raise ValueError('Listing points to a different original identity')
            for code in [listing["code"]] + listing["aliases"]:
                key = code.strip().casefold()
                if key in excluded:
                    raise ValueError('Excluded non-perfume listing cannot be published: ' + code)
                if key in codes:
                    raise ValueError("Duplicate listing code/alias: " + code)
                codes.add(key)
        if profile["validationStatus"] == "red":
            raise ValueError("Contradictory record cannot be published")
        if profile['validationStatus'] == 'green':
            required = ['shobiProduct', 'shobiIdentity', 'identity', 'fid', 'url', 'socialCard', 'image', 'notes', 'icons', 'gender', 'season']
            if not all(profile['validationChecks'].get(k) is True for k in required):
                raise ValueError('Green certification requires the full inherited validation chain')
        if not profile["listings"]:
            raise ValueError("Original has no searchable listing")
