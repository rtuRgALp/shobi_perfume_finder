import copy
import unittest
from pipeline.listing_audience import apply_listing_audiences, listing_audience
from pipeline.model import DATA, read
from pipeline.fragella_resolve import resolve


class ListingAudienceTests(unittest.TestCase):
    def test_codes_and_lines(self):
        for code, expected in [('mp','masculine'),('wp','feminine'),('el','unisex'),('n',None),('lux',None)]:
            self.assertEqual(listing_audience('https://leparfum.com.gr/en/niche-perfumes/100-x-' + code), expected)
        self.assertIsNone(listing_audience('https://leparfum.com.gr/en/luxury-perfumes/100-x'))

    def test_public_audience_preserves_provider_input(self):
        profiles = read(DATA / 'catalog/profiles.json')
        before = copy.deepcopy(profiles)
        public = apply_listing_audiences(profiles)
        self.assertEqual(profiles, before)
        for p in public:
            for l in p['listings']:
                expected = listing_audience(l['url'])
                if expected:
                    self.assertEqual(p['gender'], expected)

    def test_mixed_audiences_cannot_be_remerged(self):
        p = copy.deepcopy(read(DATA / 'catalog/profiles.json')[0])
        p['listings'] = [dict(p['listings'][0], url='https://leparfum.com.gr/en/x/one-mp'),
                         dict(p['listings'][0], url='https://leparfum.com.gr/en/x/one-wp')]
        with self.assertRaises(ValueError):
            apply_listing_audiences([p])

    def test_the_one_is_two_distinct_identities(self):
        profiles = read(DATA / 'catalog/profiles.json')
        codes = {l['code']: p for p in profiles for l in p['listings']}
        men, women = codes['1099-DOL'], codes['566-DOL']
        self.assertEqual((men['fragranticaId'], men['gender']), ('2056','masculine'))
        self.assertEqual((women['fragranticaId'], women['gender']), ('698','feminine'))
        self.assertNotEqual(men['image'], women['image'])
        self.assertEqual([n['name'] for n in men['mainNotes']],
                         ['Amber', 'Tobacco', 'Ginger', 'Cardamom', 'Grapefruit', 'Cedar'])
        self.assertEqual(men['evidence']['mainNotes']['status'], 'verified')
        self.assertIn('Tobacco', men['pyramid']['base'])
        self.assertNotIn('566-DOL', men['listings'][0]['aliases'])
        self.assertEqual(men['evidence']['accords']['status'], 'provider')

    def test_reviewed_retailer_mapping_still_rejects_wrong_identity(self):
        p = next(p for p in read(DATA / 'catalog/profiles.json') if p['id']=='shobi-191')
        row = {'_id':'The-One','Name':'The One','Brand':'Dolce & Gabbana','Gender':'men',
               'Main Accords':['amber','tobacco','aromatic','citrus']}
        def accepted(r):
            return resolve([p], {'The-One': {'profile':r,'retrievedAt':'2026-11-02'}})[0]
        self.assertIn(p['id'], accepted(row))
        for key, value in [('Name','The One Royal Night'),('Gender','women'),('Main Accords',['floral'])]:
            self.assertNotIn(p['id'], accepted(dict(row, **{key:value})))
