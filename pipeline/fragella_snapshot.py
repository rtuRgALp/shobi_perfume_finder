"""Explicit one-time API collection. Private caches; no automatic publication.

python -m pipeline.fragella_snapshot collect [--limit 2253] [--workers 6]
All runs share a durable 4,980-attempt budget, independent of the completed trial.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlencode, unquote, urlparse
import urllib.error
import urllib.request
import unicodedata

from .fragella_trial import atomic_write, candidates, load_key, query_name, trial_lock
from .model import ROOT, read

OUTPUT = ROOT / 'data/raw/fragella-snapshot'
BUDGET = 4980
BASE = 'https://api.fragella.com/api/v1/'


def canonical_name(profile):
    """Use the established source URL's spelling, retaining edition qualifiers."""
    url = profile.get('fragranticaUrl') or ''
    if '/perfume/' in url:
        slug = unquote(urlparse(url).path.rsplit('/', 1)[-1])
        name = re.sub(r'-\d+\.html$', '', slug).replace('-', ' ')
        if name and not name.endswith('.html'):
            return name
    return query_name(profile)


def search_parameters(profile, fallback=False):
    params = {'search': canonical_name(profile), 'limit': 10, 'page': 1}
    if fallback:
        # Exact brand filtering changes recall; aliases must be reviewed separately.
        aliases = read(ROOT / 'contracts/fragella-identity-aliases.v1.json')
        houses = [profile['brand'], *aliases['brandAliases'].get(profile['brand'], [])]
        for canonical, alternatives in aliases['brandAliases'].items():
            if profile['brand'] in alternatives:
                houses.extend([canonical, *alternatives])
        for supplied, correction in aliases.get('providerBrandCorrections', {}).items():
            if profile['brand'] == correction['canonical']:
                houses.append(supplied)
        path = urlparse(profile.get('fragranticaUrl') or '').path.split('/')
        if len(path) == 4 and path[1] == 'perfume':
            houses.append(unquote(path[2]).replace('-', ' '))
        for house in list(houses):
            house = house.replace('’', "'")
            houses.append(unicodedata.normalize('NFKD', house).encode('ascii', 'ignore').decode())
            houses.append(re.sub(r'\s*&\s*', ' & ', house))
        params['brand'] = ','.join(list(dict.fromkeys(houses))[:10])
        params['search'] = query_name(profile)
    if len(params['search']) < 3:
        params.setdefault('brand', profile['brand'])
        params.pop('search')
    return params


class SnapshotClient:
    def __init__(self, key, directory=OUTPUT, budget=BUDGET, interval=0.5, opener=urllib.request.urlopen):
        if not 1 <= budget <= BUDGET:
            raise ValueError('Budget must be between 1 and 4,980 attempts.')
        self.key, self.directory, self.budget = key, Path(directory), budget
        self.interval, self.opener = interval, opener
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / 'responses').mkdir(exist_ok=True)
        self.ledger_path = self.directory / 'requests.jsonl'
        self.lock = threading.Lock()
        self.last_start = 0.0
        self.stopped = None
        self.attempts = {}
        if self.ledger_path.exists():
            for line in self.ledger_path.read_text().splitlines():
                entry = json.loads(line)  # Corruption fails closed, never resets quota.
                if entry['event'] == 'reserved':
                    self.attempts[entry['id']] = entry

    def log(self, entry):
        import os
        with self.ledger_path.open('a') as output:
            output.write(json.dumps(entry, ensure_ascii=False) + '\n')
            output.flush()
            os.fsync(output.fileno())

    def fetch(self, params):
        url = BASE + 'fragrances?' + urlencode(params)
        identity = hashlib.sha256(url.encode()).hexdigest()
        cache = self.directory / 'responses' / (identity + '.json')
        with self.lock:
            if cache.exists():
                return read(cache), True
            if self.stopped:
                raise ValueError(self.stopped)
            if identity in self.attempts:
                raise ValueError('Request already attempted without a usable response; not retried.')
            if len(self.attempts) >= self.budget:
                self.stopped = 'Local API budget exhausted.'
                raise ValueError(self.stopped)
            time.sleep(max(0, self.interval - (time.monotonic() - self.last_start)))
            self.last_start = time.monotonic()
            entry = {'event': 'reserved', 'id': identity, 'url': url, 'retrievedAt': datetime.now(timezone.utc).isoformat()}
            self.log(entry)
            self.attempts[identity] = entry
        status = 'interrupted'
        try:
            request = urllib.request.Request(url, headers={'x-api-key': self.key, 'Accept': 'application/json', 'User-Agent': 'Shobi-Snapshot/1.0'})
            with self.opener(request, timeout=30) as response:
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise ValueError('Response exceeds size limit.')
                payload = json.loads(body)
            candidates(payload)
            payload = json.loads(json.dumps(payload).replace(self.key, '[REDACTED]'))
            result = {'source': url, 'retrievedAt': entry['retrievedAt'], 'response': payload}
            atomic_write(cache, result)
            status = 'ok'
            return result, False
        except urllib.error.HTTPError as error:
            status = 'http-' + str(error.code)
            if error.code in (401, 402, 403, 429):
                with self.lock:
                    self.stopped = f'Provider returned HTTP {error.code}; remaining work stopped.'
            raise ValueError(f'HTTP {error.code}') from None
        except (OSError, ValueError):
            status = 'failed'
            raise ValueError('Request or response failed; existing catalog retained.') from None
        finally:
            with self.lock:
                self.log({'event': 'completed', 'id': identity, 'status': status})


def collect(limit=None, workers=6, fallback=False, ids=None):
    if not 1 <= workers <= 8:
        raise ValueError('Use 1–8 workers.')
    profiles = read(ROOT / 'data/catalog/profiles.json')
    if ids is not None:
        profiles = [p for p in profiles if p['id'] in ids]
    profiles = sorted(profiles, key=lambda p: p['id'])[:limit]
    key = load_key()
    with trial_lock(OUTPUT):
        client = SnapshotClient(key)
        report_path = OUTPUT / ('fallback.json' if fallback else 'collection.json')
        report = read(report_path) if report_path.exists() else {'version': 1, 'provider': 'Fragella', 'records': {}}
        pending_profiles = iter(profiles)
        def work(p):
            params = search_parameters(p, fallback)
            try:
                data, cached = client.fetch(params)
                return p['id'], {'source': data['source'], 'retrievedAt': data['retrievedAt'], 'candidateCount': len(candidates(data['response'])), 'cached': cached, 'status': 'ok'}
            except ValueError as error:
                return p['id'], {'status': 'failed', 'error': str(error)}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(work, p) for p in [next(pending_profiles, None) for _ in range(workers)] if p}
            completed = 0
            while futures:
                done, futures = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    identity, row = future.result()
                    report['records'][identity] = row
                    completed += 1
                    report['attempts'] = len(client.attempts)
                    report['stopped'] = client.stopped
                    atomic_write(report_path, report)
                    if completed % 25 == 0 or completed == len(profiles):
                        print(f'{completed}/{len(profiles)} records; {len(client.attempts)} total API attempts; {sum(r["status"] == "ok" for r in report["records"].values())} usable responses', flush=True)
                    p = next(pending_profiles, None) if not client.stopped else None
                    if p:
                        futures.add(pool.submit(work, p))
        print('Private collection report:', report_path, flush=True)
        if client.stopped:
            raise ValueError(client.stopped)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['collect'])
    parser.add_argument('--limit', type=int)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--fallback-ids', type=Path, help='JSON array of reviewed unresolved catalog IDs for brand-filtered fallback searches.')
    args = parser.parse_args()
    try:
        collect(args.limit, args.workers, args.fallback_ids is not None, read(args.fallback_ids) if args.fallback_ids else None)
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
