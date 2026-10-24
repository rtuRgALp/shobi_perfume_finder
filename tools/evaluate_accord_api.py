"""Small, read-only 10ML accord pilot. Never writes production catalog data.

Run: python tools/evaluate_accord_api.py [--refresh]
Responses are retained in the private raw cache; results are research evidence,
not approved identity mappings or statistically representative coverage estimates.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import random
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/raw/accord-api-evaluation"


def normalize(value):
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.lower().replace("&", " and ")))


def edition_name(value):
    text = normalize(value)
    for phrase, short in [('extrait de parfum', 'extrait'), ('eau de parfum', 'edp'), ('eau de toilette', 'edt')]:
        text = text.replace(phrase, short)
    return text


def name_without_brand(profile):
    name, brand = profile['name'], profile['brand']
    # A natural suffix such as "Bleu de Chanel" is part of the perfume name.
    # Remove only an explicit brand prefix or a delimited source suffix.
    prefix = re.compile(r'^' + re.escape(brand) + r'\s+', re.I)
    name = prefix.sub('', name)
    return re.sub(r'\s+[-–—|]\s*' + re.escape(brand) + r'$', '', name, flags=re.I).strip()


def sample(profiles):
    targets = ['9828', '33519', '46066', '31861', '9099', '14982', '410', '17',
        '11801', '3865', '74594', '118623', '66514', '81409', '117345', '98362', '10554']
    by_fid = {p['fragranticaId']: p for p in profiles if p['fragranticaId']}
    selected = [(by_fid[fid], 'targeted') for fid in targets if fid in by_fid]
    selected.extend((p, 'missing-source') for p in profiles if not p['fragranticaId'])
    chosen = {p['id'] for p, _ in selected}
    pool = sorted((p for p in profiles if p['id'] not in chosen), key=lambda p: p['id'])
    selected.extend((p, 'seeded-random') for p in random.Random(20261023).sample(pool, 40 - len(selected)))
    return selected


def run(refresh=False, search=False):
    profiles = json.loads((ROOT / 'data/catalog/profiles.json').read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rules = json.loads((ROOT / 'contracts/boost-rules.v1.json').read_text())
    triggers = set(rules['heavy'] + rules['light'])
    results = []
    for index, (profile, stratum) in enumerate(sample(profiles), 1):
        query_name = name_without_brand(profile)
        parameters = {'house': profile['brand'], 'format': 'detailed', 'locale': 'en'}
        if search:
            parameters.update(q=query_name, limit=8)
            url = 'https://mcp.10ml.com/api/v1/perfumes?' + urllib.parse.urlencode(parameters)
        else:
            url = 'https://mcp.10ml.com/api/v1/perfumes/' + urllib.parse.quote(query_name, safe='') + '?' + urllib.parse.urlencode(parameters)
        cache = OUTPUT / ('pilot-' + hashlib.sha256(url.encode()).hexdigest() + '.json')
        row = {'id': profile['id'], 'name': profile['name'], 'brand': profile['brand'],
            'stratum': stratum, 'queryName': query_name, 'url': url}
        try:
            started = time.monotonic()
            cached = cache.exists() and not refresh
            if cached:
                response = json.loads(cache.read_text())
            else:
                time.sleep(1)
                req = urllib.request.Request(url, headers={'User-Agent': 'Shobi-API-Evaluation/1.0', 'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=25) as r:
                    response = json.load(r)
                cache.write_text(json.dumps(response, ensure_ascii=False, indent=2))
            candidates = response.get('results', []) if search else [response.get('perfume') or {}]
            candidates = [p for p in candidates if p]
            matches = [p for p in candidates if edition_name(p.get('name', '')) in {edition_name(profile['name']), edition_name(query_name)} and normalize(p.get('house', '')) == normalize(profile['brand'])]
            row.update(found=bool(candidates) if search else response.get('found', False), providerExact=response.get('exact'),
                elapsedSeconds=round(time.monotonic() - started, 3), cached=cached)
            perfume = (matches[0] if len(matches) == 1 else {}) if search else response.get('perfume') or {}
            row.update(candidates=[{k: p.get(k) for k in ['id', 'name', 'house', 'concentration', 'accords']} for p in candidates],
                candidateCount=len(candidates), unambiguousLiteralEditionAndHouseMatch=len(matches) == 1, relaxed=response.get('relaxed'))
            accords = perfume.get('accords') or []
            row.update(providerId=perfume.get('id'), providerName=perfume.get('name'),
                providerHouse=perfume.get('house'), concentration=perfume.get('concentration'),
                accords=accords, hasAccords=bool(accords), profileKind=perfume.get('profile'),
                literalNameMatch=normalize(perfume.get('name', '')) in {normalize(profile['name']), normalize(query_name)},
                literalHouseMatch=normalize(perfume.get('house', '')) == normalize(profile['brand']),
                recognizedBoostTrigger=any(rules['vocabulary'].get(a.strip().lower()) in triggers for a in accords))
        except urllib.error.HTTPError as error:
            row.update(error=str(error), status=error.code,
                responseBody=error.read(4000).decode('utf-8', errors='replace'))
            if error.code == 429:
                results.append(row)
                print('Rate limited; ending pilot without retries.', flush=True)
                break
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            row['error'] = str(error)
        results.append(row)
        print(f"{index}/40 {profile['name']}: found={row.get('found')} accords={len(row.get('accords', []))}", flush=True)
    report = {'evaluatedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
        'method': ('Search endpoint with explicit name, house and normalized EDP/EDT/Extrait comparison. ' if search else 'Direct name lookup. ') + '40 mixed targeted and seeded-random catalog profiles; one documented request per profile, 1-second delay; no production updates',
        'attempted': len(results), 'found': sum(bool(r.get('found')) for r in results),
        'withAccords': sum(bool(r.get('hasAccords')) for r in results),
        'literalNameAndHouseMatchWithAccords': sum(bool(r.get('hasAccords') and r.get('literalNameMatch') and r.get('literalHouseMatch')) for r in results),
        'unambiguousNormalizedMatchWithAccords': sum(bool(r.get('hasAccords') and r.get('unambiguousLiteralEditionAndHouseMatch')) for r in results),
        'notFoundResponses': sum(r.get('status') == 404 for r in results),
        'otherFailures': sum(bool(r.get('error')) and r.get('status') != 404 for r in results),
        'results': results}
    (OUTPUT / ('10ml-search-pilot.json' if search else '10ml-pilot.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Re-request instead of using saved research responses')
    parser.add_argument('--search', action='store_true', help='Evaluate the search endpoint and strict candidate matching')
    args = parser.parse_args()
    run(args.refresh, args.search)
