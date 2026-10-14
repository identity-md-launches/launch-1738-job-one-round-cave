"""Offline replay of real saved ZTO first, then IMD code proofs."""
import json
from pathlib import Path
import code_frontier_review as tool

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent


def main():
    zto_source = tool.read_json(TOOLS / 'code-routes/zto-proof.json')
    imd_source = tool.read_json(TOOLS / 'code-routes/imd-proof.json')
    imd_target = tool.read_json(TOOLS / 'code-target-proofs/imd-target-proof.json')
    zto = tool.evaluate(zto_source, [],
                        tool.read_json(HERE / 'zto-example-review.json'), 26188209)
    imd = tool.evaluate(imd_source, [imd_target],
                        tool.read_json(HERE / 'imd-example-review.json'), 26188209)
    passed = (zto['decision'] == 'refuse'
              and zto['reasons'] == ['missing-caller-anchor']
              and zto['measured_runtimes'][0]['code_hash'] ==
              '0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d'
              and imd['decision'] == 'refuse'
              and imd['reasons'] == ['unresolved-call-operands', 'missing-caller-anchor']
              and imd['unresolved_call_site_count'] == 34)
    return {'demonstration_passed': passed,
            'ZTO': {'decision': zto['decision'], 'reasons': zto['reasons'],
                    'proved_runtimes': len(zto['measured_runtimes'])},
            'IMD': {'decision': imd['decision'], 'reasons': imd['reasons'],
                    'proved_runtimes': len(imd['measured_runtimes']),
                    'unresolved_call_site_count': imd['unresolved_call_site_count']},
            'note': 'Historical proof replay; example hash lists copied from evidence are not independent review.'}


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['demonstration_passed'] else 1)
