import copy
import tempfile
import unittest
from pathlib import Path

from pipeline.display_names import restore_display_names
from pipeline.listing_urls import clean_listing_url, clean_listing_urls
from pipeline.model import DATA, ROOT, read
from pipeline.release import build
from pipeline.sources import parse_shobi


class CatalogPresentationTests(unittest.TestCase):
    def test_reviewed_names_restore_from_legacy_inputs_without_changing_other_fields(self):
        profiles = {p['id']: p for p in read(DATA / 'catalog/profiles.json')}
        for rule in read(ROOT / 'contracts/display-name-corrections.v1.json')['mappings']:
            with self.subTest(id=rule['id']):
                legacy = copy.deepcopy(profiles[rule['id']])
                legacy['name'] = rule['previousName']
                fixed = restore_display_names([legacy])[0]
                self.assertEqual(fixed['name'], rule['name'])
                self.assertIn(rule['previousName'], fixed['nameAliases'])
                self.assertEqual(restore_display_names([fixed]), [fixed])
                for key in legacy.keys() - {'name', 'nameAliases'}:
                    self.assertEqual(fixed[key], legacy[key])
                for key, value in [('brand', 'Unrelated'), ('fragranticaId', '0'), ('name', 'Unrelated')]:
                    mismatch = copy.deepcopy(legacy)
                    mismatch[key] = value
                    self.assertEqual(restore_display_names([mismatch]), [mismatch])

    def test_clean_links_preserve_product_paths_and_queries(self):
        url = 'https://leparfum.com.gr/en/niche/1508-kil?language=en'
        self.assertEqual(clean_listing_url(url + '#/1-choose-eau_de_parfum/2-bottle-50ml/3-extra_essence-3ml'), url)
        self.assertEqual(clean_listing_url(url), url)
        profile = copy.deepcopy(read(DATA / 'catalog/profiles.json')[0])
        profile['listings'].append(copy.deepcopy(profile['listings'][0]))
        for listing in profile['listings']:
            listing['url'] = url + '#/2-bottle-50ml'
        fixed = clean_listing_urls([profile])
        self.assertTrue(all(l['url'] == url for l in fixed[0]['listings']))
        self.assertIn('#', profile['listings'][0]['url'])
        self.assertEqual(clean_listing_urls(fixed), fixed)

    def test_imported_shobi_links_drop_product_options(self):
        fixture = Path(__file__).parent / 'fixtures/shobi.html'
        html = fixture.read_text().replace('/10-ex"', '/10-ex#/2-bottle-50ml/3-extra_essence-3ml"')
        rows, _ = parse_shobi(html, 'https://leparfum.com.gr/en/perfumes')
        self.assertEqual(rows[0]['url'], 'https://leparfum.com.gr/en/fragrances-for-men/10-ex')

    def test_build_repairs_legacy_names_and_links_in_published_profiles_and_index(self):
        profile = copy.deepcopy(next(p for p in read(DATA / 'catalog/profiles.json') if p['id'] == 'shobi-2266'))
        profile['name'] = 'Angels Share'
        profile['listings'][0]['url'] += '#/2-bottle-50ml/3-extra_essence-3ml'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = build([profile], public=root, data=root)
            release = root / manifest['basePath']
            published = read(release / 'profiles/shobi-2266.json')
            self.assertEqual(published['name'], "Angels' Share")
            self.assertNotIn('#', published['listings'][0]['url'])
            self.assertEqual(read(release / 'index.json')['perfumes'][0]['name'], published['name'])
            self.assertEqual(profile['name'], 'Angels Share')

