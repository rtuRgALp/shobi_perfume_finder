"""Conservative source adapters. Unknown markup and identity fail closed."""
import datetime as dt
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
from .model import read, write


def normalized(value):
    value = unicodedata.normalize("NFKD", str(value))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.encode("ascii", "ignore").decode().lower()).split())


class SourceError(RuntimeError):
    pass


class Client:
    def __init__(self, cache, max_age_days=7, delay=1.0):
        self.cache = Path(cache)
        self.max_age = max_age_days * 86400
        self.delay = delay
        self.last_request = 0.0
        self.failures = {}

    def get(self, url):
        host = urllib.parse.urlparse(url).hostname
        if host not in {"www.fragrantica.com", "leparfum.com.gr"}:
            raise SourceError("Unsupported source host")
        key = hashlib.sha256(url.encode()).hexdigest()
        html_path, meta_path = self.cache / (key + ".html"), self.cache / (key + ".json")
        if html_path.exists() and meta_path.exists() and time.time() - html_path.stat().st_mtime < self.max_age:
            return html_path.read_text(), read(meta_path)
        if self.failures.get(host, 0) >= 3:
            raise SourceError("Source circuit open after three consecutive failures: " + host)
        for attempt in range(2):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "ShobiCatalog/1.0 (independent fragrance research)", "Accept": "text/html"})
                with urllib.request.urlopen(request, timeout=20) as response:
                    final_url = response.url
                    if urllib.parse.urlparse(final_url).hostname != host:
                        raise SourceError("Source redirected to another host")
                    html = response.read(8_000_001)
                    if len(html) > 8_000_000:
                        raise SourceError("Source response exceeded size limit")
                    html = html.decode("utf-8", errors="replace")
                meta = {"source": final_url, "retrievedAt": dt.datetime.now(dt.timezone.utc).isoformat()}
                self.cache.mkdir(parents=True, exist_ok=True)
                html_path.write_text(html)
                write(meta_path, meta)
                self.failures[host] = 0
                return html, meta
            except (urllib.error.URLError, TimeoutError, OSError, SourceError) as error:
                if isinstance(error, urllib.error.HTTPError) and error.code in (403, 429):
                    break
                if attempt == 0:
                    time.sleep(1)
        self.failures[host] = self.failures.get(host, 0) + 1
        raise SourceError("Source unavailable; existing evidence preserved: " + url)


def fragrantica_id(url):
    match = re.search(r"(?:-(\d+)\.html|/p/(\d+))(?:$|[?#/])", url)
    return next((v for v in match.groups() if v), None) if match else None


def parse_fragrantica(html, expected, source_url):
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.select_one('link[rel="canonical"]')
    canonical_url = canonical.get("href", source_url) if canonical else source_url
    if urllib.parse.urlparse(canonical_url).hostname != 'www.fragrantica.com' or fragrantica_id(canonical_url) != expected["fragranticaId"]:
        raise SourceError("Fragrantica ID contradicts established mapping")
    title = soup.select_one('h1[itemprop="name"], h1')
    if not title:
        raise SourceError("Fragrantica identity heading missing")
    title_text = normalized(title.get_text(" ", strip=True))
    # Match exact original + exact brand, allowing only the documented audience suffix.
    identity = normalized(expected["name"] + " " + expected["brand"])
    suffixes = ["", " for women and men", " for men and women", " for women", " for men"]
    if title_text not in [identity + suffix for suffix in suffixes]:
        raise SourceError("Name, brand or edition needs identity review")
    accords = [n.get_text(" ", strip=True).lower() for n in soup.select('.accord-bar')]
    if not accords:
        heading = next((n for n in soup.find_all(['h5', 'h6']) if n.get_text(' ', strip=True).lower() == 'main accords'), None)
        bars = heading.find_next_sibling() if heading else None
        if bars:
            accords = [n.get_text(' ', strip=True).lower() for n in bars.select('div[style*="width:"] > span')]
    accords = list(dict.fromkeys(a for a in accords if a))
    result = {}
    if accords:
        result["accords"] = accords
    pyramid = {}
    for heading, key in [("Top Notes", "top"), ("Middle Notes", "heart"), ("Base Notes", "base")]:
        node = next((n for n in soup.find_all(['h3', 'h4']) if n.get_text(' ', strip=True) == heading), None)
        section = soup.select_one('pyramid-level-new[notes="' + ('middle' if key == 'heart' else key) + '"]')
        if section is None:
            section = node.find_next_sibling() if node else None
        if section:
            names = [a.get_text(" ", strip=True) for a in section.select('a[href*="/notes/"]')]
            if names:
                pyramid[key] = list(dict.fromkeys(names))
    if pyramid:
        result["pyramid"] = {k: pyramid.get(k, []) for k in ["top", "heart", "base"]}
    description = soup.select_one('[itemprop="description"] p')
    if description:
        # Keep the factual opening sentence, avoiding wholesale description reproduction.
        text = description.get_text(" ", strip=True)
        sentence = re.split(r"(?<=[.!?])\s+", text)[0]
        if len(sentence) <= 500:
            result["description"] = sentence
    rating, count = soup.select_one('[itemprop="ratingValue"]'), soup.select_one('[itemprop="ratingCount"]')
    if rating:
        try:
            value = float(rating.get("content") or rating.get_text(strip=True))
            best = soup.select_one('[itemprop="bestRating"]')
            scale = float(best.get("content") or best.get_text(strip=True)) if best else 5
            if 0 <= value <= scale:
                result["rating"] = {"value": value, "scale": "0–" + str(scale).removesuffix('.0'),
                    "votes": int(re.sub(r"\D", "", str(count.get("content") or count.get_text()))) if count else None}
        except (ValueError, TypeError):
            pass
    # Performance votes can be client-rendered. Do not invent numeric scales from labels.
    if not result:
        raise SourceError("Profile sections absent or source layout changed")
    return result


def parse_shobi(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for card in soup.select('article.product-miniature'):
        title = card.select_one('h2.product-title a')
        link = card.select_one('a.product-thumbnail') or title
        pid = card.get('data-id-product')
        if not title or not link or not pid:
            continue
        match = re.search(r"\b(\d+-[A-Z0-9]+)\b", title.get_text(" ", strip=True).upper())
        if not match:
            continue
        description = card.select_one('.product-description-short')
        description_text = description.get_text(" ", strip=True) if description else None
        declared = re.search(r'inspired by (?:the )?fragrance notes of\s+(.+?)(?:\.\s|\.$|$)', description_text or '', re.I)
        url = urllib.parse.urljoin(base_url, link.get('href', ''))
        if urllib.parse.urlparse(url).hostname != "leparfum.com.gr":
            continue
        products.append({"id": str(pid), "code": match.group(1), "url": url,
            "description": description_text, "declaredOriginal": declared.group(1).strip() if declared else None})
    if not products:
        raise SourceError("No Shobi products parsed; collection may be incomplete or markup changed")
    pages = set()
    for link in soup.select('.pagination a[href]'):
        candidate = urllib.parse.urljoin(base_url, link['href'])
        parsed = urllib.parse.urlparse(candidate)
        if parsed.hostname == 'leparfum.com.gr' and parsed.path == urllib.parse.urlparse(base_url).path:
            pages.add(candidate)
    return products, sorted(pages)
