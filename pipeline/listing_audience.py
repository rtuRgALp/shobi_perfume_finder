"""Project Shobi's audience codes without changing original/provider identities."""
import copy
import re
from urllib.parse import unquote, urlparse
from .model import evidence

AUDIENCES = {'mp': 'masculine', 'wp': 'feminine', 'el': 'unisex'}


def listing_audience(url):
    path = unquote(urlparse(url).path).lower()
    suffix = re.search(r'-(mp|wp|el|n|lux)$', path)
    if suffix:
        # N and LUX are product lines, not audiences.
        return AUDIENCES.get(suffix[1])
    category = path.split('/')[-2] if '/' in path else ''
    return {'fragrances-for-men': 'masculine', 'fragrances-for-women': 'feminine',
            'elegants-fragrances': 'unisex'}.get(category)


def apply_listing_audiences(profiles):
    result = copy.deepcopy(profiles)
    for profile in result:
        audiences = {listing_audience(l['url']) for l in profile['listings']} - {None}
        if len(audiences) > 1:
            raise ValueError('Conflicting Shobi audiences require separate originals: ' + profile['id'])
        if audiences:
            audience = audiences.pop()
            if audience != profile['gender']:
                listing = next(l for l in profile['listings'] if listing_audience(l['url']))
                profile['gender'] = audience
                profile['evidence']['gender'] = evidence(listing['url'], 'verified', None,
                    'Shobi listing audience: MP=men, WP=women, EL=unisex. N and LUX identify lines only. '
                    'Original perfume audience remains in the maintained catalog for provider identity matching.')
    return result
