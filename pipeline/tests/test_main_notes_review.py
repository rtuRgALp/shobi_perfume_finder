import unittest
from pipeline.model import ROOT, DATA, read


class MainNotesReviewTests(unittest.TestCase):
    def test_reviewed_cards_match_published_identity_order_and_assets(self):
        profiles = {p['id']: p for p in read(DATA / 'catalog/profiles.json')}
        for review in read(ROOT / 'contracts/reviewed-main-notes.v1.json')['reviews']:
            with self.subTest(id=review['id']):
                profile = profiles[review['id']]
                self.assertEqual(profile['fragranticaId'], review['fragranticaId'])
                self.assertEqual(profile['mainNotes'], review['notes'])
                self.assertEqual(profile['evidence']['mainNotes']['source'], review['source'])
                self.assertEqual(profile['evidence']['mainNotes']['status'], 'verified')
                self.assertEqual(len(review['sha256']), 64)
                for note in profile['mainNotes']:
                    self.assertTrue((ROOT / 'public' / note['icon']).is_file())

    def test_all_profiles_have_notes_and_source_exceptions_remain_distinct(self):
        profiles = {p['id']: p for p in read(DATA / 'catalog/profiles.json')}
        self.assertTrue(all(p['mainNotes'] for p in profiles.values()))
        expected = {
            'shobi-5083': ['Passionfruit', 'Peach', 'Green Pear', 'Lily', 'Sandalwood', 'Vanilla'],
            'shobi-3455': ['Neroli', 'Tuberose', 'Jasmine', 'Sandalwood', 'Musk'],
            'shobi-1409': ['Agarwood (Oud)'],
            'shobi-1220': ['Oak', 'Red Cedar'],
            'shobi-1143': ['Tangerine', 'Pink Magnolia'],
            'shobi-328': ['Citron', 'Lavender', 'Orchid', 'Nutmeg', 'Basil', 'Allspice', 'Oakmoss', 'Amber', 'Patchouli'],
        }
        reviews = {r['id']: r for r in read(ROOT / 'contracts/reviewed-main-notes.v1.json')['reviews'] if r.get('kind') == 'source-notes'}
        self.assertEqual(set(reviews), set(expected))
        for pid, names in expected.items():
            self.assertEqual([n['name'] for n in profiles[pid]['mainNotes']], names)
            self.assertIn('not ordered Social Card certification', profiles[pid]['evidence']['mainNotes']['note'])
            self.assertTrue(reviews[pid]['sourceIdentity'])
