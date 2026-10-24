import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from pipeline.fragella_snapshot import SnapshotClient, canonical_name, search_parameters


class SnapshotTests(unittest.TestCase):
    def test_canonical_spelling_and_short_queries(self):
        p = {'name': 'Avent', 'brand': 'Creed', 'fragranticaUrl': 'https://www.fragrantica.com/perfume/Creed/Aventus-9828.html'}
        self.assertEqual(canonical_name(p), 'Aventus')
        self.assertEqual(search_parameters(p)['search'], 'Aventus')
        self.assertEqual(search_parameters({'name': 'X', 'brand': 'Example'})['brand'], 'Example')

    def test_cache_resume_budget_and_key_not_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            calls = []
            def opener(request, **kwargs):
                calls.append(request.full_url)
                return io.BytesIO(b'{"data": [{"Name":"Neroli"}]}')
            c = SnapshotClient('trial-secret', temp, budget=1, interval=0, opener=opener)
            c.fetch({'search': 'Neroli'})
            resumed = SnapshotClient('trial-secret', temp, budget=1, interval=0, opener=opener)
            self.assertTrue(resumed.fetch({'search': 'Neroli'})[1])
            with self.assertRaisesRegex(ValueError, 'budget'):
                resumed.fetch({'search': 'Amber'})
            self.assertEqual(len(calls), 1)
            self.assertNotIn('trial-secret', (Path(temp) / 'requests.jsonl').read_text())

    def test_quota_error_stops_without_retries(self):
        with tempfile.TemporaryDirectory() as temp:
            def opener(request, **kwargs):
                raise urllib.error.HTTPError(request.full_url, 429, 'quota', {}, None)
            client = SnapshotClient('secret', temp, interval=0, opener=opener)
            with self.assertRaisesRegex(ValueError, '429'):
                client.fetch({'search': 'Neroli'})
            with self.assertRaisesRegex(ValueError, 'stopped'):
                client.fetch({'search': 'Amber'})
            self.assertEqual(len(client.attempts), 1)
