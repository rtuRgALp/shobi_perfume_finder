import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline.model import DATA, ROOT, read, write, validate_profiles
from pipeline.release import build, rollback
from pipeline.sources import Client, SourceError, parse_fragrantica, parse_shobi
from pipeline.refresh import collect_listing_pages, hydrate, reconcile_listings, refresh

FIXTURES = Path(__file__).parent / 'fixtures'


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = read(DATA / 'catalog/profiles.json')

    def test_baseline_and_aliases(self):
        self.assertGreaterEqual(len(self.profiles), 2253)
        self.assertGreaterEqual(sum(p['validationStatus'] == 'green' for p in self.profiles), 2247)
        self.assertGreaterEqual(sum(p['validationStatus'] == 'yellow' for p in self.profiles), 6)
        self.assertGreaterEqual(sum(len(r['aliases']) for p in self.profiles for r in p['listings']), 25)
        validate_profiles(self.profiles)

    def test_ordered_notes_are_unchanged(self):
        source = ROOT / '_reference/MarvvRed/Shobi_Inspiration/database/catalog/database_final_perfume_only.json'
        if not source.exists():
            self.skipTest('Reference trees are deliberately not required by CI')
        originals = {r['code']: r for r in read(source)}
        corrections = {r['id']: r for r in read(ROOT / 'contracts/reviewed-source-corrections.v1.json')['mappings'] if r.get('withdrawnMainNotes')}
        for p in self.profiles:
            original = originals.get(p['listings'][0]['code'])
            if original:
                correction = corrections.get(p['id'])
                if correction and p['evidence']['identity']['note'] == correction['reason']:
                    self.assertEqual(correction['withdrawnMainNotes'], original['fragranticaSocialCardNotes'])
                    self.assertEqual(p['mainNotes'], [])
                    self.assertEqual(p['evidence']['mainNotes']['status'], 'conflicting')
                    continue
                self.assertEqual([n['name'] for n in p['mainNotes']], original['fragranticaSocialCardNotes'])

    def test_exact_source_parsing(self):
        p = {'name': 'Neroli', 'brand': 'Example', 'fragranticaId': '42'}
        fields = parse_fragrantica((FIXTURES / 'fragrantica.html').read_text(), p, 'https://www.fragrantica.com/p/42')
        self.assertEqual(fields['accords'], ['citrus', 'white floral'])
        self.assertEqual(fields['pyramid']['heart'], ['Neroli'])
        self.assertEqual(fields['rating'], {'value': 4.2, 'scale': '0–5', 'votes': 1250})
        self.assertNotIn('second', fields['description'])
        self.assertNotIn('longevity', fields)

    def test_identity_and_layout_conflicts(self):
        html = (FIXTURES / 'fragrantica.html').read_text()
        for p in [{'name': 'Neroli Intense', 'brand': 'Example', 'fragranticaId': '42'}, {'name': 'Neroli', 'brand': 'Example', 'fragranticaId': '43'}]:
            with self.assertRaises(SourceError):
                parse_fragrantica(html, p, 'https://www.fragrantica.com/p/42')
        with self.assertRaises(SourceError):
            parse_fragrantica('<html>Access denied</html>', {'name': 'Neroli', 'brand': 'Example', 'fragranticaId': '42'}, 'https://www.fragrantica.com/p/42')

    def test_current_source_markup(self):
        fields = parse_fragrantica((FIXTURES / 'fragrantica-modern.html').read_text(),
            {'name': 'Neroli', 'brand': 'Example', 'fragranticaId': '42'}, 'https://www.fragrantica.com/p/42')
        self.assertEqual(fields['accords'], ['citrus', 'white floral'])
        self.assertEqual(fields['pyramid']['top'], ['Neroli'])

    def test_shobi_pagination_and_empty_page(self):
        products, pages = parse_shobi((FIXTURES / 'shobi.html').read_text(), 'https://leparfum.com.gr/en/perfumes')
        self.assertEqual(products[0]['code'], '10-EX')
        self.assertEqual(len(pages), 2)
        with self.assertRaises(SourceError):
            parse_shobi('<html>Changed layout</html>', 'https://leparfum.com.gr/en/perfumes')

    def test_rank_order_follows_page_numbers_not_discovery_order(self):
        base = 'https://leparfum.com.gr/en/best-sales'
        pages = {base: ([{'id': '1'}], [base + '?page=10', base + '?page=2']),
            base + '?page=10': ([{'id': '10'}], []), base + '?page=2': ([{'id': '2'}], [])}
        class FakeClient:
            def get(self, url):
                return url, {}
        with patch('pipeline.refresh.parse_shobi', side_effect=lambda html, _: pages[html]):
            self.assertEqual([r['id'] for r in collect_listing_pages(FakeClient(), base)], ['1', '2', '10'])
            with self.assertRaises(SourceError):
                collect_listing_pages(FakeClient(), base, max_pages=1)

    def test_hydration_never_changes_certified_notes(self):
        p = self.profiles[0]
        updated = hydrate(p, {'accords': ['woody'], 'mainNotes': [{'name': 'Fake', 'icon': None}]}, {'source': 'https://www.fragrantica.com/p/42', 'retrievedAt': '2026-10-23'})
        self.assertEqual(updated['mainNotes'], p['mainNotes'])
        self.assertEqual(updated['evidence']['accords']['status'], 'verified')

    def test_source_failure_preserves_release(self):
        class FailedClient:
            failures = {}
            def get(self, url):
                raise SourceError('Offline')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / 'catalog/profiles.json', [self.profiles[0]])
            before = build([self.profiles[0]], public=root / 'public', data=root)
            report = refresh(limit=1, client=FailedClient(), data=root, public=root / 'public')
            self.assertEqual(report['hydrated'], 0)
            self.assertEqual(read(root / 'public/data/current.json'), before)

    def test_unresolved_profiles_do_not_starve_later_hydration(self):
        class FailedClient:
            failures = {}
            requested = []
            def get(self, url):
                if 'fragrantica.com' in url:
                    self.requested.append(url)
                raise SourceError('Needs review')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles = copy.deepcopy(self.profiles[:2])
            for p in profiles:
                p['evidence']['accords']['retrievedAt'] = None
            write(root / 'catalog/profiles.json', profiles)
            client = FailedClient()
            refresh(limit=1, client=client, data=root, public=root / 'public')
            refresh(limit=1, client=client, data=root, public=root / 'public')
            self.assertEqual(len(set(client.requested)), 2)

    def test_build_is_repeatable_and_invalid_release_cannot_replace_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles = [self.profiles[0]]
            first = build(profiles, public=root, data=root)
            first_bytes = (root / 'data/current.json').read_bytes()
            self.assertEqual(build(profiles, public=root, data=root), first)
            self.assertEqual(first_bytes, (root / 'data/current.json').read_bytes())
            clean = root / 'another-build'
            rebuilt = build(profiles, public=clean, data=root)
            self.assertEqual(rebuilt, first)
            self.assertEqual(first_bytes, (clean / 'data/current.json').read_bytes())
            invalid = copy.deepcopy(profiles)
            invalid[0]['validationStatus'] = 'red'
            with self.assertRaises(ValueError):
                build(invalid, public=root, data=root)
            self.assertEqual(first_bytes, (root / 'data/current.json').read_bytes())
            updated = copy.deepcopy(profiles)
            updated[0]['description'] = 'A sourced update.'
            second = build(updated, public=root, data=root)
            self.assertNotEqual(second['releaseId'], first['releaseId'])
            rollback(root)
            self.assertEqual(read(root / 'data/current.json'), first)

    def test_new_identity_requires_review(self):
        p = copy.deepcopy(self.profiles[:1]); review = []
        reconcile_listings(p, [{'id': '9999999', 'code': '99-NEW', 'url': 'https://leparfum.com.gr/en/new'}], review)
        self.assertEqual(len(p), 1)
        self.assertEqual(review[0]['kind'], 'unresolved-listing')

    def test_changed_declared_original_is_quarantined(self):
        profiles = copy.deepcopy(self.profiles[:1]); review = []
        listing = profiles[0]['listings'][0]
        previous = listing['url']
        reconcile_listings(profiles, [{'id': listing['id'], 'code': listing['code'],
            'url': 'https://leparfum.com.gr/en/changed', 'declaredOriginal': 'An unrelated perfume'}], review)
        self.assertEqual(review[0]['kind'], 'listing-identity-conflict')
        self.assertEqual(listing['url'], previous)

    def test_scope_and_certification_gate(self):
        p = copy.deepcopy(self.profiles[:1])
        p[0]['listings'][0]['aliases'].append('130-LEL')
        with self.assertRaisesRegex(ValueError, 'Excluded'):
            validate_profiles(p)
        p = copy.deepcopy(self.profiles[:1])
        p[0]['validationStatus'] = 'green'
        p[0]['validationChecks']['notes'] = False
        with self.assertRaisesRegex(ValueError, 'full inherited validation chain'):
            validate_profiles(p)

    def test_client_rejects_other_hosts_and_has_circuit_breaker(self):
        client = Client(Path('/tmp/shobi-test-unused'))
        with self.assertRaises(SourceError):
            client.get('https://example.com')
        client.failures['www.fragrantica.com'] = 3
        with self.assertRaisesRegex(SourceError, 'circuit open'):
            client.get('https://www.fragrantica.com/p/42')


if __name__ == '__main__':
    unittest.main()
