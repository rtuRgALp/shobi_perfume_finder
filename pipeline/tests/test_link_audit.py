import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.link_audit import Auditor, audit_scope, inspect_product, normalize_url
from pipeline.listing_urls import clean_listing_urls
from pipeline.model import DATA, ROOT, read
from pipeline.release import build


class LinkAuditTests(unittest.TestCase):
    def test_unicode_canonical_is_equivalent_to_encoded_catalog_url(self):
        self.assertEqual(normalize_url('https://leparfum.com.gr/en/Ночная'),
            normalize_url('https://leparfum.com.gr/en/%D0%9D%D0%BE%D1%87%D0%BD%D0%B0%D1%8F'))

    def test_scope_includes_partial_designer_names_and_all_descriptive_urls(self):
        profile = {'id': 'shobi-1', 'brand': 'Abercrombie & Fitch', 'name': 'First Instinct',
            'listings': [{'id': '1', 'code': '999-ABE', 'url': 'https://leparfum.com.gr/en/men/first-instinct-abercrombie-type'}]}
        self.assertTrue(audit_scope([profile])[0]['designerInUrl'])
        profile['listings'][0]['url'] = 'https://leparfum.com.gr/en/men/first-instinct-type'
        self.assertFalse(audit_scope([profile])[0]['designerInUrl'])
        profile['listings'][0]['url'] = 'https://leparfum.com.gr/en/men/999-abe-mp'
        self.assertEqual(audit_scope([profile]), [])

    def test_http_success_is_not_enough_without_exact_product_identity(self):
        html = '<h1>999-ABE MP</h1><input name="id_product" value="1895"><link rel="canonical" href="https://leparfum.com.gr/en/men/first-instinct-type">'
        self.assertTrue(inspect_product(html, '1895', '999-ABE')['identityMatches'])
        self.assertTrue(inspect_product(html.replace('999-ABE', '999 - ABE'), '1895', '999-ABE')['identityMatches'])
        self.assertFalse(inspect_product(html, '1896', '999-ABE')['identityMatches'])
        self.assertFalse(inspect_product(html, '1895', '99-ABE')['identityMatches'])
        self.assertFalse(inspect_product('<h1>Page not found</h1>', '1895', '999-ABE')['identityMatches'])

    def test_recovery_requires_direct_replacement_verification(self):
        auditor = Auditor(None, interval=0)
        row = {'id': 'shobi-1', 'listingId': '1', 'code': '1-ABC', 'url': 'https://leparfum.com.gr/en/old'}
        candidate = 'https://leparfum.com.gr/en/new'
        with patch.object(auditor, 'fetch', side_effect=[{'httpStatus': 404},
                {'identityMatches': True, 'canonical': candidate}, {'identityMatches': True}]):
            self.assertEqual(auditor.check(row)['correctedUrl'], candidate)
        with patch.object(auditor, 'fetch', side_effect=[{'httpStatus': 404},
                {'identityMatches': True, 'canonical': candidate}, {'identityMatches': False}]):
            self.assertEqual(auditor.check(row)['status'], 'unresolved')
        with patch.object(auditor, 'fetch', side_effect=[{'httpStatus': 404},
                {'identityMatches': True, 'canonical': 'https://example.com/en/new'}]):
            self.assertEqual(auditor.check(row)['status'], 'unresolved')

    def test_reviewed_corrections_are_pinned_to_original_listing_code_and_old_url(self):
        profiles = {p['id']: p for p in read(DATA / 'catalog/profiles.json')}
        rules = read(ROOT / 'contracts/listing-url-corrections.v1.json')['mappings']
        self.assertTrue(rules)
        for rule in rules:
            with self.subTest(id=rule['id']):
                legacy = copy.deepcopy(profiles[rule['id']])
                listing = next(l for l in legacy['listings'] if l['id'] == rule['listingId'])
                listing['url'] = rule['previousUrl'] + '#/2-bottle-50ml'
                fixed = clean_listing_urls([legacy])[0]
                self.assertEqual(next(l for l in fixed['listings'] if l['id'] == rule['listingId'])['url'], rule['url'])
                self.assertEqual(clean_listing_urls([fixed]), [fixed])
                for field, value in [('id', 'other-original'), ('code', 'other-code'), ('url', 'https://leparfum.com.gr/en/newer')]:
                    mismatch = copy.deepcopy(legacy)
                    target = next(l for l in mismatch['listings'] if l['id'] == rule['listingId'])
                    if field == 'id':
                        mismatch['id'] = value
                    else:
                        target[field] = value
                    corrected = clean_listing_urls([mismatch])[0]
                    self.assertEqual(corrected['listings'][0]['url'], mismatch['listings'][0]['url'].split('#')[0])

    def test_release_reapplies_reviewed_url_after_legacy_import(self):
        rule = next(r for r in read(ROOT / 'contracts/listing-url-corrections.v1.json')['mappings'] if r['id'] == 'shobi-1895')
        profile = copy.deepcopy(next(p for p in read(DATA / 'catalog/profiles.json') if p['id'] == rule['id']))
        profile['listings'][0]['url'] = rule['previousUrl']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = build([profile], public=root, data=root)
            published = read(root / manifest['basePath'] / 'profiles' / (rule['id'] + '.json'))
            self.assertEqual(published['listings'][0]['url'], rule['url'])
            self.assertEqual(profile['listings'][0]['url'], rule['previousUrl'])

