#!/usr/bin/env python3
"""Rehearse exact expected return bytes with an explicit gas allowance. Nothing sent."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gas_cap_binding',
    HERE.parent / 'rehearsal-binding' / 'rehearsal_binding.py')
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)
core = binding.core
SCHEMA = 'gas-cap-rehearsal-v1'
REQUEST = 'gas-cap-request-v1'
KEYS = {'schema', 'chain_id', 'call', 'block', 'gas_limit', 'expected_return'}
EVIDENCE_KEYS = {'schema', 'source', 'transport', 'request', 'code_present',
                 'baseline', 'capped', 'recheck'}
LIMITS = ('Matched means only that two provider-reported historical eth_call results '
          'equal explicit expected bytes, one with provider-default gas and one with '
          'the exact declared gas allowance. This is not gas consumed, an estimate, '
          'a minimum gas search, a safe transaction gas limit, authorization or approval. '
          'A call may inspect gasleft() and change behavior with its allowance. RPC '
          'errors do not establish out-of-gas. No current state, side effects, future '
          'execution, ABI correctness or chain/provider authenticity is established. '
          'The sender may be a contract, not an available transaction origin. Nothing sent.')


def request(value):
    core.require(isinstance(value, dict) and set(value) == KEYS,
                 'request must contain exactly the documented fields')
    core.require(value['schema'] == REQUEST and type(value['chain_id']) is int
                 and value['chain_id'] == 1, 'request requires Ethereum mainnet')
    core.require(isinstance(value['call'], dict) and set(value['call']) ==
                 {'from', 'to', 'data', 'value'}, 'call requires explicit from, to, data, value')
    gas = value['gas_limit']
    core.require(isinstance(gas, str) and gas.isascii() and gas.isdecimal()
                 and len(gas) <= 20 and not gas.startswith('0'),
                 'gas_limit must be a positive canonical decimal string')
    core.require(int(gas) < 2**64, 'gas_limit exceeds uint64')
    return {'schema': REQUEST, 'chain_id': 1, 'call': core.transaction(value['call']),
            'block': binding.exact_block(value['block']), 'gas_limit': gas,
            'expected_return': core.data(value['expected_return'])}


def outcome(value):
    core.require(isinstance(value, dict) and len(value) == 1,
                 'outcome must contain exactly result or error')
    if 'result' in value:
        return {'result': core.data(value['result'])}
    core.require('error' in value, 'outcome lacks result or error')
    error = core.RPCError(value['error']).error
    core.require(set(error) <= {'code', 'message', 'data'}, 'unknown RPC error field')
    if 'data' in error:
        core.data(error['data'])
    return {'error': error}


def validate(value):
    core.require(isinstance(value, dict) and set(value) == EVIDENCE_KEYS
                 and value['schema'] == SCHEMA, 'invalid evidence fields or schema')
    core.require(value['source'] in core.ENDPOINTS, 'unsupported source')
    core.require(value['transport'] in ('public-rpc', 'contributor-relay'),
                 'unsupported transport attribution')
    core.require(value['code_present'] is True, 'target code was not confirmed')
    wanted = request(value['request'])
    core.require(binding.exact_block(value['recheck']) == wanted['block'],
                 'rechecked block differs from requested block')
    return wanted, outcome(value['baseline']), outcome(value['capped'])


def evaluate(evidence, proposed):
    wanted = request(proposed)
    observed, baseline, capped = validate(evidence)
    differences = [key for key in wanted if observed[key] != wanted[key]]
    report = {'schema': SCHEMA, 'verdict': 'inconclusive', 'request': wanted,
              'source': evidence['source'], 'transport': evidence['transport'],
              'request_sha256': binding.digest(wanted),
              'evidence_sha256': binding.digest(evidence), 'differences': differences,
              'baseline': baseline, 'capped': capped, 'limits': LIMITS}
    if differences:
        report.update(verdict='request_mismatch', reason='evidence is for a different request')
    elif 'error' in baseline or 'error' in capped:
        report['reason'] = 'at least one provider RPC call failed; failure cause is not established'
    elif baseline['result'] != wanted['expected_return']:
        report.update(verdict='return_mismatch', reason='baseline differs from expected return bytes')
    elif capped['result'] != wanted['expected_return']:
        report.update(verdict='return_mismatch', reason='capped call differs from expected return bytes')
    else:
        report.update(verdict='matched', reason='both calls returned the exact expected bytes')
    return report


def capture(rpc, proposed):
    wanted = request(proposed)  # Validate all input before networking.
    core.require(rpc.call('eth_chainId', []) == '0x1', 'expected Ethereum mainnet')
    final = core.header(rpc.call('eth_getBlockByNumber', ['finalized', False]))
    block = wanted['block']
    core.require(core.quantity(block['number']) <= core.quantity(final['number']),
                 'requested block is newer than finalized head')
    chosen = core.header(rpc.call('eth_getBlockByNumber', [block['number'], False]))
    core.require(chosen == block, 'provider header differs from requested block')
    if chosen['number'] == final['number']:
        core.require(chosen == final, 'finalized header conflicts with requested block')
    else:
        core.require(chosen['hash'] != final['hash'] and
                     core.quantity(chosen['timestamp']) < core.quantity(final['timestamp']),
                     'historical header conflicts with finalized head')
    pin = {'blockHash': block['hash'], 'requireCanonical': True}
    code = core.data(rpc.call('eth_getCode', [wanted['call']['to'], pin]))
    core.require(code != '0x', 'target has no code')

    def run(tx):
        try:
            return outcome({'result': rpc.call('eth_call', [tx, pin])})
        except core.RPCError as exc:
            return outcome({'error': exc.error})

    baseline = run(dict(wanted['call']))
    capped_call = dict(wanted['call'], gas=hex(int(wanted['gas_limit'])))
    capped = run(capped_call)
    recheck = core.header(rpc.call('eth_getBlockByNumber', [block['number'], False]))
    evidence = {'schema': SCHEMA, 'source': rpc.endpoint,
                'transport': 'contributor-relay' if rpc.via_relay else 'public-rpc',
                'request': wanted, 'code_present': True,
                'baseline': baseline, 'capped': capped, 'recheck': recheck}
    validate(evidence)
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='offline replay of real ZTO calls with 30000 gas')
    check = commands.add_parser('check', help='compare evidence with an explicit reviewed request')
    check.add_argument('evidence')
    check.add_argument('request')
    live = commands.add_parser('live', help='read-only paired calls at the exact reviewed block')
    live.add_argument('request')
    live.add_argument('--rpc', choices=core.ENDPOINTS, default=core.ENDPOINTS[0])
    live.add_argument('--relay', help='explicit contributor transport; never saved in evidence')
    live.add_argument('--save', required=True, help='new evidence file within the workspace')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            proposed = binding.read_json(HERE / 'zto-request.json')
            evidence = binding.read_json(HERE / 'zto-evidence.json')
        else:
            proposed = binding.read_json(args.request)
            request(proposed)
            if args.command == 'check':
                evidence = binding.read_json(args.evidence)
            else:
                path = core.workspace_path(args.save)
                core.require(not path.exists() and path.parent.is_dir(),
                             'save requires a new file and an existing parent')
                evidence = capture(core.RPC(args.rpc, relay=args.relay), proposed)
                raw = (json.dumps(evidence, indent=2, allow_nan=False) + '\n').encode()
                core.require(len(raw) <= binding.LIMIT, 'evidence exceeds 95 KB')
                with path.open('xb') as handle:
                    handle.write(raw)
        report = evaluate(evidence, proposed)
        print(json.dumps(report, indent=2, allow_nan=False))
        return {'matched': 0, 'return_mismatch': 1, 'request_mismatch': 1,
                'inconclusive': 2}[report['verdict']]
    except (ValueError, KeyError, TypeError, OSError, RecursionError, core.RPCError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'inconclusive', 'error': str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
