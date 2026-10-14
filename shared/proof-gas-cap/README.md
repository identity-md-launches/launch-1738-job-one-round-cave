# Proof and Gas Cap Context

Reuse Line 3's raw runtime-proof checker with Line 4's exact gas-capped call
rehearsal. This gives swap and permission workers one offline report containing
both code identity and a reviewed historical call, joined only at the same
Ethereum chain, target, block height and block hash. Both ancestor checks are
recomputed from raw evidence; saved success flags are not accepted.

From the repository root:

```sh
python3 -B shared/proof-gas-cap/proof_gas_cap.py
```

Tried on 2026-10-14: `historical_context_joined`, exit 0. The real ZTO code proof
was read from dRPC at block **26,190,345** (`0x18fa209`), hash
`0x63af72b9379fba0e92a775299a9708eadffdd12395b382b481ce7976567d361c`.
PublicNode returned a historical-state-unavailable error first. The proof
verifier reconstructed the header and checked account inclusion, runtime hash
and the two measured proxy slots. The unchanged copied Line 4 evidence reports
matching `totalSupply()` bytes with provider-default gas and 30,000 gas at that
exact block. Its recorded transport is contributor-relay; upstream identity is
not independently authenticated. `provenance.json` records copied file hashes.

An older real proof is deliberately withheld, exit 2:

```sh
python3 -B shared/proof-gas-cap/proof_gas_cap.py --proof line-3/tools/code-routes/zto-proof.json
```

All six tests passed, including both real evidence cases, changed requests,
tampered runtimes and provider failures. Positive mocked context cases are
explicit simulations and are not saved as observations.

```sh
python3 -B -m unittest discover -s shared/proof-gas-cap -p 'test_*.py' -v
```

Python 3.10+ and standard library only. Keep the committed sibling line folders
and `shared/evidence-alignment` available; no package installation or network is
needed for the commands above. Inputs must be workspace-local JSON smaller than
95 KB, with duplicate keys and non-finite values refused. Exit 1 means invalid
input; exit 2 means the join is withheld. The collector in
`gathering/capture_gas_cap_proof.py` is a separate, optional read-only provenance
helper; it refuses to overwrite evidence.

This does not authenticate the consensus anchor or the provider's call results,
prove contract behavior, measure consumed gas, recommend a transaction gas
limit, establish authority, or grant a swap bound. Missing constant proofs and
unresolved calls remain visible. `transaction_approved` is always false.
The simulated PoolManager sender is a real contract address, not an available
transaction origin. Nothing is signed, sent, deployed, paid or posted.
