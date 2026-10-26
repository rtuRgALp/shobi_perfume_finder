"""Explicit, read-only audit of designer-bearing and other descriptive shop URLs.

Run with python -m pipeline.link_audit. Network results remain private until
reviewed corrections are pinned in a contract; ordinary builds never fetch URLs.
"""
import concurrent.futures
import argparse
import datetime as dt
import hashlib
import re
import subprocess
import threading
import time
import unicodedata
import urllib.parse

from bs4 import BeautifulSoup
from .model import DATA, read, write


def words(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return re.findall(r'[a-z0-9]+', value.lower())


def normalize_url(url):
    # Canonical tags can contain literal Greek/Cyrillic characters while catalog
    # URLs already percent-encode them. Encoding alone is not a dead-link fix.
    encoded = urllib.parse.quote(urllib.parse.urldefrag(url)[0], safe=":/?=&%+@;,-._~!$()[]")
    return re.sub(r'%[0-9a-fA-F]{2}', lambda m: m.group().upper(), encoded)


def audit_scope(profiles):
    result = []
    for profile in profiles:
        brand = set(words(profile['brand'])) - {'and', 'by', 'the', 'paris', 'london', 'perfumes', 'parfums', 'de'}
        for listing in profile['listings']:
            slug = urllib.parse.unquote(urllib.parse.urlsplit(listing['url']).path.rsplit('/', 1)[-1])
            tokens = set(words(slug))
            designer = bool(brand) and (brand <= tokens or any(len(w) >= 4 and w in tokens for w in brand))
            descriptive = not re.match(r'^\d{1,5}-[a-zA-Z0-9]+(?:-|$)', slug)
            if designer or descriptive:
                result.append({'id': profile['id'], 'brand': profile['brand'], 'name': profile['name'],
                    'listingId': listing['id'], 'code': listing['code'], 'url': listing['url'],
                    'designerInUrl': designer})
    return result


def inspect_product(html, expected_id, expected_code):
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.select_one('h1')
    product_id = soup.select_one('input[name="id_product"]')
    canonical = soup.select_one('link[rel="canonical"]')
    title = heading.get_text(' ', strip=True) if heading else None
    code_title = re.sub(r'\s*[-–—]\s*', '-', title or '')
    actual_id = product_id.get('value') if product_id else None
    matches = bool(actual_id == expected_id and title and
        re.search(r'(?<![A-Z0-9-])' + re.escape(expected_code) + r'(?![A-Z0-9-])', code_title, re.I))
    return {'productId': actual_id, 'heading': title, 'identityMatches': matches,
        'canonical': canonical.get('href') if canonical else None}


class Auditor:
    def __init__(self, directory, interval=0.5):
        self.directory = directory
        self.interval = interval
        self.lock = threading.Lock()
        self.last_start = 0

    def fetch(self, url, row):
        with self.lock:
            time.sleep(max(0, self.interval - (time.monotonic() - self.last_start)))
            self.last_start = time.monotonic()
        record = {'requestedUrl': url, 'checkedAt': dt.datetime.now(dt.timezone.utc).isoformat()}
        key = hashlib.sha256(url.encode()).hexdigest()
        body = self.directory / (key + '.html')
        try:
            # A socket timeout does not bound DNS/redirects or a trickling body.
            # curl's total deadline also prevents one stalled shop request from
            # holding the audit indefinitely. Pass arguments without a shell.
            response = subprocess.run(['curl', '--silent', '--show-error', '--location',
                '--max-time', '25', '--max-redirs', '5', '--max-filesize', '8000000',
                '--header', 'Cache-Control: no-cache', '--output', str(body),
                '--write-out', '%{http_code}\n%{url_effective}', url],
                capture_output=True, text=True, timeout=30)
            if response.returncode:
                record['error'] = response.stderr.strip() or 'Request failed'
                return record
            status, final_url = response.stdout.split('\n', 1)
            record.update(httpStatus=int(status), finalUrl=final_url)
            if int(status) != 200:
                record['error'] = 'HTTP ' + status
                return record
            if urllib.parse.urlsplit(record['finalUrl']).hostname != 'leparfum.com.gr':
                record['error'] = 'Unexpected redirect host'
                return record
            html = body.read_text(errors='replace')
            record.update(inspect_product(html, row['listingId'], row['code']))
        except (subprocess.TimeoutExpired, TimeoutError, OSError) as error:
            record['error'] = str(error)
        return record

    def check(self, row):
        row = dict(row)
        original = self.fetch(row['url'], row)
        row['checks'] = [original]
        row['status'] = 'working' if original.get('identityMatches') else 'unresolved'
        candidate = original.get('canonical') if original.get('identityMatches') else None
        if not candidate:
            lookup = 'https://leparfum.com.gr/index.php?controller=product&id_product=' + row['listingId'] + '&id_lang=1'
            recovery = self.fetch(lookup, row)
            row['checks'].append(recovery)
            if recovery.get('identityMatches'):
                candidate = recovery.get('canonical')
        if candidate:
            candidate = normalize_url(candidate)
            parsed = urllib.parse.urlsplit(candidate)
            if parsed.scheme == 'https' and parsed.hostname == 'leparfum.com.gr' and parsed.path.startswith('/en/') and candidate != normalize_url(row['url']):
                verified = self.fetch(candidate, row)
                row['checks'].append(verified)
                if verified.get('identityMatches'):
                    row.update(status='correction', correctedUrl=candidate)
        return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume', action='store_true', help='Keep completed checks from the current audit')
    parser.add_argument('--retry-unresolved', action='store_true', help='Resume and recheck unresolved requests')
    args = parser.parse_args()
    directory = DATA / 'raw/link-audit'
    directory.mkdir(parents=True, exist_ok=True)
    scope = audit_scope(read(DATA / 'catalog/profiles.json'))
    auditor = Auditor(directory)
    results = read(directory / 'report.json')['results'] if (args.resume or args.retry_unresolved) and (directory / 'report.json').exists() else []
    scope_keys = {(r['listingId'], r['url']) for r in scope}
    results = [r for r in results if (r['listingId'], r['url']) in scope_keys
        and not (args.retry_unresolved and r['status'] == 'unresolved')]
    completed = {(r['listingId'], r['url']) for r in results}
    print('Auditing', len(scope), 'URLs;', sum(r['designerInUrl'] for r in scope), 'designer matches', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(auditor.check, row) for row in scope if (row['listingId'], row['url']) not in completed]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            results.append(row)
            write(directory / 'report.json', {'checkedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
                'scopeCount': len(scope), 'results': sorted(results, key=lambda r: r['id'])})
            if len(results) % 20 == 0 or row['status'] != 'working':
                print(len(results), '/', len(scope), row['status'], row['code'], row.get('correctedUrl', row['url']), flush=True)


if __name__ == '__main__':
    main()
