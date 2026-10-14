#!/usr/bin/env python3
"""Map gaps between validated ERC-20 Approval-event discovery windows."""

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'permission-gate'))
import permission_gate as gate

lens = gate.lens
MAX_INPUTS = 16


def assess(values, requested=None):
    lens.require(isinstance(values, list) and 1 <= len(values) <= MAX_INPUTS,
                 'supply 1..16 raw Approval-window observations')
    rows, headers, positions, pairs = [], {}, {}, set()
    identity = None
    for value in values:
        report = lens.report(value)
        query = value['query']
        lens.require(query['mode'] == 'approval_window',
                     'explicit-pair reads do not establish event-window coverage')
        owner = lens.address(query['owner']) if query['owner'] is not None else None
        current = (report['chain_id'], report['token'], report['token_address'],
                   report['decimals'], owner)
        lens.require(identity is None or identity == current,
                     'chain, token, decimals and owner filter must match')
        identity = current
        start, end = query['from_block'], query['to_block']
        rows.append((start, end, len(value['logs'])))
        for raw_header in (value['block'], *value['log_headers'].values()):
            h = lens.header(raw_header)
            number = lens.quantity(h['number'])
            fingerprint = (h['hash'].lower(), lens.quantity(h['timestamp']))
            lens.require(number not in headers or headers[number] == fingerprint,
                         'conflicting block headers at the same height')
            headers[number] = fingerprint
        for log in value['logs']:
            number = lens.quantity(log['blockNumber'])
            index = lens.quantity(log['logIndex'])
            position = (number, index)
            canonical = json.dumps(log, sort_keys=True, separators=(',', ':'), allow_nan=False)
            lens.require(position not in positions or positions[position] == canonical,
                         'conflicting Approval log at the same position')
            positions[position] = canonical
            pairs.add((lens.topic_address(log['topics'][1]),
                       lens.topic_address(log['topics'][2])))
    lens.require(len(pairs) <= lens.MAX_PAIRS, 'more than 64 discovered pairs; partition the scan')
    if requested is None:
        low, high = min(row[0] for row in rows), max(row[1] for row in rows)
    else:
        lens.require(isinstance(requested, tuple) and len(requested) == 2
                     and all(type(n) is int for n in requested), 'invalid target interval')
        low, high = requested
    lens.require(0 <= low <= high and high - low <= 100_000,
                 'target interval must be ordered and at most 100001 blocks')
    covered, gaps = [], []
    cursor = low
    for start, end, _ in sorted(rows):
        if end < low or start > high:
            continue
        first, last = max(start, low), min(end, high)
        if first > cursor:
            gaps.append([cursor, first - 1])
        if last >= cursor:
            cursor = last + 1
        if covered and first <= covered[-1][1] + 1:
            covered[-1][1] = max(covered[-1][1], last)
        else:
            covered.append([first, last])
    if cursor <= high:
        gaps.append([cursor, high])
    commands = []
    for first, last in gaps:
        while first <= last:
            end = min(first + lens.MAX_BLOCKS - 1, last)
            command = ('python3 -B line-2/tools/allowance-lens/allowance_lens.py '
                       '--live --token ' + identity[1] + ' --block ' + str(end)
                       + ' --window ' + str(end - first + 1))
            if identity[4] is not None:
                command += ' --owner ' + identity[4]
            commands.append(command)
            first = end + 1
    lens.require(len(commands) <= 64, 'target has too many read-only capture steps')
    ordered_headers = sorted(headers)
    lens.require(all(headers[a][1] <= headers[b][1]
                     for a, b in zip(ordered_headers, ordered_headers[1:])),
                 'block header timestamps go backwards')
    return {
        'schema': 'approval-coverage-report-v1',
        'chain_id': identity[0], 'token': identity[1], 'token_address': identity[2],
        'decimals': identity[3], 'owner_filter': identity[4],
        'target': {'from_block': low, 'to_block': high},
        'status': 'gaps_remain' if gaps else 'continuous_event_scan_in_target',
        'complete_wallet_audit': False,
        'windows': [{'from_block': a, 'to_block': b, 'approval_logs': count}
                    for a, b, count in sorted(rows)],
        'covered_intervals': [{'from_block': a, 'to_block': b} for a, b in covered],
        'missing_intervals': [{'from_block': a, 'to_block': b} for a, b in gaps],
        'discovered_pair_count': len(pairs),
        'discovered_pairs': [{'owner': a, 'spender': b} for a, b in sorted(pairs)],
        'read_only_capture_commands': commands,
        'limitations': [
            'Continuous coverage applies only to the selected block interval and owner filter.',
            'Approvals before the target, unknown spenders, Permit2 and signatures remain outside coverage.',
            'Event discovery is not a current allowance measurement; recheck every known pair at one block.',
            'Saved RPC observations and block headers are trusted claims, not Ethereum proofs or present canonicality.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', action='append', help='raw workspace observation; repeat up to 16 times')
    parser.add_argument('--from-block', type=int)
    parser.add_argument('--to-block', type=int)
    args = parser.parse_args(argv)
    try:
        lens.require((args.from_block is None) == (args.to_block is None),
                     'provide both target bounds or neither')
        files = args.input or [str(HERE.parent / 'allowance-lens' / 'observation.json'),
                               str(HERE.parent / 'allowance-changes' / 'lens-recheck.json')]
        lens.require(len(files) <= MAX_INPUTS, 'too many inputs')
        values = [gate.load(path) for path in files]
        target = None if args.from_block is None else (args.from_block, args.to_block)
        print(json.dumps(assess(values, target), indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
