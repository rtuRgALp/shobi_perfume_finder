import copy
import tempfile
import unittest
from pathlib import Path
from pipeline.model import DATA, read, write
from pipeline.sources import SourceError
from pipeline.web_recovery import heading_matches, parse_page, recover, reviewed_corrections, split_pages


class WebRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.profile = copy.deepcopy(read(DATA / 'catalog/profiles.json')[0])
        self.profile.update(name='Neroli', brand='Example', fragranticaId='42', fragranticaUrl='https://www.fragrantica.com/perfume/Example/Neroli-42.html', nameAliases=[])
        self.profile['accords'] = []
        self.profile['description'] = None
        self.profile['rating'] = None
        self.profile['pyramid'] = {'top': [], 'heart': [], 'base': []}
        self.url = self.profile['fragranticaUrl']
        self.page = '''Crawled: today; Source: open({"ref_id":"original"})
L64: # Neroli Example for women and men
L69: ###### main accords
L70:
L71: citrus
L72:
L73: white floral
L74: 【26†Search by accords】
L90: Perfume rating 4.2 out of 5 with 1,234 votes
L95: Neroli by Example is a Citrus Floral fragrance for women and men. Neroli was launched in 2020.
L100: Fragrance Composition
L105: #### Top Notes
L107: 【50†Bergamot】 【51†Neroli】
L109: #### Middle Notes
L111: 【52†Jasmine】
L113: #### Base Notes
L115: 【53†Musk】
L116: ### Designer Example
'''

    def test_explicit_fields_retain_order_and_original_scale(self):
        fields = parse_page(self.page, self.profile, self.url)
        self.assertEqual(fields['accords'], ['citrus', 'white floral'])
        self.assertEqual(fields['rating'], {'value': 4.2, 'scale': '0–5', 'votes': 1234})
        self.assertEqual(fields['pyramid']['top'], ['Bergamot', 'Neroli'])
        self.assertEqual(fields['description'], 'A citrus floral fragrance for women and men. Introduced in 2020.')
        self.assertNotIn('mainNotes', fields)

    def test_missing_sections_wrong_original_and_wrong_edition_fail_closed(self):
        for page, url in [(self.page.replace('# Neroli Example', '# Neroli Intense Example'), self.url),
                          (self.page, self.url.replace('-42.html', '-43.html'))]:
            with self.assertRaises(SourceError):
                parse_page(page, self.profile, url)
        fields = parse_page(self.page.split('L90:')[0], self.profile, self.url)
        self.assertEqual(fields, {'accords': ['citrus', 'white floral']})

    def test_missing_accord_section_does_not_block_other_fields(self):
        fields = parse_page(self.page.replace('###### main accords', '###### unavailable'), self.profile, self.url)
        self.assertNotIn('accords', fields)
        self.assertEqual(fields['pyramid']['base'], ['Musk'])
        self.assertEqual(fields['rating']['scale'], '0–5')

    def test_existing_accords_do_not_block_pyramid_and_receipts_complement_each_other(self):
        self.profile['accords'] = ['woody']
        self.profile['rating'] = {'value': 3.9, 'scale': '0–5', 'votes': 10}
        newer = self.page.split('L100:')[0]
        older = self.page.replace('###### main accords', '###### unavailable')
        with tempfile.TemporaryDirectory() as temp:
            for filename, page, date in [('new.json', newer, '2026-10-24T01:00:00Z'), ('old.json', older, '2026-10-24T00:00:00Z')]:
                write(Path(temp) / filename, {'retrievedAt': date, 'raw': 'Neroli (' + self.url + ')\n' + page})
            profiles, report = recover([self.profile], Path(temp))
            p = profiles[0]
            self.assertEqual(p['accords'], ['woody'])
            self.assertEqual(p['rating'], self.profile['rating'])
            self.assertEqual(p['pyramid']['heart'], ['Jasmine'])
            self.assertEqual(p['mainNotes'], self.profile['mainNotes'])
            self.assertEqual(report['missingByField']['pyramid'], 0)
            repeated, second = recover(profiles, Path(temp))
            self.assertEqual(repeated, profiles)
            self.assertEqual(second['imported'], [])

    def test_review_note_headings_are_not_pyramid_evidence(self):
        page = self.page.split('L100:')[0] + '\n### Designer Example\n#### Top Notes\n【99†Invented in a review】'
        self.assertNotIn('pyramid', parse_page(page, self.profile, self.url))

    def test_partial_pyramid_is_completed_only_when_retained_layers_agree(self):
        self.profile['pyramid']['top'] = ['Bergamot', 'Neroli']
        with tempfile.TemporaryDirectory() as temp:
            write(Path(temp) / 'page.json', {'retrievedAt': '2026-10-24T00:00:00Z', 'raw': 'Neroli (' + self.url + ')\n' + self.page})
            profiles, report = recover([self.profile], Path(temp))
            self.assertEqual(profiles[0]['pyramid']['heart'], ['Jasmine'])
            self.assertEqual(report['missingByField']['pyramid'], 0)
            self.profile['pyramid']['top'] = ['Rose']
            profiles, report = recover([self.profile], Path(temp))
            self.assertEqual(profiles[0]['pyramid'], self.profile['pyramid'])
            self.assertEqual(report['missingByField']['pyramid'], 1)
            self.assertEqual(report['missingPyramidLayers']['heart'], 1)

    def test_audience_suffix_does_not_erase_a_named_mens_edition(self):
        self.profile.update(name='Neroli for Men', fragranticaUrl='https://www.fragrantica.com/perfume/Example/Neroli-for-Men-42.html')
        self.assertTrue(heading_matches('Neroli for Men Example for men', self.profile))
        self.assertFalse(heading_matches('Neroli Example for women', self.profile))

    def test_receipt_is_source_bound_and_preserves_main_notes_and_known_values(self):
        raw = 'Neroli perfume (' + self.url + ')\n' + self.page
        self.assertEqual(len(list(split_pages(raw))), 1)
        old_notes = copy.deepcopy(self.profile['mainNotes'])
        with tempfile.TemporaryDirectory() as temp:
            write(Path(temp) / 'receipt.json', {'retrievedAt': '2026-10-24T00:00:00Z', 'raw': raw})
            profiles, report = recover([self.profile], Path(temp))
            self.assertEqual(len(report['imported']), 1)
            self.assertEqual(profiles[0]['mainNotes'], old_notes)
            self.assertEqual(profiles[0]['evidence']['accords']['status'], 'verified')
            repeated, report = recover(profiles, Path(temp))
            self.assertEqual(repeated, profiles)
            self.assertEqual(report['imported'], [])

    def test_reviewed_heading_is_pinned_to_identity_and_exact_heading(self):
        from pipeline.model import ROOT
        item = read(ROOT / 'contracts/public-source-headings.v1.json')['mappings'][0]
        profile = dict(item, fragranticaUrl=None, nameAliases=[])
        self.assertTrue(heading_matches(item['heading'], profile))
        self.assertFalse(heading_matches(item['heading'] + ' Intense', profile))
        profile['fragranticaId'] = '999999'
        self.assertFalse(heading_matches(item['heading'], profile))

    def test_reviewed_identity_correction_withdraws_wrong_notes_without_substitution(self):
        from pipeline.model import ROOT
        baseline = copy.deepcopy(self.profile)
        rule = read(ROOT / 'contracts/reviewed-source-corrections.v1.json')['mappings'][0]
        baseline.update(rule['expected'], id=rule['id'], mainNotes=[{'name': n, 'icon': None} for n in rule['withdrawnMainNotes']])
        for listing in baseline['listings']:
            listing['originalId'] = baseline['id']
        fixed = reviewed_corrections([baseline])[0]
        self.assertEqual(fixed['fragranticaId'], '721')
        self.assertEqual(fixed['mainNotes'], [])
        self.assertIsNone(fixed['image'])
        self.assertEqual(fixed['evidence']['mainNotes']['status'], 'conflicting')
        self.assertEqual(fixed['evidence']['accords']['status'], 'verified')
        self.assertEqual(reviewed_corrections([fixed]), [fixed])
        baseline['brand'] = 'Kenzo'
        with self.assertRaises(SourceError):
            reviewed_corrections([baseline])
