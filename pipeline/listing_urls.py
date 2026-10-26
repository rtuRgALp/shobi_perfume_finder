"""Keep shopping links independent of imported product-option selections."""
import copy
from urllib.parse import urldefrag
from .model import ROOT, read


def clean_listing_url(url):
    return urldefrag(url)[0]


def clean_listing_urls(profiles):
    result = copy.deepcopy(profiles)
    rules = {(r['id'], r['listingId'], r['code']): r
        for r in read(ROOT / 'contracts/listing-url-corrections.v1.json')['mappings']}
    for profile in result:
        for listing in profile['listings']:
            listing['url'] = clean_listing_url(listing['url'])
            rule = rules.get((profile['id'], listing['id'], listing['code']))
            if rule and listing['url'] == rule['previousUrl']:
                listing['url'] = rule['url']
    return result
