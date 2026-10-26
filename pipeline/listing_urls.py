"""Keep shopping links independent of imported product-option selections."""
import copy
from urllib.parse import urldefrag


def clean_listing_url(url):
    return urldefrag(url)[0]


def clean_listing_urls(profiles):
    result = copy.deepcopy(profiles)
    for profile in result:
        for listing in profile['listings']:
            listing['url'] = clean_listing_url(listing['url'])
    return result
