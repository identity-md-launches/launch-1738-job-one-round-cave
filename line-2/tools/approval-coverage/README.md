# Approval Coverage Map

Map the block intervals actually scanned for ERC-20 `Approval` events in saved raw Allowance Lens observations. The result gives a worker exact missing intervals and read-only commands for scanning them. It keeps the distinct owner–spender pairs already seen, including pairs from a scan followed by an empty scan. Python 3.10+ and the standard library suffice; the adjacent Permission Gate and Allowance Lens sources are included in this line.

## One command to see it working

From the repository root:

```sh
python3 -B line-2/tools/approval-coverage/approval_coverage.py
```

The default command replays two **real saved ZTO Ethereum observations**. The first scanned blocks 26,182,252–26,183,751 and saw 27 Approval logs covering 19 owner–spender pairs. The later 50-block scan covered 26,184,307–26,184,356 and saw zero logs. When tried locally, the tool reported `gaps_remain` for the **555 unscanned blocks 26,183,752–26,184,306**, retained all 19 known pairs, and suggested a bounded historical read of that gap. Six focused offline tests passed. This command makes no network request and does not claim a new chain observation.

Repeat `--input PATH` to assess 1–16 raw Allowance Lens `approval_window` snapshots. `--from-block N --to-block N` sets an inclusive target; without them, the target runs from the earliest supplied window start to the latest end. Inputs must be workspace JSON files at most 96 KiB each. Duplicate JSON keys are rejected. Snapshots must agree on Ethereum chain, ZTO or IMD, token decimals, and the optional owner filter. Existing Allowance Lens validation checks the underlying logs and raw token calls. Conflicting headers or logs at the same height or position are rejected. The target is limited to 100,001 blocks; scan suggestions are split into chunks of at most 2,000 blocks. Exit 0 means a valid report, including a gap report; exit 1 is invalid input, and exit 2 is command syntax error.

The suggested commands are **read-only** historical `Allowance Lens --live` calls. Run one only if a public RPC has the needed history, save its raw observation with that tool's `--save`, then assess the expanded set. This tool never signs, sends, pays, posts, or changes an allowance.

`continuous_event_scan_in_target` describes event-window coverage only. It is never a complete wallet audit: approvals before the chosen interval can persist, and even a continuous scan needs current same-block `allowance()` reads for every known pair before policy review. Unknown spenders, Permit2 sub-permissions, unused signatures, other tokens and nonstandard authorizations remain outside the result. Saved RPC data is trusted historical evidence, not a proof of present canonicality.

Run the focused tests with `python3 -B -m unittest discover -s line-2/tools/approval-coverage -p 'test_*.py' -v`.
