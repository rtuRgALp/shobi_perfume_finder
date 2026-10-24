import copy
import unittest

from pipeline.fragella_resolve import enrich, evaluate, provider_fields, resolve, provider_brand
from pipeline.model import DATA, read, validate_profiles


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.profile = copy.deepcopy(read(DATA / 'catalog/profiles.json')[0])
        self.profile.update(name='Neroli Eau de Parfum', brand='Example', gender='unisex',
                            fragranticaUrl='https://www.fragrantica.com/perfume/Example/Neroli-Eau-de-Parfum-42.html', fragranticaId='42')
        self.profile['mainNotes'] = [{'name': name, 'icon': None} for name in ['Bergamot', 'Neroli', 'Amber']]
        self.row = {'_id': 'neroli-edp', 'Name': 'Neroli Eau de Parfum unisex', 'Brand': 'Example', 'Gender': 'unisex',
                    'Year': '2020', 'OilType': 'Eau de Parfum', 'Confidence': 'high', 'General Notes': ['Bergamot', 'Neroli', 'Amber'],
                    'Main Accords': ['citrus', 'amber'], 'Notes': {'Top': [{'name': 'Bergamot'}], 'Base': ['Amber']},
                    'rating': '4.2', 'Longevity': 'Long Lasting', 'Sillage': 'Strong'}
        self.item = {'profile': self.row, 'retrievedAt': '2026-10-24T00:00:00+00:00', 'source': 'https://api.fragella.com/docs.html'}

    def test_exact_identity_and_independent_notes_required(self):
        self.assertEqual(evaluate(self.profile, self.row)[0], [])
        for field, value, reason in [('Name', 'Neroli Intense', 'name-or-edition-mismatch'), ('Brand', 'Other', 'brand-mismatch'),
                                     ('OilType', 'Eau de Toilette', 'concentration-conflict'), ('Gender', 'women', 'gender-conflict'),
                                     ('General Notes', [], 'insufficient-note-corroboration')]:
            row = copy.deepcopy(self.row)
            row[field] = value
            if field == 'General Notes':
                row['Notes'] = {}
            self.assertIn(reason, evaluate(self.profile, row)[0])

    def test_le_parfum_name_does_not_invent_a_concentration(self):
        self.profile.update(name='Neroli Le Parfum', fragranticaUrl='https://www.fragrantica.com/perfume/Example/Neroli-Le-Parfum-42.html')
        self.row.update(Name='Neroli Le Parfum', OilType='Eau de Parfum')
        self.assertEqual(evaluate(self.profile, self.row)[0], [])

    def test_truncated_house_correction_requires_the_full_house_in_name(self):
        self.assertEqual(provider_brand({'Brand': 'Maison Francis', 'Name': 'Maison Francis Kurkdjian Baccarat Rouge 540'}), 'Maison Francis Kurkdjian')
        self.assertEqual(provider_brand({'Brand': 'Maison Francis', 'Name': 'Baccarat Rouge 540'}), 'Maison Francis')

    def test_reviewed_regional_note_names_corroborate_without_altering_notes(self):
        self.profile['mainNotes'] = [{'name': 'Bergamot', 'icon': None}, {'name': 'Vetiver', 'icon': None}]
        self.row.update({'General Notes': ['Calabrian Bergamot', 'Haitian Vetiver'], 'Notes': {}})
        self.assertEqual(evaluate(self.profile, self.row)[0], [])
        self.assertEqual([n['name'] for n in self.profile['mainNotes']], ['Bergamot', 'Vetiver'])

    def test_decorative_house_suffix_preserves_exact_perfume_name(self):
        self.row['Name'] = 'Neroli Eau de Parfum Example unisex'
        self.assertEqual(evaluate(self.profile, self.row)[0], [])
        self.row['Name'] = 'Neroli Intense Eau de Parfum Example unisex'
        self.assertIn('name-or-edition-mismatch', evaluate(self.profile, self.row)[0])

    def test_url_ampersand_formatting_does_not_erase_edition_words(self):
        self.profile.update(name='Neroli Amber', fragranticaUrl='https://www.fragrantica.com/perfume/Example/Neroli-Amber-42.html')
        self.row.update(Name='Neroli & Amber')
        self.assertEqual(evaluate(self.profile, self.row)[0], [])
        self.row['Name'] = 'Neroli & Amber Intense'
        self.assertIn('name-or-edition-mismatch', evaluate(self.profile, self.row)[0])

    def test_conflicting_duplicate_ids_are_quarantined(self):
        other = copy.deepcopy(self.item)
        other['profile'].update(_id='other-id', Year='2021')
        mappings, reviews = resolve([self.profile], {'a': self.item, 'b': other})
        self.assertEqual(mappings, {})
        self.assertIn('contradictory-duplicate-identities', reviews[0]['reasons'][0]['reasons'])

    def test_known_contradictory_provider_record_is_never_selected(self):
        self.row['_id'] = 'Bleu-De-Chanel'
        self.assertEqual(resolve([self.profile], {'a': self.item})[0], {})

    def test_one_provider_id_cannot_silently_merge_distinct_originals(self):
        second = copy.deepcopy(self.profile)
        second.update(id='shobi-9999', fragranticaId='43', fragranticaUrl='https://www.fragrantica.com/perfume/Example/Neroli-Eau-de-Parfum-43.html')
        mappings, reviews = resolve([self.profile, second], {'a': self.item})
        self.assertEqual(mappings, {})
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0]['reasons'][0]['reasons'], ['provider-id-shared-by-distinct-originals'])

    def test_audited_audience_exception_cannot_override_edition_or_source_id(self):
        self.row['Gender'] = 'women'
        reviewed = {self.profile['id']: {'fragranticaId': '42', 'providerId': 'neroli-edp', 'reason': 'Exact identity reviewed; retain inherited audience.'}}
        mappings, _ = resolve([self.profile], {'a': self.item}, reviewed)
        self.assertIn(self.profile['id'], mappings)
        self.row['OilType'] = 'Eau de Toilette'
        self.assertEqual(resolve([self.profile], {'a': self.item}, reviewed)[0], {})
        self.row['OilType'] = 'Eau de Parfum'
        reviewed[self.profile['id']]['fragranticaId'] = 'different-original'
        self.assertEqual(resolve([self.profile], {'a': self.item}, reviewed)[0], {})

    def test_estimates_have_distinct_evidence_and_keep_descriptive_scales(self):
        for field in ('accords', 'rating', 'longevity', 'sillage'):
            self.profile[field] = [] if field == 'accords' else None
        self.profile['pyramid'] = {'top': [], 'heart': [], 'base': []}
        original = copy.deepcopy(self.profile)
        updated = enrich(self.profile, self.item)
        self.assertEqual(updated['longevity'], {'label': 'Long Lasting', 'scale': 'Fragella descriptive assessment', 'votes': None})
        self.assertEqual(updated['evidence']['accords']['status'], 'provider')
        self.assertIn('model estimates', updated['evidence']['accords']['note'])
        self.assertEqual(updated['mainNotes'], original['mainNotes'])
        self.assertEqual(updated['validationChecks'], original['validationChecks'])
        self.assertEqual(updated['name'], original['name'])
        self.assertEqual(updated['pyramid']['top'], ['Bergamot'])
        validate_profiles([updated])

    def test_known_values_survive_different_provider_values(self):
        self.profile['accords'] = ['woody']
        self.profile['evidence']['accords']['status'] = 'verified'
        self.profile['description'] = 'Previously sourced description.'
        updated = enrich(self.profile, self.item)
        self.assertEqual(updated['accords'], ['woody'])
        self.assertEqual(updated['evidence']['accords']['status'], 'verified')
        self.assertEqual(updated['description'], self.profile['description'])

    def test_incomplete_or_invalid_optional_fields_do_not_invent_data(self):
        self.assertEqual(provider_fields({'rating': 'unknown', 'Longevity': 'N/A', 'Notes': {'Top': None}}), {})
        self.assertEqual(provider_fields({'rating': '6'}), {})
