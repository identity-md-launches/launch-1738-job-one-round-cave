"""Offline adversarial checks; saved demo evidence was collected from Ethereum."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('tested_gas_cap', HERE / 'gas_cap.py')
gas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gas)


class FakeRPC:
    endpoint = gas.core.ENDPOINTS[0]
    via_relay = True

    def __init__(self, wanted):
        self.wanted = wanted
        self.calls = []
        self.code = '0x6000'
        self.changed = False
        self.fail_capped = False
        self.final = dict(wanted['block'])

    def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'eth_chainId':
            return '0x1'
        if method == 'eth_getBlockByNumber':
            if params[0] == 'finalized':
                return self.final
            block = dict(self.wanted['block'])
            if self.changed and len(self.calls) > 5:
                block['hash'] = '0x' + 'ab' * 32
            return block
        if method == 'eth_getCode':
            return self.code
        if method == 'eth_call':
            if self.fail_capped and 'gas' in params[0]:
                raise gas.core.RPCError({'code': -32000, 'message': 'gas allowance error'})
            return self.wanted['expected_return']
        raise AssertionError('Unexpected method: ' + method)


class GasCapTests(unittest.TestCase):
    def setUp(self):
        self.request = gas.binding.read_json(HERE / 'zto-request.json')
        self.evidence = gas.binding.read_json(HERE / 'zto-evidence.json')

    def test_real_saved_pair(self):
        report = gas.evaluate(self.evidence, self.request)
        self.assertEqual(report['verdict'], 'matched')
        self.assertEqual(int(report['capped']['result'], 16), 10**27)
        self.assertEqual(report['transport'], 'contributor-relay')

    def test_real_tight_allowance_does_not_match(self):
        wanted = gas.binding.read_json(HERE / 'zto-tight-request.json')
        evidence = gas.binding.read_json(HERE / 'zto-tight-evidence.json')
        report = gas.evaluate(evidence, wanted)
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertEqual(report['baseline']['result'], wanted['expected_return'])
        self.assertEqual(report['capped']['error']['message'], 'intrinsic gas too low')

    def test_each_request_field_is_bound(self):
        alternatives = {'gas_limit': '30001', 'expected_return': '0x',
                        'call': dict(self.request['call'], value='0x1'),
                        'block': dict(self.request['block'], timestamp='0x6acf62d8')}
        for key, value in alternatives.items():
            with self.subTest(key=key):
                wanted = dict(self.request, **{key: value})
                self.assertEqual(gas.evaluate(self.evidence, wanted)['verdict'], 'request_mismatch')

    def test_each_call_field_is_bound(self):
        for field, value in [('from', gas.core.TOKENS['IMD']),
                             ('to', gas.core.TOKENS['IMD']), ('data', '0x70a08231'),
                             ('value', '0x1')]:
            wanted = copy.deepcopy(self.request)
            wanted['call'][field] = value
            self.assertEqual(gas.evaluate(self.evidence, wanted)['verdict'], 'request_mismatch')

    def test_bad_gas_limits(self):
        for value in [True, 30000, '', '0', '-1', '030000', '0x7530', '1.0',
                      ' 30000', '٣٠٠٠٠', str(2**64), '1'*21]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                gas.request(dict(self.request, gas_limit=value))
        self.assertEqual(gas.request(dict(self.request, gas_limit='1'))['gas_limit'], '1')
        self.assertEqual(gas.request(dict(self.request, gas_limit=str(2**64-1)))['gas_limit'], str(2**64-1))

    def test_implicit_sender_and_extra_transaction_fields_refused(self):
        for field in ['from', 'nonce', 'gas', 'gasPrice', 'accessList']:
            wanted = copy.deepcopy(self.request)
            if field == 'from':
                del wanted['call']['from']
            else:
                wanted['call'][field] = '0x1'
            with self.assertRaises(ValueError):
                gas.request(wanted)

    def test_chain_boolean_wrong_chain_and_schema(self):
        for key, value in [('chain_id', True), ('chain_id', 2), ('schema', 'anything')]:
            with self.assertRaises(ValueError):
                gas.request(dict(self.request, **{key: value}))

    def test_all_missing_and_extra_fields(self):
        for document, validator in [(self.request, gas.request), (self.evidence, gas.validate)]:
            for field in document:
                candidate = dict(document)
                del candidate[field]
                with self.assertRaises(ValueError):
                    validator(candidate)
            with self.assertRaises(ValueError):
                validator(dict(document, extra='unknown'))

    def test_return_difference_in_either_call(self):
        for side in ['baseline', 'capped']:
            evidence = dict(self.evidence, **{side: {'result': '0x'}})
            self.assertEqual(gas.evaluate(evidence, self.request)['verdict'], 'return_mismatch')

    def test_abi_false_is_only_exact_bytes_not_success(self):
        raw = '0x' + '00'*32
        wanted = dict(self.request, expected_return=raw)
        evidence = dict(self.evidence, request=wanted, baseline={'result': raw}, capped={'result': raw})
        report = gas.evaluate(evidence, wanted)
        self.assertEqual(report['verdict'], 'matched')
        self.assertIn('ABI correctness', report['limits'])

    def test_errors_are_inconclusive_even_when_both_equal(self):
        for code in [3, -32000, -32602]:
            error = {'error': {'code': code, 'message': 'execution reverted', 'data': '0x'}}
            for side in ['baseline', 'capped']:
                evidence = dict(self.evidence, **{side: error})
                self.assertEqual(gas.evaluate(evidence, self.request)['verdict'], 'inconclusive')
            evidence = dict(self.evidence, baseline=error, capped=error)
            self.assertEqual(gas.evaluate(evidence, self.request)['verdict'], 'inconclusive')

    def test_invalid_outcomes(self):
        for bad in [{}, {'result': '0x', 'error': {}}, {'other': '0x'},
                    {'result': '0x1'}, {'error': {'code': True, 'message': 'bad'}},
                    {'error': {'code': 3, 'message': 'bad', 'extra': 1}},
                    {'error': {'code': 3, 'message': 'bad', 'data': {'nested': '0x'}}}]:
            with self.assertRaises(ValueError):
                gas.outcome(bad)

    def test_header_recheck_and_code_confirmation(self):
        for key, value in [('recheck', dict(self.request['block'], hash='0x'+'ab'*32)),
                           ('code_present', 1), ('source', 'https://example.com'),
                           ('transport', 'trusted')]:
            with self.assertRaises(ValueError):
                gas.validate(dict(self.evidence, **{key: value}))

    def test_pair_uses_exact_hash_and_only_capped_call_has_gas(self):
        rpc = FakeRPC(self.request)
        evidence = gas.capture(rpc, self.request)
        self.assertEqual(gas.evaluate(evidence, self.request)['verdict'], 'matched')
        reads = [(method, params) for method, params in rpc.calls if method in ('eth_call', 'eth_getCode')]
        self.assertEqual(len(reads), 3)
        for method, params in reads:
            self.assertEqual(params[1], {'blockHash': self.request['block']['hash'], 'requireCanonical': True})
        calls = [params[0] for method, params in reads if method == 'eth_call']
        self.assertEqual(calls[0], self.request['call'])
        self.assertEqual(calls[1], dict(self.request['call'], gas='0x7530'))
        self.assertTrue(all(method in gas.core.RPC.METHODS for method, _ in rpc.calls))

    def test_bad_request_refused_before_network(self):
        rpc = FakeRPC(self.request)
        with self.assertRaises(ValueError):
            gas.capture(rpc, dict(self.request, gas_limit='0'))
        self.assertEqual(rpc.calls, [])

    def test_empty_code_refused_before_call(self):
        rpc = FakeRPC(self.request)
        rpc.code = '0x'
        with self.assertRaises(ValueError):
            gas.capture(rpc, self.request)
        self.assertFalse(any(method == 'eth_call' for method, _ in rpc.calls))

    def test_changed_header_discarded(self):
        rpc = FakeRPC(self.request)
        rpc.changed = True
        with self.assertRaises(ValueError):
            gas.capture(rpc, self.request)

    def test_newer_than_finalized_refused(self):
        rpc = FakeRPC(self.request)
        rpc.final = dict(self.request['block'], number=hex(int(self.request['block']['number'], 16)-1))
        with self.assertRaises(ValueError):
            gas.capture(rpc, self.request)

    def test_provider_cap_failure_retained_without_cause_guess(self):
        rpc = FakeRPC(self.request)
        rpc.fail_capped = True
        report = gas.evaluate(gas.capture(rpc, self.request), self.request)
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertIn('not established', report['reason'])

    def test_duplicate_nonfinite_oversized_json(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b' '*95001]:
            with self.assertRaises(ValueError):
                gas.binding.parse_json(raw)

    def test_outside_workspace_path_refused(self):
        with self.assertRaises(ValueError):
            gas.binding.read_json('/tmp/outside-gas-cap.json')


if __name__ == '__main__':
    unittest.main()
