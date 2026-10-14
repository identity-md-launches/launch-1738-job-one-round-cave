#!/usr/bin/env python3
"""Keep a code-identity report and a gas rehearsal from being joined by address alone."""
import argparse
import json
import re
from pathlib import Path
import sys

ROOT = Path.cwd().resolve()

def load(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or path.stat().st_size > 100_000:
        raise ValueError("input must be a small file inside the workspace")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key: " + key)
            value[key] = item
        return value
    with path.open() as handle:
        return json.load(handle, object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")))

def context(chain, target, block):
    if type(chain) is not int or chain != 1:
        raise ValueError("context requires Ethereum chain ID 1")
    if not isinstance(target, str) or not re.fullmatch(r"0x[0-9a-f]{40}", target):
        raise ValueError("context requires a lowercase contract address")
    if not isinstance(block, dict):
        raise ValueError("missing block context")
    number, digest = block.get("number"), block.get("hash")
    if not isinstance(number, str) or not re.fullmatch(r"0x(?:0|[1-9a-f][0-9a-f]*)", number):
        raise ValueError("context requires a canonical block quantity")
    if not isinstance(digest, str) or not re.fullmatch(r"0x[0-9a-f]{64}", digest):
        raise ValueError("context requires a full block hash")
    return chain, target, number, digest

def align(code, gas):
    if code.get("schema") != "code-target-proofs-result-v1":
        raise ValueError("not a Code Target Proofs result")
    if gas.get("schema") != "gas-lens-v1":
        raise ValueError("not a Gas Lens report")
    code_block, gas_block = code.get("code_block"), gas.get("block")
    source, call = code.get("source_target"), gas.get("call")
    if not isinstance(code_block, dict) or not isinstance(gas_block, dict) or not isinstance(call, dict):
        raise ValueError("missing required context")
    same = (context(code.get("chain_id"), source, code_block)
            == context(gas.get("chain_id"), call.get("to"), gas_block))
    return {"schema": "evidence-alignment-v1", "status": "aligned" if same else "not_aligned",
            "chain_id": {"code": code.get("chain_id"), "gas": gas.get("chain_id")},
            "target": {"code": source, "gas": call.get("to")},
            "block": {"code": code_block, "gas": gas_block}, "gas_verdict": gas.get("verdict"),
            "code_decision": code.get("decision"),
            "scope": "Alignment only: this neither authenticates either report nor proves code behavior, call success, gas sufficiency, authority, safety, or future execution."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code", nargs="?", default="line-3/tools/code-target-proofs/demo-result.json")
    parser.add_argument("gas", nargs="?", default="shared/evidence-alignment/zto-gas-report.json")
    args = parser.parse_args()
    try:
        code = load(args.code)
        if "results" in code:
            code = next(item["result"] for item in code["results"] if item["token"] == "ZTO")
        print(json.dumps(align(code, load(args.gas)), indent=2))
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        raise SystemExit(2)

if __name__ == "__main__":
    main()
