#!/usr/bin/env python3
"""Require a receiver-selected quorum of saved ZTO/IMD quote witnesses."""
import argparse
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'zto-witness-policy'))
import zto_witness_policy as policy_tool

replay = policy_tool.replay
require = replay.require
REQUEST_KEYS = {'schema', 'policy', 'minimum_distinct_groups', 'amount', 'slippage_bps',
                'candidates'}
CANDIDATE_KEYS = {'snapshot', 'quoter'}


def validate_request(request):
    require(type(request) is dict and set(request) == REQUEST_KEYS, 'unexpected request fields')
    require(request['schema'] == 'zto-witness-quorum-request-v1', 'unexpected request schema')
    policy_tool.validate_policy(request['policy'])
    minimum = request['minimum_distinct_groups']
    require(type(minimum) is int and 2 <= minimum <= 8,
            'minimum distinct groups must be an integer from 2 to 8')
    require(type(request['amount']) is str, 'amount must be a decimal string')
    require(type(request['slippage_bps']) is int and 0 <= request['slippage_bps'] <= 9999,
            'slippage bps must be 0..9999')
    candidates = request['candidates']
    require(type(candidates) is list and minimum <= len(candidates) <= 8,
            'candidate count must meet quorum and be at most 8')
    for candidate in candidates:
        require(type(candidate) is dict and set(candidate) == CANDIDATE_KEYS,
                'candidate must name exactly snapshot and quoter')
        require(all(type(candidate[k]) is str for k in CANDIDATE_KEYS),
                'candidate paths must be strings')
    return request


def evaluate(request, loader=replay.read_json):
    """Recompute each candidate, then release only a policy-approved diverse quorum."""
    validate_request(request)
    policy = request['policy']
    observations, checks, rows, reasons = [], [], [], []
    seen_sources = set()
    leader = None
    for candidate in request['candidates']:
        observation, check = loader(candidate['snapshot']), loader(candidate['quoter'])
        block = replay.header(observation)
        quote = replay.path.quote(observation, policy['input_token'], request['amount'])
        matches = replay.check_source(observation, check, policy['input_token'], request['amount'], quote)
        source = observation['base']['source']
        group = policy['sources'].get(source)
        if source in seen_sources:
            reasons.append('duplicate_source_label')
        seen_sources.add(source)
        if group is None:
            reasons.append('source_not_approved_by_receiver')
        if quote['status'] != 'estimated':
            reasons.append('incomplete_local_fill')
        if not matches:
            reasons.append('quoter_does_not_match_complete_local_fill')
        if block['hash'] != policy['expected_block_hash']:
            reasons.append('caller_block_anchor_mismatch')
        age = policy['reference_block'] - int(block['number'], 16)
        if age < 0 or age > policy['max_age_blocks']:
            reasons.append('outside_caller_age_limit')
        if leader is not None and not replay.witness.compare_snapshots(leader, observation)['same_pool_state_and_coverage']:
            reasons.append('different_block_state_or_coverage')
        leader = leader or observation
        observations.append(observation); checks.append(check)
        rows.append({'source_label': source, 'receiver_provider_group': group,
                     'block': block, 'local_status': quote['status'],
                     'raw_quoter_matches': matches, 'output_raw': str(quote.get('estimate', {}).get('output_raw'))})
    groups = {row['receiver_provider_group'] for row in rows if row['receiver_provider_group'] is not None}
    if len(groups) < request['minimum_distinct_groups']:
        reasons.append('insufficient_distinct_receiver_provider_groups')
    if request['slippage_bps'] > policy['maximum_slippage_bps']:
        reasons.append('slippage_exceeds_receiver_ceiling')
    raw = replay.path.z.parse_amount(request['amount'], replay.path.decode(observations[0])[0]['decimals'][1 if policy['input_token'] == 'ZTO' else 0])
    if raw > int(policy['maximum_input_raw']):
        reasons.append('input_exceeds_receiver_ceiling')
    # The inherited pair review supplies the bounded floor amount only after it replays both files.
    chosen = None
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i]['receiver_provider_group'] != rows[j]['receiver_provider_group']:
                chosen = (i, j); break
        if chosen:
            break
    pair = None
    if chosen:
        i, j = chosen
        pair = policy_tool.review(observations[i], observations[j], checks[i], checks[j], policy,
                                  policy['input_token'], request['amount'], request['slippage_bps'])
        if not pair['bound_released']:
            reasons.append('selected_pair_withheld')
    else:
        reasons.append('no_cross_group_pair')
    reasons = list(dict.fromkeys(reasons))
    released = not reasons and pair is not None and pair['bound_released']
    return {'schema': 'zto-witness-quorum-report-v1', 'status': 'accepted' if released else 'withheld',
            'chain_id': 1, 'pool_id': replay.path.z.POOL,
            'receiver_policy_sha256': replay.digest(policy),
            'request_sha256': replay.digest(request), 'input_token': policy['input_token'],
            'requested_input': request['amount'], 'input_raw': str(raw),
            'slippage_bps': request['slippage_bps'],
            'minimum_distinct_groups': request['minimum_distinct_groups'],
            'distinct_receiver_provider_groups': sorted(groups), 'candidates': rows,
            'selected_pair_indexes': list(chosen) if chosen else None, 'reasons': reasons,
            'bound_released': released, 'bound': pair['bound'] if released else None,
            'limitations': ['Receiver-assigned groups do not authenticate independent upstreams.',
                            'A relabeled copied capture can pass an incorrectly trusted receiver policy.',
                            *replay.LIMITATIONS]}


def demo_request():
    observation, check = policy_tool.replay.demo_inputs()
    source = observation['base']['source']
    policy = {'schema': 'zto-witness-policy-v1', 'expected_block_hash': observation['base']['block']['hash'],
              'reference_block': int(observation['base']['block']['number'], 16), 'max_age_blocks': 0,
              'input_token': 'ZTO', 'maximum_input_raw': str(10**18), 'maximum_slippage_bps': 100,
              'sources': {source: 'archived-publicnode'}}
    # Direct objects make this demonstration network-free and show why one capture is not a quorum.
    return {'schema': 'zto-witness-quorum-request-v1', 'policy': policy, 'minimum_distinct_groups': 2,
            'amount': '1', 'slippage_bps': 100,
            'candidates': [{'snapshot': 'demo-a', 'quoter': 'demo-a'},
                           {'snapshot': 'demo-b', 'quoter': 'demo-b'}]}, observation, check


def demo():
    request, observation, check = demo_request()
    calls = iter((observation, check, observation, check))
    result = evaluate(request, lambda _: next(calls))
    result['mode'] = 'offline_real_historical_single_source'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--request')
    args = parser.parse_args(argv)
    try:
        require((args.demo and args.request is None) or (not args.demo and args.request is not None),
                'use exactly one of --demo or --request')
        if args.demo:
            # This fixture adapter never opens a socket or a user file.
            result = demo()
        else:
            result = evaluate(replay.read_json(args.request))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if args.demo or result['bound_released'] else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
