# Gas Cap Rehearsal and record 40 checks

The goal, all old records, existing tools and protected configuration are
unchanged. The gathering report lists no current broken Line 4 tool.

Ran the following from the repository root:

```sh
python3 -B -m unittest discover -s line-4/tools/gas-cap-rehearsal -p 'test_*.py' -v
python3 -B line-4/tools/gas-cap-rehearsal/gas_cap.py demo
python3 -B line-4/tools/gas-cap-rehearsal/gas_cap.py check line-4/tools/gas-cap-rehearsal/zto-tight-evidence.json line-4/tools/gas-cap-rehearsal/zto-tight-request.json
```

All 21 tests passed. The offline real-ZTO demo returned `matched` (exit 0).
The separately captured real-ZTO tight-allowance pair returned `inconclusive`
(exit 2), retaining the provider's `intrinsic gas too low` error. This is the
expected refusal, not a failing test or an inferred proof of out-of-gas.
The two pairs were independently collected through the contributor-provided
Ethereum transport, with PublicNode source attribution, at block 26,190,857.
No transport address is saved. Nothing was signed, broadcast, paid or deployed.

The structural image inspector accepted the PNG at 1254 × 1254 and the JPEG
at 512 × 512. Both final images were viewed. The standard-library conservation
check found exactly 2,725 changed pixels inside the addition rectangle and
zero outside. The SHA-256 matches the new record's image URL. See
`VISUAL-40.md` for the inherited digit-count limitation and visual review.
These checks are local observations, with no independent authority.
