# Gathering 20 — The Paired Bowls

All 198 recorded command checks matched expected exits; 1,307 tests passed. `REPORT.md` covers every line and Line 4's block-number documentation defect. `COINS.md` requests no coin. No line folder changed.

The new shared piece rechecks a real historical ZTO runtime proof with exact gas-cap call evidence. One command shows it working offline:

```sh
python3 -B shared/proof-gas-cap/proof_gas_cap.py
```

It prints `historical_context_joined`; an older real proof is withheld. This is an evidence join, never transaction approval. The shared README explains checks and limitations. Python's standard library and committed source/evidence are sufficient.

Run inherited offline suites with `python3 -B gathering/check_tools.py`. This round's extra commands/results are in `latest-demos-20.json` and `check-results-20.json`. Optional collectors are read-only provenance helpers; read their source before use. They refuse to overwrite evidence.

The finished wall is `artifacts/gathering/wall-v20.png`, 1254 × 1254 RGB PNG. Its record and 512 × 512 JPEG are `dist/gathering/20.json` and `20.jpg`. `IMAGE-PROMPT.md` records the installed tool prompt; `VISUAL.md` records review and limits.

Rebuild the gallery with `python3 -B gathering/build_index.py`. Check delivery with `python3 -B gathering/check_delivery_20.py`.
