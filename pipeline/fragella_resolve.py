"""Exact identity resolution and explicitly invoked snapshot import.

Search ranking is never identity evidence. Name/brand equality, nonconflicting
edition and gender, and independent inherited-note overlap are required. Fuzzy
and partial-name candidates remain private review items. API assessments retain
provider provenance rather than being relabeled as observed community facts.
"""
import argparse
import copy
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlparse

from .fragella_snapshot import OUTPUT, canonical_name
from .fragella_trial import candidates, normalize
from .model import DATA, ROOT, evidence, read, validate_profiles, write
from .release import build

ALIASES = read(ROOT / 'contracts/fragella-identity-aliases.v1.json')
EXCLUSIONS = read(ROOT / 'contracts/fragella-provider-exclusions.v1.json')['records']
NOTE_ALIASES = {normalize(alias): normalize(canonical)
                for canonical, aliases in ALIASES.get('identityNoteAliases', {}).items()
                for alias in [canonical, *aliases]}


def normalized_note(value):
    value = normalize(value)
    return NOTE_ALIASES.get(value, value)


def brand_names(brand):
    names = {brand, *ALIASES['brandAliases'].get(brand, [])}
    # Alias equivalence is symmetric and explicit, never fuzzy.
    for canonical, aliases in ALIASES['brandAliases'].items():
        if brand in aliases:
            names.update([canonical, *aliases])
    return {normalize(n) for n in names}


def expected_brands(profile):
    names = brand_names(profile['brand'])
    parts = urlparse(profile.get('fragranticaUrl') or '').path.split('/')
    if len(parts) == 4 and parts[1] == 'perfume':
        names.add(normalize(unquote(parts[2]).replace('-', ' ')))
    return names


def provider_brand(row):
    brand = row.get('Brand') or ''
    for supplied, correction in ALIASES.get('providerBrandCorrections', {}).items():
        if (normalize(brand) == normalize(supplied)
                and normalize(row.get('Name')).startswith(normalize(correction['requiredNamePrefix']) + ' ')):
            return correction['canonical']
    return brand


def display_names(brand):
    prefixes = brand_names(brand)
    for canonical, extras in ALIASES.get('displayNamePrefixes', {}).items():
        if normalize(canonical) in prefixes:
            prefixes.update(normalize(extra) for extra in extras)
    return prefixes


def identity_name(name, brand):
    # Established Fragrantica slugs omit ampersands. Normalize this cosmetic
    # connector consistently, retaining all ordered name/edition words.
    value = normalize(name)
    for suffix in (' for women and men', ' for men and women', ' for women', ' for men', ' unisex'):
        if value.endswith(suffix):
            value = value[:-len(suffix)]
            break
    prefixes = display_names(brand)
    for prefix in sorted(prefixes, key=len, reverse=True):
        if value.startswith(prefix + ' '):
            value = value[len(prefix) + 1:]
            break
    return ' '.join(word for word in value.split() if word != 'and')


def concentration(value):
    value = normalize(value).replace('eau de cologne', 'edc')
    for token in ('extrait', 'edp', 'edt', 'edc'):
        if re.search(r'\b' + token + r'\b', value):
            return token
    # "Le Parfum" can be a flanker name marketed as EDP. Only a standalone
    # concentration label establishes Parfum; names retain their edition words.
    if value == 'parfum':
        return 'parfum'
    return None


def note_names(row):
    notes = row.get('General Notes') or []
    result = {normalized_note(n) for n in notes if isinstance(n, str)} if isinstance(notes, list) else set()
    pyramid = row.get('Notes') or {}
    if isinstance(pyramid, dict):
        for level in ('Top', 'Middle', 'Base'):
            values = pyramid.get(level) or []
            if not isinstance(values, list):
                continue
            result.update(normalized_note(n.get('name')) if isinstance(n, dict) else normalized_note(n) for n in values if isinstance(n, (str, dict)))
    return result - {''}


def evaluate(profile, row):
    reasons = []
    if not profile.get('fragranticaId') or profile.get('validationChecks', {}).get('identity') is not True:
        reasons.append('uncertified-original-identity')
    expected = {identity_name(profile['name'], profile['brand']), identity_name(canonical_name(profile), profile['brand'])}
    actual = identity_name(row.get('Name'), provider_brand(row))
    if normalize(provider_brand(row)) not in expected_brands(profile):
        reasons.append('brand-mismatch')
    actual_names = {actual}
    # Some API records append the full house to the perfume title. Remove that
    # decoration only as an additional candidate; never rewrite a natural name
    # such as Bleu de Chanel or accept a partial perfume-name match.
    for brand in display_names(provider_brand(row)):
        brand = ' '.join(word for word in brand.split() if word != 'and')
        if actual.endswith(' ' + brand):
            actual_names.add(actual[:-len(brand) - 1])
    if not actual_names & expected:
        reasons.append('name-or-edition-mismatch')
    source_type = concentration(canonical_name(profile)) or concentration(profile['name'])
    row_type = concentration(row.get('OilType'))
    name_type = concentration(row.get('Name'))
    if source_type and row_type and source_type != row_type:
        reasons.append('concentration-conflict')
    if name_type and row_type and name_type != row_type:
        reasons.append('provider-concentration-conflict')
    expected_gender = {'masculine': 'men', 'feminine': 'women', 'unisex': 'unisex'}.get(profile['gender'])
    actual_gender = normalize(row.get('Gender'))
    if expected_gender and actual_gender and actual_gender != expected_gender:
        reasons.append('gender-conflict')
    original_notes = {normalized_note(n['name']) for n in profile['mainNotes']}
    overlap = original_notes & note_names(row)
    if len(overlap) < min(2, len(original_notes)) or not original_notes or len(overlap) / len(original_notes) < 0.4:
        reasons.append('insufficient-note-corroboration')
    if not row.get('_id'):
        reasons.append('missing-provider-id')
    return reasons, sorted(overlap)


def load_candidates(directory=OUTPUT):
    by_id = {}
    for path in sorted((Path(directory) / 'responses').glob('*.json')):
        response = read(path)
        for row in candidates(response['response']):
            pid = row.get('_id')
            if not isinstance(pid, str) or not pid:
                continue
            item = {'profile': row, 'retrievedAt': response['retrievedAt'], 'source': response['source']}
            if pid not in by_id or by_id[pid]['retrievedAt'] < item['retrievedAt']:
                by_id[pid] = item
    # Trial candidates are usable research evidence too; no paid refetch required.
    trial = ROOT / 'data/raw/fragella-trial'
    ledger = read(trial / 'requests.json')['attempts'] if (trial / 'requests.json').exists() else []
    for entry in ledger:
        path = trial / (entry['id'] + '.json')
        if path.exists():
            for row in candidates(read(path)):
                pid = row.get('_id')
                if pid and pid not in by_id:
                    by_id[pid] = {'profile': row, 'retrievedAt': entry['startedAt'], 'source': 'https://api.fragella.com/docs.html'}
    return by_id


def resolve(profiles, provider_rows, reviewed=None):
    review_path = ROOT / 'contracts/fragella-reviewed-mappings.v1.json'
    if reviewed is None:
        reviewed = read(review_path)['mappings'] if review_path.exists() else {}
    brands = {}
    for item in provider_rows.values():
        if item['profile'].get('_id') in EXCLUSIONS:
            continue
        brands.setdefault(normalize(provider_brand(item['profile'])), []).append(item)
    accepted, reviews = {}, []
    for profile in profiles:
        same_brand = [r for name in expected_brands(profile) for r in brands.get(name, [])]
        matches, hints = [], []
        manual = reviewed.get(profile['id'])
        reviewed_match = None
        for item in same_brand:
            reasons, overlap = evaluate(profile, item['profile'])
            if (manual and manual['fragranticaId'] == profile['fragranticaId']
                    and manual['providerId'] == item['profile'].get('_id')
                    and reasons == ['gender-conflict']):
                reviewed_match = dict(item, identityReview=manual['reason'])
            if not reasons:
                matches.append(item)
            elif 'name-or-edition-mismatch' not in reasons:
                hints.append({'providerId': item['profile']['_id'], 'reasons': reasons, 'noteOverlap': overlap})
        if reviewed_match:
            matches = [reviewed_match]
        if len(matches) > 1:
            # Multiple provider IDs may duplicate an identity. Accept only when all
            # populated year/type values and all ordered accord lists agree.
            years = {str(r['profile'].get('Year')) for r in matches if r['profile'].get('Year')}
            types = {concentration(r['profile'].get('OilType')) for r in matches} - {None}
            accord_sets = {tuple(normalize(a) for a in r['profile'].get('Main Accords', [])) for r in matches}
            if len(years) > 1 or len(types) > 1 or len(accord_sets) > 1:
                hints.extend({'providerId': r['profile']['_id'], 'reasons': ['contradictory-duplicate-identities']} for r in matches)
                matches = []
        if matches:
            selected = sorted(matches, key=lambda r: (not bool(r['profile'].get('OilType')), not bool(r['profile'].get('Year')), r['profile']['_id']))[0]
            accepted[profile['id']] = selected
        else:
            reviews.append({'id': profile['id'], 'name': profile['name'], 'brand': profile['brand'],
                            'canonicalName': canonical_name(profile), 'reasons': hints or [{'reasons': ['no-corroborated-exact-identity']}]})
    owners = {}
    by_id = {p['id']: p for p in profiles}
    for identity, item in accepted.items():
        owners.setdefault(item['profile']['_id'], []).append(identity)
    for provider_id, identities in owners.items():
        original_ids = {by_id[identity]['fragranticaId'] for identity in identities} - {None}
        if len(original_ids) > 1:
            for identity in identities:
                accepted.pop(identity)
                p = by_id[identity]
                reviews.append({'id': identity, 'name': p['name'], 'brand': p['brand'], 'canonicalName': canonical_name(p),
                                'reasons': [{'providerId': provider_id, 'reasons': ['provider-id-shared-by-distinct-originals']}]})
    return accepted, reviews


def provider_fields(row):
    fields = {}
    accords = row.get('Main Accords')
    if isinstance(accords, list) and accords and all(isinstance(a, str) and a.strip() for a in accords):
        fields['accords'] = list(dict.fromkeys(a.strip().lower() for a in accords))
    pyramid = row.get('Notes')
    if isinstance(pyramid, dict):
        levels = {}
        for source, target in [('Top', 'top'), ('Middle', 'heart'), ('Base', 'base')]:
            notes = pyramid.get(source) or []
            if isinstance(notes, list):
                levels[target] = list(dict.fromkeys(n['name'].strip() if isinstance(n, dict) else n.strip()
                    for n in notes if isinstance(n, str) and n.strip() or isinstance(n, dict) and isinstance(n.get('name'), str) and n['name'].strip()))
        if any(levels.values()):
            fields['pyramid'] = {key: levels.get(key, []) for key in ('top', 'heart', 'base')}
    try:
        value = float(row.get('rating'))
        if 0 <= value <= 5:
            fields['rating'] = {'value': value, 'scale': '0–5 (Fragella Bayesian)', 'votes': None}
    except (ValueError, TypeError):
        pass
    for field, key in [('longevity', 'Longevity'), ('sillage', 'Sillage')]:
        label = row.get(key)
        if isinstance(label, str) and label.strip() and normalize(label) not in ('unknown', 'n a', 'not available'):
            fields[field] = {'label': label.strip(), 'scale': 'Fragella descriptive assessment', 'votes': None}
    return fields


def enrich(profile, item):
    result = copy.deepcopy(profile)
    row = item['profile']
    source = 'https://api.fragella.com/api/v1/fragrances/' + quote(row['_id'], safe='')
    for key, value in provider_fields(row).items():
        existing = result[key]
        # Preserve certified/observed values and any previously published values.
        empty = not existing or key == 'pyramid' and not any(existing.values())
        if not empty:
            continue
        result[key] = value
        result['evidence'][key] = evidence(source, 'provider', item['retrievedAt'],
            'Fragella provider assessment; may include model estimates. Individual observed/predicted provenance is unavailable. '
            + 'Provider confidence: ' + str(row.get('Confidence') or 'unspecified') + '. Identity matched by exact name, reviewed brand aliases and inherited note corroboration; ' + ALIASES['version'] + '.'
            + (' Identity review: ' + item['identityReview'] if item.get('identityReview') else ''))
    return result


def run(publish=False):
    profiles = read(DATA / 'catalog/profiles.json')
    rows = load_candidates()
    accepted, reviews = resolve(profiles, rows)
    conflicts = []
    for p in profiles:
        if p['id'] not in accepted:
            continue
        for field, value in provider_fields(accepted[p['id']]['profile']).items():
            existing = p[field]
            if existing and not (field == 'pyramid' and not any(existing.values())) and existing != value:
                conflicts.append({'id': p['id'], 'field': field, 'action': 'retained-published-value',
                                  'providerId': accepted[p['id']]['profile']['_id']})
    report = {'ruleVersion': ALIASES['version'], 'candidateRecords': len(rows), 'accepted': len(accepted), 'review': reviews,
              'excludedProviderRecords': EXCLUSIONS,
              'retainedFieldDisagreements': conflicts,
              'mappings': {identity: {'providerId': r['profile']['_id'], 'retrievedAt': r['retrievedAt'],
                                      'identityMethod': 'reviewed-audience-discrepancy' if r.get('identityReview') else ALIASES['version']} for identity, r in accepted.items()}}
    write(DATA / 'reports/fragella-resolution.json', report)
    write(OUTPUT / 'unresolved-ids.json', [r['id'] for r in reviews])
    write(OUTPUT / 'proposed-mappings.json', report['mappings'])
    if publish:
        updated = [enrich(p, accepted[p['id']]) if p['id'] in accepted else p for p in profiles]
        for p in updated:
            aliases = [*p.get('nameAliases', []), canonical_name(p)]
            correction = ALIASES.get('originalNameCorrections', {}).get(p['fragranticaId'])
            if correction and p['name'] in correction['previousNames']:
                aliases.append(p['name'])
                p['name'] = correction['name']
            if p['id'] in accepted:
                aliases.append(accepted[p['id']]['profile']['Name'])
            p['nameAliases'] = sorted({a.strip() for a in aliases if a.strip() and normalize(a) != normalize(p['name'])})
        validate_profiles(updated)
        build(updated)
        write(DATA / 'catalog/profiles.json', updated)
        write(DATA / 'catalog/fragella-mappings.json', report['mappings'])
    print(f'{len(accepted)} exact corroborated mappings; {len(reviews)} profiles remain in review; {len(rows)} distinct provider records')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true', help='Validate, publish and persist the resolved launch snapshot.')
    args = parser.parse_args()
    run(args.publish)
