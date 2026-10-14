import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import code_frontier_review as tool

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zto = tool.read_json(TOOLS / 'code-routes/zto-proof.json')
        cls.imd = tool.read_json(TOOLS / 'code-routes/imd-proof.json')
        cls.imd_target = tool.read_json(TOOLS / 'code-target-proofs/imd-target-proof.json')
        cls.zto_review = tool.read_json(HERE / 'zto-example-review.json')
        cls.imd_review = tool.read_json(HERE / 'imd-example-review.json')
        cls.height = 26188209

    def test_real_zto_refuses_without_independent_anchor(self):
        result = tool.evaluate(self.zto, [], self.zto_review, self.height)
        self.assertEqual(result['reasons'], ['missing-caller-anchor'])
        self.assertTrue(result['raw_proofs_reverified'])
        self.assertFalse(result['anchor_authenticity_verified'])

    def test_matching_hash_argument_exercises_acceptance_logic_only(self):
        # The hash copied from evidence checks equality, not independent trust.
        result = tool.evaluate(self.zto, [], self.zto_review, self.height,
                               self.zto['observation']['block']['hash'])
        self.assertEqual(result['decision'], 'accept-bounded-code-identities')
        self.assertFalse(result['dependency_completeness_verified'])

    def test_age_is_measured_from_code_evidence(self):
        result = tool.evaluate(self.zto, [], self.zto_review, self.height + 1)
        self.assertIn('code-evidence-too-old', result['reasons'])
        with self.assertRaisesRegex(ValueError, 'precedes'):
            tool.evaluate(self.zto, [], self.zto_review, self.height - 1)

    def test_reviewed_hash_and_set_are_exact(self):
        altered = copy.deepcopy(self.zto_review)
        altered['runtimes'][0]['code_hash'] = '0x' + '11' * 32
        result = tool.evaluate(self.zto, [], altered, self.height)
        self.assertEqual(result['mismatched_runtime_hashes'][0]['address'],
                         self.zto_review['source_target'])
        self.assertIn('reviewed-runtime-set-or-hash-mismatch', result['reasons'])
        result = tool.evaluate(self.imd, [], self.imd_review, self.height)
        self.assertEqual(result['missing_reviewed_runtimes'],
                         ['0x1a44076050125825900e736c501f859c50fe728c'])
        self.assertIn('missing-constant-target-proofs', result['reasons'])

    def test_real_imd_keeps_unknown_operands_after_target_proof(self):
        result = tool.evaluate(self.imd, [self.imd_target],
                               self.imd_review, self.height)
        self.assertEqual(result['missing_constant_targets'], [])
        self.assertEqual(result['unresolved_call_site_count'], 34)
        self.assertIn('unresolved-call-operands', result['reasons'])

    def test_corrupt_proof_and_wrong_anchor_fail_closed(self):
        broken = copy.deepcopy(self.zto)
        broken['observation']['nodes'][0]['code'] = '0x6000'
        with self.assertRaises((ValueError, KeyError)):
            tool.evaluate(broken, [], self.zto_review, self.height)
        with self.assertRaises((ValueError, KeyError)):
            tool.evaluate(self.zto, [], self.zto_review, self.height, '0x' + '11' * 32)

    def test_review_validation(self):
        invalid = copy.deepcopy(self.zto_review)
        invalid['runtimes'].append(copy.deepcopy(invalid['runtimes'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            tool.validate_review(invalid)
        invalid = copy.deepcopy(self.zto_review)
        invalid['runtimes'][0]['address'] = '0x' + '00' * 20
        with self.assertRaises(ValueError):
            tool.validate_review(invalid)
        invalid = copy.deepcopy(self.zto_review)
        invalid['extra'] = 'wildcard'
        with self.assertRaises(ValueError):
            tool.validate_review(invalid)

    def test_cli_refusal_is_structured_exit_three(self):
        command = [sys.executable, '-B', str(HERE / 'code_frontier_review.py'),
                   '--source', str(TOOLS / 'code-routes/zto-proof.json'),
                   '--review', str(HERE / 'zto-example-review.json'),
                   '--as-of-block', str(self.height)]
        result = subprocess.run(command, cwd=HERE.parents[2],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)['reasons'], ['missing-caller-anchor'])
        self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
