#!/usr/bin/env python3
"""Read a real ZTO runtime proof at the already reviewed gas-cap block."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path('shared/proof-gas-cap').resolve()))
import proof_gas_cap as glue
proof = glue.code.calls.proof
lens = proof.lens

def capture(endpoint):
    wanted = glue.cap.binding.read_json('shared/proof-gas-cap/zto-request.json')
    rpc = proof.ProofRPC(endpoint)
    selected = rpc.call('eth_getBlockByNumber', [wanted['block']['number'], False])
    lens.require(glue.cap.core.header(selected) == wanted['block'], 'requested header differs')
    decimal = lens.quantity(selected['number'])
    lens.require(decimal == 26190345, 'wrong historical block')
    final = rpc.call('eth_getBlockByNumber', ['finalized', False])
    lens.require(lens.quantity(final['number']) >= decimal, 'requested block newer than finalized head')

    class Pinned:
        endpoint = rpc.endpoint
        def call(self, method, params):
            if method == 'eth_getBlockByNumber' and params == ['finalized', False]:
                return selected
            return rpc.call(method, params)

    bundle = proof.collect(Pinned(), wanted['call']['to'])
    report = glue.evaluate(bundle, glue.cap.binding.read_json('shared/proof-gas-cap/zto-evidence.json'), wanted)
    lens.require(report['status'] == 'historical_context_joined', 'new proof does not join')
    return bundle

def fresh(endpoint):
    rpc = proof.ProofRPC(endpoint)
    bundle = proof.collect(rpc, lens.ZTO)
    selected = rpc.call('eth_getBlockByNumber', [bundle['observation']['block']['number'], False])
    block = glue.cap.core.header(selected)
    lens.require(block['hash'] == bundle['observation']['block']['hash'], 'proof block changed')
    request = glue.cap.binding.read_json('shared/proof-gas-cap/zto-request.json')
    request = {**request, 'block': block}
    # The same explicit call, expected return and worker-selected allowance are retained.
    evidence = glue.cap.capture(glue.cap.core.RPC(endpoint), request)
    report = glue.evaluate(bundle, evidence, request)
    lens.require(report['status'] == 'historical_context_joined', 'fresh evidence did not join')
    return {'zto-proof.json': bundle, 'live-evidence.json': evidence,
            'live-request.json': request, 'live-result.json': report}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rpc', choices=sorted(lens.PUBLIC_SOURCES), default=lens.PUBLIC_RPC)
    p.add_argument('--fresh', action='store_true', help='collect all evidence at a newly finalized block')
    args = p.parse_args()
    try:
        expected = ['zto-proof.json', 'live-evidence.json', 'live-request.json', 'live-result.json'] if args.fresh else ['zto-proof.json']
        lens.require(not any((Path('shared/proof-gas-cap') / name).exists() for name in expected), 'output already exists')
        values = fresh(args.rpc) if args.fresh else {'zto-proof.json': capture(args.rpc)}
        documents = {name: json.dumps(value, indent=2) + '\n' for name, value in values.items()}
        lens.require(all(len(raw.encode()) < 95000 for raw in documents.values()), 'evidence too large')
        paths = [Path('shared/proof-gas-cap') / name for name in documents]
        lens.require(not any(path.exists() for path in paths), 'output already exists')
        for path in paths:
            with path.open('x') as h:
                h.write(documents[path.name])
        block = values['zto-proof.json']['observation']['block']
        print(json.dumps({'status': 'captured', 'block_decimal': lens.quantity(block['number']),
                          'block': block, 'rpc': args.rpc, 'fresh': args.fresh}))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'unavailable', 'rpc': args.rpc, 'error': str(exc)}))
        return 2

if __name__ == '__main__':
    sys.exit(main())
