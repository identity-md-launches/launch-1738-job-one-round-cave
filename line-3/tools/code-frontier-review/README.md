# Code Frontier Review

Match every runtime visible in a raw-proof-backed, bounded Ethereum call scan against a worker's exact reviewed hash list. The check reconstructs the supplied account, storage, header and runtime proofs on every run. It refuses a missing target proof, unresolved call operand, empty call target, proxy routing candidate, unreviewed runtime, wrong hash, stale code evidence, or absent caller anchor. A saved frontier result cannot stand in for raw evidence.

Run one command from the repository root, offline with Python 3.9+ and only the standard library:

```sh
python3 -B line-3/tools/code-frontier-review/demo.py
```

**What happened when tried:** `demonstration_passed` was `true`. Real saved ZTO evidence at block **26,188,209** matched its one example reviewed hash and had no open sites, but the tool refused it because no independent caller anchor was supplied. Real saved IMD evidence at the same block matched both example hashes and had its constant target proved; it was refused for **34 unresolved call operands** and the missing anchor. The example review hashes were copied from these historical observations for demonstration. They are not independent audits, approved code, or proof of authenticity. Eight focused tests passed.

To review your own evidence, supply raw Code Proof bundles and an independently chosen exact review document:

```text
python3 -B line-3/tools/code-frontier-review/code_frontier_review.py --source SOURCE_PROOF.json --target-proof DISCOVERED_TARGET_PROOF.json --review REVIEW.json --as-of-block DECIMAL_HEIGHT --anchor-hash INDEPENDENT_EXECUTION_BLOCK_HASH
```

The uppercase fields denote caller inputs, not stand-ins to execute. Repeat `--target-proof` for each recursively discovered constant target, at most sixteen. All input files must resolve inside the workspace, be at most 100,000 bytes, and have no duplicate JSON keys. `--anchor-hash` must be independently trusted; copying it from a proof checks equality only. The explicit decimal height is the caller's reference, never inferred to be today's chain height.

The review document has exactly `schema` (`code-frontier-review-v1`), `chain_id` (integer `1`), `source_target`, `max_age_blocks` (integer uint64), and `runtimes` (1–96 unique `{address, code_hash}` rows). The real example JSON files show the shape. Each address and code hash is exact; there are no wildcards. The review must include the source address, and the measured set must equal the reviewed set. Hashes use Ethereum Keccak-256 of **deployed runtime bytes**, including compiler metadata, not source or creation code. The output includes the normalized review digest, each proved runtime and each unresolved site.

Exit **0** means only that the exact reviewed identities match the visible bounded scan, the explicit age bound and anchor equality hold, and the scan has no open decoded call sites under this analyzer. Exit **3** gives a structured refusal. Exit **1** rejects invalid or conflicting inputs with no success JSON, and **2** is argument syntax failure. No exit authorizes a transaction.

This extends Code Dependency Frontier and depends on its committed sibling modules: Code Targets, Code Calls, Code Surface/Opcodes, Code Ancestry, Code Proof and Code Lens/Keccak. No network, package installation, wallet, key, environment variable, signature, transaction, payment, post or deployment is involved. It uses only the Python standard library. Run the checks with:

```sh
python3 -B -m unittest discover -s line-3/tools/code-frontier-review -p 'test_*.py' -v
```

The call inventory is structural and bounded. Locally constant operands depend on successful local linear execution; unresolved operands refuse, and apparently closed scans can still miss custom routing or dynamic behavior. Recognized proxy signals require a separate path review, so this gate refuses them. The review and anchor must be independently selected and trusted. Matching evidence is historical; it does not prove source equivalence, reachable behavior, dependency completeness, consensus, finality, current code, semantic safety or permission to transact.
