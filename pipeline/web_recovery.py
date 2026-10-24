"""Recover explicit profile fields from saved public-page research receipts.

Receipts contain the original URL, retrieval time and unmodified readable page
extract. Only established source IDs with matching perfume/house headings are
accepted. Search snippets, reviews and inferred accord classifications are not
inputs. Collection is explicit and never runs during deployment.
"""
import argparse
import copy
from pathlib import Path
import re

from .fragella_resolve import expected_brands, display_names
from .fragella_snapshot import canonical_name
from .fragella_trial import normalize
from .model import DATA, ROOT, evidence, read, validate_profiles, write
from .refresh import hydrate
from .release import build
from .sources import SourceError, fragrantica_id

VERSION = 'public-page-extract-v2'
RECEIPTS = DATA / 'raw/web-recovery'
FIELDS = ('accords', 'pyramid', 'description', 'rating', 'longevity', 'sillage')


def missing_fields(profile):
    return [field for field in FIELDS if not profile[field] or
            field == 'pyramid' and not all(profile[field].values())]


def split_pages(raw):
    pattern = r'^([^\n]+) \((https://www\.fragrantica\.com/[^\n]+)\)\n'
    matches = list(re.finditer(pattern, raw, re.M))
    for i, match in enumerate(matches):
        block = raw[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(raw)]
        if 'Source: open(' not in block[:1500]:
            continue
        yield match.group(2), block


def clean_line(line):
    return re.sub(r'^L\d+: ?', '', line).strip()


def source_name(value, brand):
    value = normalize(value)
    for prefix in sorted(display_names(brand), key=len, reverse=True):
        if value.startswith(prefix + ' '):
            value = value[len(prefix)+1:]
            break
    return ' '.join(word for word in value.split() if word != 'and')


def heading_matches(heading, profile):
    reviewed = read(ROOT / 'contracts/public-source-headings.v1.json')['mappings']
    for item in reviewed:
        if all(profile.get(key) == item[key] for key in ('id', 'fragranticaId', 'name', 'brand')) and heading.strip() == item['heading']:
            return True
    actual = normalize(heading)
    # Remove only the final page audience label, keeping audience words that
    # belong to the perfume's own name (e.g. Rush for Men) intact.
    for suffix in (' for women and men', ' for men and women', ' for women', ' for men', ' unisex'):
        if actual.endswith(suffix):
            actual = actual[:-len(suffix)]
            break
    expected = {source_name(name, profile['brand']) for name in
                [profile['name'], canonical_name(profile), *profile.get('nameAliases', [])]}
    for brand in expected_brands(profile):
        if actual.endswith(' ' + brand):
            name = actual[:-len(brand)-1]
            if source_name(name, profile['brand']) in expected:
                return True
    return False


def parse_page(raw, profile, source):
    if fragrantica_id(source) != profile['fragranticaId'] or not profile['fragranticaId']:
        raise SourceError('Source ID does not match the established original')
    if profile['validationChecks'].get('identity') is not True:
        raise SourceError('Original identity needs review before enrichment')
    lines = [clean_line(line) for line in raw.splitlines()]
    heading = next((line[2:] for line in lines if line.startswith('# ')), None)
    if not heading:
        raise SourceError('Original identity heading unavailable')
    if not heading_matches(heading, profile):
        raise SourceError('Source heading differs from the established name, house or edition: ' + heading)
    start = next((i for i, line in enumerate(lines) if re.fullmatch(r'#{3,6} main accords', line, re.I)), None)
    accords = []
    for line in lines[start + 1:] if start is not None else []:
        if not line:
            continue
        if not re.fullmatch(r'[a-z][a-z -]{1,35}', line):
            break
        accords.append(line)
    fields = {'accords': list(dict.fromkeys(accords))} if 0 < len(accords) <= 20 else {}
    # Exclude user reviews and recommendation sections from structured extraction.
    plain = '\n'.join(lines).split('### Designer ')[0]
    rating = re.search(r'Perfume rating\s+([\d.]+)\s+out of\s+([\d.]+)\s+with\s+([\d,]+)\s+votes', plain)
    if rating:
        value, scale = float(rating[1]), float(rating[2])
        if 0 <= value <= scale:
            fields['rating'] = {'value': value, 'scale': '0–' + str(scale).removesuffix('.0'), 'votes': int(rating[3].replace(',', ''))}
    pyramid = {}
    for label, key in [('Top', 'top'), ('Middle', 'heart'), ('Base', 'base')]:
        section = re.search(r'^#{3,6} ' + label + r' Notes\s*\n(.*?)(?=^#{1,6} |\Z)', plain, re.M | re.S)
        if section:
            names = re.findall(r'【\d+†([^】†]+)(?:†[^】]+)?】', section[1])
            if names:
                pyramid[key] = list(dict.fromkeys(names))
    if pyramid:
        fields['pyramid'] = {key: pyramid.get(key, []) for key in ('top', 'heart', 'base')}
    # Summarize only the structured introductory family/year statement. Never
    # reproduce articles/reviews or derive profile claims from note lists.
    intro = plain.split('Fragrance Composition')[0]
    family = re.search(r' by [^\n]+? is an? ([^.\n]+?) fragrance for ([^.\n]+)\.', intro)
    if family:
        kind = family[1].lower()
        article = 'An' if kind[:1] in 'aeiou' else 'A'
        sentence = f'{article} {kind} fragrance for {family[2]}.'
        year = re.search(r'was launched in (\d{4})\.', intro)
        if year:
            sentence += ' Introduced in ' + year[1] + '.'
        fields['description'] = sentence
    if not fields:
        raise SourceError('No supported structured fields available in the source extract')
    return fields


def recover(profiles, directory=RECEIPTS):
    by_fid = {}
    for path in sorted(Path(directory).glob('*.json')):
        receipt = read(path)
        for source, raw in split_pages(receipt['raw']):
            fid = fragrantica_id(source)
            if fid:
                by_fid.setdefault(fid, []).append({'source': source, 'raw': raw, 'retrievedAt': receipt['retrievedAt'], 'receipt': path.name})
    updated, imported, review = copy.deepcopy(profiles), [], []
    for p in updated:
        if not missing_fields(p):
            continue
        options = by_fid.get(p['fragranticaId'], [])
        failures = []
        for item in sorted(options, key=lambda r: r['retrievedAt'], reverse=True):
            try:
                fields = parse_page(item['raw'], p, item['source'])
                empty = {key: value for key, value in fields.items() if key in missing_fields(p)}
                if 'pyramid' in empty and any(p['pyramid'].values()):
                    candidate = empty['pyramid']
                    # Complete a partial pyramid only from one complete source
                    # agreeing with every retained layer; never combine conflicts.
                    if not all(candidate.values()) or any(p['pyramid'][k] and p['pyramid'][k] != candidate[k] for k in p['pyramid']):
                        del empty['pyramid']
                        failures.append('Pyramid incomplete or disagrees with a retained layer')
                if not empty:
                    continue
                enriched = hydrate(p, empty, item)
                for field in empty:
                    enriched['evidence'][field]['note'] = 'Observed in a publicly accessible indexed original profile; exact source ID and perfume/house heading matched. ' + VERSION + '. Main Notes remain separate.'
                p.update(enriched)
                imported.append({'id': p['id'], 'source': item['source'], 'receipt': item['receipt'], 'fields': list(empty)})
                if not missing_fields(p):
                    break
            except (SourceError, ValueError) as error:
                failures.append(str(error))
        if missing_fields(p):
            review.append({'id': p['id'], 'name': p['name'], 'brand': p['brand'], 'fragranticaId': p['fragranticaId'],
                           'fields': missing_fields(p),
                           'reason': failures[0] if failures else 'Source does not supply remaining fields' if options else 'No readable source receipt'})
    return updated, {'parserVersion': VERSION, 'imported': imported, 'remaining': review,
                     'missingByField': {field: sum(field in missing_fields(p) for p in updated) for field in FIELDS},
                     'missingPyramidLayers': {level: sum(not p['pyramid'][level] for p in updated) for level in ('top', 'heart', 'base')}}


def reviewed_corrections(profiles):
    result = copy.deepcopy(profiles)
    rules = read(ROOT / 'contracts/reviewed-source-corrections.v1.json')['mappings']
    for p in result:
        rule = next((r for r in rules if r['id'] == p['id']), None)
        if not rule or p['evidence']['identity']['note'] == rule['reason']:
            continue
        if any(p.get(key) != value for key, value in rule['expected'].items()):
            raise SourceError('Reviewed correction no longer matches original: ' + p['id'])
        old_source = p['fragranticaUrl']
        p.update(rule['updates'])
        p.update(hydrate(p, rule['fields'], {'source': rule['source'], 'retrievedAt': rule['retrievedAt']}))
        p['evidence']['identity'] = evidence(rule['identitySource'], 'verified', rule['retrievedAt'], rule['reason'])
        if rule.get('withdrawnMainNotes'):
            for field in ('mainNotes', 'seasons'):
                p['evidence'][field] = evidence(old_source, 'conflicting', rule['retrievedAt'], rule['reason'])
            p['imageEvidence'] = evidence(old_source, 'conflicting', rule['retrievedAt'], rule['reason'])
            p['evidence']['gender'] = evidence(rule['source'], 'verified', rule['retrievedAt'], 'Original page explicitly labels the male fragrance.')
        for field in rule['fields']:
            p['evidence'][field]['note'] = rule['reason']
    return result


def run(publish=False):
    profiles, report = recover(reviewed_corrections(read(DATA / 'catalog/profiles.json')))
    write(DATA / 'reports/web-recovery.json', report)
    if publish:
        validate_profiles(profiles)
        build(profiles)
        write(DATA / 'catalog/profiles.json', profiles)
    print(f"{len(report['imported'])} source observations imported; missing fields: {report['missingByField']}")
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    run(parser.parse_args().publish)
