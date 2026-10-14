#!/usr/bin/env python3
"""Match every proved runtime in a bounded call scan to an explicit review list."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code-dependency-frontier'))
import code_dependency_frontier as frontier

lens = frontier.targets.calls.lens
require = lens.require
read_json = frontier.read_json
SCHEMA = 'code-frontier-review-v1'


def validate_review(value):
    require(isinstance(value, dict) and set(value) ==
            {'schema', 'chain_id', 'source_target', 'max_age_blocks', 'runtimes'},
            'review fields must be exact')
    require(value['schema'] == SCHEMA and type(value['chain_id']) is int
            and value['chain_id'] == 1, 'wrong review schema or chain')
    root = lens.address(value['source_target'])
    age = value['max_age_blocks']
    require(type(age) is int and 0 <= age < 2**64, 'invalid max_age_blocks')
    rows = value['runtimes']
    require(isinstance(rows, list) and 1 <= len(rows) <= 96,
            'review must list 1 to 96 runtimes')
    normalized = {}
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'address', 'code_hash'},
                'review runtime fields must be exact')
        address = lens.address(row['address'])
        require(address not in normalized, 'duplicate reviewed runtime address')
        normalized[address] = lens.fixed_hex(row['code_hash'], 32)
    require(root in normalized, 'review must include source target')
    return {'schema': SCHEMA, 'chain_id': 1, 'source_target': root,
            'max_age_blocks': age,
            'runtimes': [{'address': address, 'code_hash': normalized[address]}
                         for address in sorted(normalized)]}


def evaluate(source, target_proofs, review, as_of_block, anchor_hash=None):
    """Reverify raw proofs; a saved frontier report cannot substitute for evidence."""
    review = validate_review(review)
    require(type(as_of_block) is int and 0 <= as_of_block < 2**64,
            'as_of_block must be a uint64 integer')
    report = frontier.evaluate(source, target_proofs, anchor_hash)
    target = lens.address(report['source_target'])
    height = lens.quantity(report['code_block']['number'])
    require(as_of_block >= height, 'as_of_block precedes code evidence')
    require(height < 2**64, 'code block exceeds uint64')
    expected = {row['address']: row['code_hash'] for row in review['runtimes']}
    measured = {row['address']: row['code_hash'] for row in report['runtimes']}
    require(len(measured) == report['proved_runtime_count'],
            'duplicate measured runtime address')
    missing = sorted(expected.keys() - measured.keys())
    unreviewed = sorted(measured.keys() - expected.keys())
    mismatched = [{'address': address, 'reviewed_hash': expected[address],
                   'measured_hash': measured[address]}
                  for address in sorted(expected.keys() & measured.keys())
                  if expected[address] != measured[address]]
    empty_targets = sorted({edge['target'] for edge in report['constant_edges']
                            if edge['status'] == 'proved-empty-account'})
    # A hash set does not review proxy-path order or routing semantics.
    routing_candidates = sorted({lens.address(node['address'])
                                 for bundle in [source, *target_proofs]
                                 for node in bundle['observation']['nodes']
                                 if node['kind'] != 'no-supported-proxy-signal'})
    reasons = []
    if target != review['source_target']:
        reasons.append('different-source-target')
    if missing or unreviewed or mismatched:
        reasons.append('reviewed-runtime-set-or-hash-mismatch')
    if report['missing_constant_targets']:
        reasons.append('missing-constant-target-proofs')
    if report['unresolved_call_site_count']:
        reasons.append('unresolved-call-operands')
    if empty_targets:
        reasons.append('proved-empty-call-target')
    if routing_candidates:
        reasons.append('proxy-routing-requires-separate-review')
    age = as_of_block - height
    if age > review['max_age_blocks']:
        reasons.append('code-evidence-too-old')
    if anchor_hash is None:
        reasons.append('missing-caller-anchor')
    canonical = json.dumps(review, sort_keys=True, separators=(',', ':')).encode('ascii')
    return {
        'schema': 'code-frontier-review-result-v1', 'chain_id': 1,
        'decision': 'refuse' if reasons else 'accept-bounded-code-identities',
        'reasons': reasons, 'source_target': target,
        'code_block': report['code_block'], 'as_of_block': as_of_block,
        'code_age_blocks': age, 'max_age_blocks': review['max_age_blocks'],
        'review_digest': lens.digest(canonical),
        'missing_reviewed_runtimes': missing,
        'unreviewed_measured_runtimes': unreviewed,
        'mismatched_runtime_hashes': mismatched,
        'measured_runtimes': report['runtimes'],
        'missing_constant_targets': report['missing_constant_targets'],
        'unresolved_call_site_count': report['unresolved_call_site_count'],
        'unresolved_calls': report['unresolved_calls'],
        'empty_call_targets': empty_targets,
        'routing_candidates': routing_candidates,
        'raw_proofs_reverified': True,
        'caller_supplied_anchor_hash_matched': anchor_hash is not None,
        'anchor_authenticity_verified': False,
        'reachability_verified': False, 'dependency_completeness_verified': False,
        'semantic_safety_verified': False,
        'scope': 'Exact reviewed hashes for all runtimes visible in this historical, '
                 'proof-backed bounded structural scan. A caller must independently trust '
                 'the review, execution anchor and reference height. Even acceptance does '
                 'not prove full dependencies, proxy routing, reachable behavior, consensus, '
                 'current code, safety or authorization to transact.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='workspace-local raw Code Proof JSON')
    parser.add_argument('--target-proof', action='append', default=[],
                        help='same-block raw proof of a discovered constant call target')
    parser.add_argument('--review', required=True, help='independently reviewed exact hash list')
    parser.add_argument('--as-of-block', type=int, required=True,
                        help='caller-selected decimal reference height')
    parser.add_argument('--anchor-hash', help='separately trusted execution block hash')
    args = parser.parse_args(argv)
    try:
        require(len(args.target_proof) <= 16, 'too many target proofs')
        result = evaluate(read_json(args.source),
                          [read_json(path) for path in args.target_proof],
                          read_json(args.review), args.as_of_block, args.anchor_hash)
        print(json.dumps(result, indent=2))
        return 0 if result['decision'] == 'accept-bounded-code-identities' else 3
    except (ValueError, KeyError, TypeError, OSError, OverflowError,
            AttributeError, IndexError, RecursionError) as error:
        print('Code Frontier Review: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
