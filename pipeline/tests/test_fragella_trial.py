import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from pipeline.fragella_trial import MAX_REQUESTS, TrialClient, assess, candidates, load_key, run, sample
from pipeline.model import ROOT, read


class FragellaTrialTests(unittest.TestCase):
    def test_sample_includes_edition_and_identity_stress_cases(self):
        selected = sample(read(ROOT / 'data/catalog/profiles.json'))
        self.assertEqual(len(selected), 20)
        self.assertEqual(len({p['id'] for p in selected}), 20)
        self.assertEqual(sum(not p['fragranticaId'] for p in selected), 2)
        self.assertIn('46066', [p['fragranticaId'] for p in selected])
        self.assertIn('3865', [p['fragranticaId'] for p in selected])

    def test_supported_response_shapes_and_changed_layout(self):
        self.assertEqual(candidates([]), [])
        self.assertEqual(candidates({'data': [{'Name': 'Neroli'}]}), [{'Name': 'Neroli'}])
        for payload in ({'error': 'denied'}, {'data': {}}, ['wrong']):
            with self.assertRaises(ValueError):
                candidates(payload)

    def test_identity_conflicts_and_confidence_never_approve(self):
        profile = {'id': 'test', 'name': 'Neroli Eau de Parfum', 'brand': 'Example', 'fragranticaId': '42'}
        rows = [{'Name': 'Neroli EDP', 'Brand': 'Example', 'OilType': 'Eau de Toilette', 'Main Accords': ['woody'], 'Confidence': 'High'},
                {'Name': 'Neroli EDP', 'Brand': 'Other', 'OilType': 'Eau de Parfum'},
                {'Name': 'Neroli EDP', 'Brand': 'Example', 'OilType': 'Eau de Parfum', 'Main Accords': ['woody'], 'Confidence': 'High'}]
        report = assess(profile, rows, read(ROOT / 'contracts/boost-rules.v1.json'))
        self.assertTrue(report['candidates'][0]['concentrationConflict'])
        self.assertFalse(report['candidates'][1]['brandMatch'])
        self.assertEqual(report['candidates'][2]['identityHint'], 'name-and-brand-candidate')
        self.assertTrue(all(not row['approved'] for row in report['candidates']))
        self.assertEqual(report['candidates'][2]['accordProvenance'], 'unspecified-may-be-predicted')

    def test_cache_resume_and_persistent_budget(self):
        calls = []
        def opener(request, **kwargs):
            calls.append(request.full_url)
            self.assertNotIn('test-secret', request.full_url)
            return io.BytesIO(b'[{"Name":"Example"}]')
        with tempfile.TemporaryDirectory() as directory:
            client = TrialClient('test-secret', directory, opener)
            for i in range(MAX_REQUESTS):
                client.fetch(str(i))
            resumed = TrialClient('test-secret', directory, opener)
            self.assertTrue(resumed.fetch('0')[1])
            with self.assertRaisesRegex(ValueError, 'budget'):
                resumed.fetch('new-query')
            self.assertEqual(len(calls), 20)

    def test_http_failure_is_spent_and_not_retried(self):
        def opener(request, **kwargs):
            raise urllib.error.HTTPError(request.full_url, 429, 'key=secret', {}, None)
        with tempfile.TemporaryDirectory() as directory:
            client = TrialClient('secret', directory, opener)
            with self.assertRaisesRegex(ValueError, 'HTTP 429'):
                client.fetch('Neroli')
            resumed = TrialClient('secret', directory, opener)
            with self.assertRaisesRegex(ValueError, 'already attempted'):
                resumed.fetch('Neroli')
            self.assertEqual(len(resumed.ledger['attempts']), 1)
            self.assertNotIn('secret', (Path(directory) / 'requests.json').read_text())

    def test_credential_loading_and_redaction(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'FRAGELLA_API_KEY': ''}):
            env = Path(directory) / '.env.local'
            env.write_text('FRAGELLA_API_KEY="test-secret"\n')
            self.assertEqual(load_key(env), 'test-secret')
            client = TrialClient(load_key(env), directory, lambda *a, **k: io.BytesIO(b'[{"Name":"test-secret"}]'))
            payload, _ = client.fetch('Neroli')
            self.assertEqual(payload[0]['Name'], '[REDACTED]')
            env.write_text('FRAGELLA_API_KEY=pub_example\n')
            with self.assertRaises(ValueError):
                load_key(env)

    def test_dry_run_needs_no_key_or_network(self):
        with patch('pipeline.fragella_trial.load_key', side_effect=AssertionError('must not load key')), patch('builtins.print') as output:
            run(dry_run=True)
            self.assertEqual(json.loads(output.call_args.args[0])['networkRequests'], 0)


if __name__ == '__main__':
    unittest.main()
