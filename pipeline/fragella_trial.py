"""Private, bounded provider evaluation; never imports or publishes profiles.

Run from the project root: .venv/bin/python -m pipeline.fragella_trial --dry-run
Then configure FRAGELLA_API_KEY in the environment or .env.local and omit --dry-run.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from pipeline.model import ROOT, read

OUTPUT = ROOT / 'data/raw/fragella-trial'
MAX_REQUESTS = 20
TARGET_FIDS = ('9828', '33519', '46066', '31861', '9099', '14982', '410', '17',
               '11801', '3865', '74594', '118623', '66514', '117345', '98362',
               '10554', '31619', '84547')


def normalize(value):
    value = str(value or '').replace('’', "'").replace('‘', "'")
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    value = ' '.join(re.findall(r'[a-z0-9]+', value.lower().replace('&', ' and ')))
    for phrase, short in [('extrait de parfum', 'extrait'), ('eau de parfum', 'edp'), ('eau de toilette', 'edt')]:
        value = value.replace(phrase, short)
    return value


def query_name(profile):
    brand = re.escape(profile['brand'])
    name = re.sub(r'^' + brand + r'\s+', '', profile['name'], flags=re.I)
    return re.sub(r'\s+[-–—|]\s*' + brand + r'$', '', name, flags=re.I).strip()


def sample(profiles):
    by_fid = {p['fragranticaId']: p for p in profiles if p['fragranticaId']}
    selected = [by_fid[fid] for fid in TARGET_FIDS if fid in by_fid]
    selected.extend(sorted((p for p in profiles if not p['fragranticaId']), key=lambda p: p['id']))
    return selected[:MAX_REQUESTS]


def load_key(path=None):
    key = os.environ.get('FRAGELLA_API_KEY', '').strip()
    path = Path(path) if path is not None else ROOT / '.env.local'
    if not key and path.exists():
        for line in path.read_text().splitlines():
            name, sep, value = line.strip().partition('=')
            if sep and name.strip() == 'FRAGELLA_API_KEY':
                key = value.strip().strip('\"\'')
                break
    if not key or key.startswith('pub_') or key in {'YOUR_API_KEY', '[api-key]'}:
        raise ValueError('Set a secret FRAGELLA_API_KEY in .env.local or the environment. A public widget key cannot be used.')
    return key


def atomic_write(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


@contextmanager
def trial_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another Fragella trial is already running.') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


class TrialClient:
    """Reserve attempts durably before network access; never retry spent requests.

    The 20-request cap applies to this entire local trial, including failed and
    interrupted attempts, across reruns. It does not track other API clients.
    """
    def __init__(self, key, directory=OUTPUT, opener=urllib.request.urlopen):
        self.key, self.directory, self.opener = key, Path(directory), opener
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.directory / 'requests.json'
        self.ledger = read(self.ledger_path) if self.ledger_path.exists() else {'version': 1, 'attempts': []}
        if self.ledger.get('version') != 1 or not isinstance(self.ledger.get('attempts'), list):
            raise ValueError('Invalid request ledger; refusing network access.')

    def fetch(self, query):
        url = 'https://api.fragella.com/api/v1/fragrances?' + urllib.parse.urlencode({'search': query, 'limit': 10, 'page': 1})
        cache_id = hashlib.sha256(url.encode()).hexdigest()
        cache = self.directory / (cache_id + '.json')
        if cache.exists():
            return read(cache), True
        if any(a['id'] == cache_id for a in self.ledger['attempts']):
            raise ValueError('This request was already attempted without a usable cache; manual review is required before retrying.')
        if len(self.ledger['attempts']) >= MAX_REQUESTS:
            raise ValueError('The persistent 20-request trial budget is exhausted.')
        entry = {'id': cache_id, 'query': query, 'startedAt': datetime.now(timezone.utc).isoformat(), 'status': 'reserved'}
        self.ledger['attempts'].append(entry)
        atomic_write(self.ledger_path, self.ledger)
        request = urllib.request.Request(url, headers={'x-api-key': self.key, 'Accept': 'application/json', 'User-Agent': 'Shobi-Fragella-Trial/1.0'})
        try:
            with self.opener(request, timeout=30) as response:
                payload = json.load(response)
            # Do not store headers or error bodies. Defensively redact an echoed key.
            payload = json.loads(json.dumps(payload).replace(self.key, '[REDACTED]'))
            candidates(payload)  # Fail closed on an unexpected response shape.
            atomic_write(cache, payload)
            entry['status'] = 'ok'
            return payload, False
        except urllib.error.HTTPError as error:
            entry['status'] = 'http-' + str(error.code)
            raise ValueError(f'Fragella returned HTTP {error.code}; stopped without retrying.') from None
        except (OSError, ValueError):
            entry['status'] = 'failed'
            raise ValueError('Request or response validation failed; stopped without retrying.') from None
        finally:
            atomic_write(self.ledger_path, self.ledger)


def candidates(payload):
    rows = payload.get('data') if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not all(isinstance(p, dict) for p in rows):
        raise ValueError('Unexpected Fragella response shape')
    return rows


def assess(profile, payload, rules):
    """Expose review hints, not identity approvals or verified provenance."""
    expected_names = {normalize(profile['name']), normalize(query_name(profile))}
    rows = []
    for p in candidates(payload):
        accords = p.get('Main Accords') or []
        accords = accords if isinstance(accords, list) and all(isinstance(a, str) for a in accords) else []
        matches = sorted({rules['vocabulary'][a.strip().lower()] for a in accords
                          if a.strip().lower() in rules['vocabulary']})
        name_match = normalize(p.get('Name')) in expected_names
        brand_match = normalize(p.get('Brand')) == normalize(profile['brand'])
        # An explicit source concentration can reject a conflicting API OilType.
        expected_types = set(re.findall(r'\b(?:edp|edt|extrait)\b', normalize(profile['name'])))
        api_types = set(re.findall(r'\b(?:edp|edt|extrait)\b', normalize(p.get('OilType'))))
        conflict = bool(expected_types and api_types and expected_types != api_types)
        rows.append({
            'providerId': p.get('_id'), 'name': p.get('Name'), 'brand': p.get('Brand'),
            'year': p.get('Year'), 'concentration': p.get('OilType'), 'gender': p.get('Gender'),
            'accords': accords, 'accordStrengths': p.get('Main Accords Percentage'),
            'providerConfidence': p.get('Confidence'), 'accordProvenance': 'unspecified-may-be-predicted',
            'nameMatch': name_match, 'brandMatch': brand_match, 'concentrationConflict': conflict,
            'identityHint': 'name-and-brand-candidate' if name_match and brand_match and not conflict else 'mismatch-or-alias-review',
            'recognizedVocabulary': matches,
            'boostTriggerMatches': [a for a in matches if a in rules['heavy'] + rules['light']],
            'approved': False,
        })
    return {'catalogId': profile['id'], 'name': profile['name'], 'brand': profile['brand'],
            'fragranticaId': profile['fragranticaId'], 'query': query_name(profile),
            'reviewRequired': True, 'candidates': rows,
            'hasMore': payload.get('pagination', {}).get('has_more') if isinstance(payload, dict) else None}


def run(dry_run=False, limit=MAX_REQUESTS):
    if not 1 <= limit <= MAX_REQUESTS:
        raise ValueError('Limit must be between 1 and 20.')
    selected = sample(read(ROOT / 'data/catalog/profiles.json'))[:limit]
    if dry_run:
        print(json.dumps({'networkRequests': 0, 'plannedQueries': [query_name(p) for p in selected]}, indent=2))
        return
    key = load_key()  # No requests or state writes when the key is missing.
    rules = read(ROOT / 'contracts/boost-rules.v1.json')
    with trial_lock(OUTPUT):
        client = TrialClient(key)
        report = {'version': 1, 'provider': 'Fragella', 'approvedImports': 0, 'results': [], 'stopped': None}
        for profile in selected:
            try:
                before = len(client.ledger['attempts'])
                payload, cached = client.fetch(query_name(profile))
                row = assess(profile, payload, rules)
                row['cached'] = cached
                report['results'].append(row)
                print(f"{len(report['results'])}/{len(selected)}: {profile['name']} — {len(row['candidates'])} candidates", flush=True)
                if len(client.ledger['attempts']) > before:
                    time.sleep(1)
            except ValueError as error:
                report['stopped'] = str(error)
                break
            finally:
                report['requestsAttempted'] = len(client.ledger['attempts'])
                atomic_write(OUTPUT / 'report.json', report)
        print(f"Trial report: {OUTPUT / 'report.json'}")
        if report['stopped']:
            raise ValueError(report['stopped'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Preview the sample without credentials or network access.')
    parser.add_argument('--limit', type=int, default=MAX_REQUESTS, help='Maximum sample size (1–20); reruns share one persistent 20-request budget.')
    args = parser.parse_args()
    try:
        run(args.dry_run, args.limit)
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
