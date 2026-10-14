import copy
import unittest
from unittest.mock import patch
import zto_witness_quorum as tool


class QuorumTests(unittest.TestCase):
    def setUp(self):
        self.observation, self.check = tool.policy_tool.replay.demo_inputs()
        self.policy = {'schema': 'zto-witness-policy-v1',
                       'expected_block_hash': self.observation['base']['block']['hash'],
                       'reference_block': int(self.observation['base']['block']['number'], 16),
                       'max_age_blocks': 0, 'input_token': 'ZTO',
                       'maximum_input_raw': str(10**18), 'maximum_slippage_bps': 100,
                       'sources': {self.observation['base']['source']: 'one'}}

    def request(self, count=2):
        return {'schema': 'zto-witness-quorum-request-v1', 'policy': copy.deepcopy(self.policy),
                'minimum_distinct_groups': 2, 'amount': '1', 'slippage_bps': 100,
                'candidates': [{'snapshot': 's' + str(i), 'quoter': 'q' + str(i)} for i in range(count)]}

    def evaluate_request(self, request, items):
        return tool.evaluate(request, lambda _: next(items))

    def test_real_single_source_demo_withholds(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = tool.demo()
        self.assertFalse(result['bound_released'])
        self.assertIn('duplicate_source_label', result['reasons'])
        self.assertIn('insufficient_distinct_receiver_provider_groups', result['reasons'])

    def test_synthetic_three_group_quorum_releases(self):
        observations, checks = [], []
        for i, (label, group) in enumerate((('https://one.example/rpc', 'one'), ('https://two.example/rpc', 'two'), ('https://three.example/rpc', 'three'))):
            obs, check = copy.deepcopy(self.observation), copy.deepcopy(self.check)
            obs['base']['source'] = check['source'] = label
            observations.append(obs); checks.append(check); self.policy['sources'][label] = group
        del self.policy['sources'][self.observation['base']['source']]
        request = self.request(3)
        result = self.evaluate_request(request, iter(sum(zip(observations, checks), ())))
        self.assertTrue(result['bound_released'])
        self.assertEqual(result['bound']['planning_minimum_raw'], '15139234039518')
        self.assertEqual(result['distinct_receiver_provider_groups'], ['one', 'three', 'two'])

    def test_duplicate_or_unapproved_source_withholds(self):
        request = self.request()
        result = self.evaluate_request(request, iter((self.observation, self.check, self.observation, self.check)))
        self.assertFalse(result['bound_released'])
        self.assertIn('duplicate_source_label', result['reasons'])
        altered, altered_check = copy.deepcopy(self.observation), copy.deepcopy(self.check)
        altered['base']['source'] = altered_check['source'] = 'https://other.example/rpc'
        result = self.evaluate_request(request, iter((self.observation, self.check, altered, altered_check)))
        self.assertIn('source_not_approved_by_receiver', result['reasons'])

    def test_strict_request_controls(self):
        for key, value in [('minimum_distinct_groups', True), ('minimum_distinct_groups', 1),
                           ('amount', 1), ('slippage_bps', True), ('candidates', [])]:
            request = self.request(); request[key] = value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    tool.validate_request(request)


if __name__ == '__main__':
    unittest.main()
