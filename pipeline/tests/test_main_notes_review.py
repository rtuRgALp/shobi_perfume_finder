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
