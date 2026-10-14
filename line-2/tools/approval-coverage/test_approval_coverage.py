import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approval_coverage as coverage

ROOT = Path(__file__).resolve().parents[2]


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = json.loads((ROOT / 'tools/allowance-lens/observation.json').read_text())
        cls.last = json.loads((ROOT / 'tools/allowance-changes/lens-recheck.json').read_text())

    def test_real_gap_and_no_false_clearance(self):
        result = coverage.assess([self.first, self.last])
        self.assertEqual(result['status'], 'gaps_remain')
        self.assertEqual(result['missing_intervals'],
                         [{'from_block': 26183752, 'to_block': 26184306}])
        self.assertEqual(result['discovered_pair_count'], 19)
        self.assertEqual(result['windows'][1]['approval_logs'], 0)
        self.assertFalse(result['complete_wallet_audit'])
        self.assertIn('--block 26184306 --window 555',
                      result['read_only_capture_commands'][0])

    def test_identical_overlap_and_target_edges(self):
        result = coverage.assess([self.first, self.first])
        self.assertEqual(result['status'], 'continuous_event_scan_in_target')
        self.assertEqual(result['missing_intervals'], [])
        result = coverage.assess([self.first], (26182250, 26183753))
        self.assertEqual(result['missing_intervals'],
                         [{'from_block': 26182250, 'to_block': 26182251},
                          {'from_block': 26183752, 'to_block': 26183753}])

    def test_owner_filters_cannot_mix(self):
        filtered = copy.deepcopy(self.last)
        filtered['query']['owner'] = self.first['raw']['balances'][0]['owner']
        with self.assertRaisesRegex(ValueError, 'owner filter'):
            coverage.assess([self.first, filtered])

    def test_same_height_conflict_refused(self):
        altered = copy.deepcopy(self.last)
        altered['block']['hash'] = '0x' + 'a' * 64
        with self.assertRaisesRegex(ValueError, 'conflicting block headers'):
            coverage.assess([self.last, altered])

    def test_explicit_read_is_not_scan(self):
        explicit = json.loads((ROOT / 'tools/permission-gate/live-observation.json').read_text())['observations'][0]
        with self.assertRaisesRegex(ValueError, 'explicit-pair'):
            coverage.assess([explicit])

    def test_invalid_target_refused(self):
        with self.assertRaisesRegex(ValueError, 'target interval'):
            coverage.assess([self.first], (26183751, 26182252))


if __name__ == '__main__':
    unittest.main()
