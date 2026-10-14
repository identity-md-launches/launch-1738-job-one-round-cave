import unittest
from unittest.mock import patch
import proof_gas_cap as tool

class RealEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.bundle = tool.cap.binding.read_json('line-3/tools/code-routes/zto-proof.json')
        self.evidence = tool.cap.binding.read_json(tool.HERE / 'zto-evidence.json')
        self.request = tool.cap.binding.read_json(tool.HERE / 'zto-request.json')

    def test_real_different_block_is_withheld(self):
        r = tool.evaluate(self.bundle, self.evidence, self.request)
        self.assertFalse(r['context_aligned'])
        self.assertEqual(r['gas_cap_verdict'], 'matched')
        self.assertIsNone(r['joined_call'])
        self.assertFalse(r['transaction_approved'])

    def test_real_same_block_proof_joins(self):
        raw = tool.cap.binding.read_json(tool.HERE / 'zto-proof.json')
        r = tool.evaluate(raw, self.evidence, self.request)
        self.assertTrue(r['context_aligned'])
        self.assertEqual(r['status'], 'historical_context_joined')
        self.assertEqual(int(r['joined_call']['block']['number'], 16), 26190345)
        self.assertFalse(r['transaction_approved'])

    def test_tampered_runtime_is_not_a_proof(self):
        self.bundle['observation']['nodes'][0]['code'] = '0x6000'
        with self.assertRaises(ValueError):
            tool.evaluate(self.bundle, self.evidence, self.request)

    def test_changed_request_cannot_join(self):
        self.request['gas_limit'] = '30001'
        r = tool.evaluate(self.bundle, self.evidence, self.request)
        self.assertEqual(r['gas_cap_verdict'], 'request_mismatch')
        self.assertIsNone(r['joined_call'])

    def test_matching_context_is_not_enough_when_provider_failed(self):
        # Explicit simulation of aligned code context; no synthetic proof is saved.
        identity = tool.code.evaluate(self.bundle, [])
        identity['code_block'] = self.request['block']
        self.evidence['capped'] = {'error': {'code': -32000, 'message': 'test provider failure'}}
        with patch.object(tool.code, 'evaluate', return_value=identity):
            r = tool.evaluate(self.bundle, self.evidence, self.request)
        self.assertTrue(r['context_aligned'])
        self.assertEqual(r['gas_cap_verdict'], 'inconclusive')
        self.assertIsNone(r['joined_call'])

    def test_simulated_alignment_preserves_both_scopes(self):
        identity = tool.code.evaluate(self.bundle, [])
        identity['code_block'] = self.request['block']
        with patch.object(tool.code, 'evaluate', return_value=identity):
            r = tool.evaluate(self.bundle, self.evidence, self.request)
        self.assertEqual(r['status'], 'historical_context_joined')
        self.assertEqual(r['joined_call'], self.request)
        self.assertIn('scope', r['code_identity'])
        self.assertIn('limits', r['gas_cap_rehearsal'])
        self.assertFalse(r['transaction_approved'])

if __name__ == '__main__':
    unittest.main()
