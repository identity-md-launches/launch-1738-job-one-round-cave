#!/usr/bin/env python3
"""Reverify code proofs beside an exact gas-capped call. Offline, nothing sent."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

code = module('shared_cap_code', ROOT / 'line-3/tools/code-target-proofs/code_target_proofs.py')
cap = module('shared_cap_call', ROOT / 'line-4/tools/gas-cap-rehearsal/gas_cap.py')
alignment = module('shared_cap_alignment', HERE.parent / 'evidence-alignment/evidence_alignment.py')

def evaluate(bundle, evidence, request):
    # Recompute both ancestors' checks from raw evidence, never trust saved verdicts.
    identity = code.evaluate(bundle, [])
    rehearsal = cap.evaluate(evidence, request)
    wanted = rehearsal['request']
    same = (alignment.context(identity['chain_id'], identity['source_target'], identity['code_block'])
            == alignment.context(wanted['chain_id'], wanted['call']['to'], wanted['block']))
    joined = same and rehearsal['verdict'] == 'matched'
    return {'schema': 'proof-gas-cap-context-v1',
            'status': 'historical_context_joined' if joined else 'withheld',
            'context_aligned': same, 'gas_cap_verdict': rehearsal['verdict'],
            'code_identity': identity, 'gas_cap_rehearsal': rehearsal,
            'joined_call': wanted if joined else None,
            'transaction_approved': False,
            'limits': 'A historical evidence join only. State proofs bind code to the supplied '
                      'header, whose consensus authenticity is unverified. Call results remain '
                      'provider claims, not execution proofs. No code semantics, consumed gas, '
                      'safe transaction gas limit, authority, future execution or trade bounds '
                      'are established. Missing constant target proofs and unresolved call '
                      'operands remain visible. Nothing is signed or sent.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', default=str(HERE / 'zto-proof.json'))
    parser.add_argument('--evidence', default=str(HERE / 'zto-evidence.json'))
    parser.add_argument('--request', default=str(HERE / 'zto-request.json'))
    args = parser.parse_args()
    try:
        report = evaluate(cap.binding.read_json(args.proof),
                          cap.binding.read_json(args.evidence), cap.binding.read_json(args.request))
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report['status'] == 'historical_context_joined' else 2
    except (ValueError, KeyError, TypeError, OSError, AttributeError, RecursionError) as exc:
        print(json.dumps({'status': 'invalid', 'error': str(exc)}), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
