"""Import certified source material without modifying either reference tree."""
import shutil
from pathlib import Path
from .model import DATA, PUBLIC, ROOT, evidence, read, write


def js_map(path):
    text = path.read_text(encoding="utf-8")
    import json
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def bootstrap(reference=None):
    ref = Path(reference) if reference else ROOT / "_reference/MarvvRed/Shobi_Inspiration"
    catalog = ref / "database/catalog"
    full = read(catalog / "database_final_perfume_only.json")
    if len(full) != 2253 or sum(p["validationStatus"] == "green" for p in full) != 2247:
        raise ValueError("Reference differs from agreed certified baseline")
    certificate = read(catalog / "final-perfume-catalog-certification.json")
    aliases = {r["keptCode"]: r["removedCodes"] for r in certificate["confirmedSameOriginalListingsCollapsed"]}
    ranks = read(catalog / "shobi-bestseller-ranks.json")["ranks"]
    recent = {r["code"]: r["addedDate"] for r in read(catalog / "recent-additions.json")["entries"]}
    images = js_map(ref / "database/assets/perfumes/map.js")
    icons = js_map(ref / "database/assets/note-icons/map.js")
    asset_files = set()
    def asset(path):
        if not path:
            return None
        src = ref / path
        if not src.is_file():
            return None
        target = "assets/" + "/".join(Path(path).parts[-2:])
        asset_files.add((src, PUBLIC / target))
        return target
    profiles = []
    for row in full:
        code = row["code"]
        fid = str(row.get("fragranticaId") or "") or None
        image = asset(images.get(code))
        notes = row.get("fragranticaSocialCardNotes") or []
        source = row.get("fragranticaUrl") or None
        checks = row.get("validationChecks", {})
        # Legacy accord fields have no independent source evidence: never certify them.
        missing = evidence(None, "missing", note="Awaiting project-owned profile hydration")
        profiles.append({
            "schemaVersion": 1, "id": "shobi-" + str(row["prestashopProductId"]),
            "name": row["inspiredBy"], "brand": row["brand"], "edition": None,
            "fragranticaId": fid, "fragranticaUrl": source,
            "image": image, "imageEvidence": evidence(source, "inherited", note="Imported local bottle asset"),
            "gender": row.get("genderAffinity") or None,
            "seasons": list(dict.fromkeys("autumn" if s == "fall" else s for s in row.get("seasons", []))),
            "mainNotes": [{"name": n, "icon": asset(icons.get(n.lower()))} for n in notes],
            "accords": [], "pyramid": {"top": [], "heart": [], "base": []},
            "description": None, "rating": None, "longevity": None, "sillage": None,
            "evidence": {
                "identity": evidence(source or row["shobiUrl"], "inherited" if checks.get("identity") else "missing"),
                "mainNotes": evidence(source, "inherited" if checks.get("notes") else "missing", note="Exact ordered Social Card evidence imported from MarvvRed"),
                "gender": evidence(source, "inherited" if checks.get("gender") else "missing"),
                "seasons": evidence(source, "inherited" if checks.get("season") else "missing"),
                **{k: dict(missing) for k in ["accords", "pyramid", "description", "rating", "longevity", "sillage"]},
            },
            "validationStatus": row["validationStatus"], "validationIssues": row.get("validationIssues", []),
            "validationChecks": checks,
            "listings": [{"id": str(row["prestashopProductId"]), "code": code,
                "aliases": aliases.get(code, []), "url": row["shobiUrl"], "status": "active",
                "originalId": "shobi-" + str(row["prestashopProductId"]),
                "addedDate": recent.get(code), "bestSellerRank": ranks.get(code)}]
        })
    for src, dest in asset_files:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    write(DATA / "catalog/profiles.json", profiles)
    write(DATA / "catalog/baseline.json", {"count": 2253, "green": 2247, "yellow": 6,
        "provenance": "MarvvRed/Shobi_Inspiration supplied snapshot", "assetCount": len(asset_files)})
    for filename in ["final-perfume-catalog-certification.json", "catalog-scope-exclusions.json"]:
        shutil.copyfile(catalog / filename, DATA / "catalog" / filename)
    shutil.copyfile(ROOT / "_reference/smellyCat-deep/shobi_inspiration/LICENSE", ROOT / "LICENSE")
    print("Imported", len(profiles), "perfumes and", len(asset_files), "referenced assets")
