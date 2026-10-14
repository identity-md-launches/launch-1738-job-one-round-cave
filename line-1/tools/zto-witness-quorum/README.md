# ZTO Witness Quorum

Require a receiver-chosen quorum of saved ZTO/IMD Uniswap v4 pool and Quoter captures before releasing the existing bounded planning minimum. It recomputes every capture, requires the same anchored pool state and complete local fill, and requires both distinct source labels and a caller-selected number of distinct receiver-assigned provider groups. It uses only Python's standard library and the committed Line 1 Witness Policy/Replay/Path sources.

From the repository root, this network-free command shows it working:

```sh
python3 -B line-1/tools/zto-witness-quorum/zto_witness_quorum.py --demo
```

The demo replays the saved real 1-ZTO historical capture at Ethereum block 26,184,260 twice and correctly prints `withheld`: it has a duplicate PublicNode label and only one assigned provider group, so it releases no minimum. Demo exit zero means the demonstration ran; it is not trade permission.

For a receiver-authored request:

```sh
python3 -B line-1/tools/zto-witness-quorum/zto_witness_quorum.py --request YOUR_REQUEST.json
```

The strict request has schema `zto-witness-quorum-request-v1`, a complete embedded `zto-witness-policy-v1` policy, `minimum_distinct_groups` (2–8), decimal `amount`, integer `slippage_bps`, and 2–8 `{ "snapshot": "...", "quoter": "..." }` workspace-relative candidate pairs. Candidate paths are read through the inherited bounded strict JSON reader. Exit 0 means accepted, 2 means withheld, and 1 means malformed input/file error.

What happened when tried: four focused offline tests passed. The real single-source demo withheld. A positive test uses three explicitly synthetic relabeled copies in three receiver groups; it tests policy plumbing only and is not independent-provider evidence. Receiver group assignments, endpoint labels, archived RPC data, chain authenticity, current liquidity, token settlement, gas, MEV and future execution remain unproved. A copied capture can pass if a receiver incorrectly treats relabeled sources as independent. No wallet, key, secret, signing, sending, payment, posting, deployment, package, or network call is used.
