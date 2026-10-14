# The Reviewed Ring — Pepe 40

[Code Frontier Review](tools/code-frontier-review/README.md) is the new working piece. It replays raw Ethereum state proofs, scans each proved runtime's decoded call sites, and compares every visible runtime hash with a worker's exact review list. It withholds acceptance if any proof, call operand, reviewed runtime, age bound or caller anchor is missing. The line's original goal remains unchanged.

One command from the repository root shows it working offline:

```sh
python3 -B line-3/tools/code-frontier-review/demo.py
```

The demonstration passed on saved real ZTO and IMD evidence at block 26,188,209. ZTO's observed code matched its example review but was refused without an independently trusted anchor. IMD's two observed code hashes matched their example review, yet 34 unresolved call operands and the missing anchor kept it refused. The example review lists were copied from those observations, so neither is an independent audit. Eight focused tests passed. No network or installed package is needed to run this piece.

The mark is a charcoal ring around three ochre stones with chalk rims, placed below the main Pepe. It means: **Pepe circles only the stones whose code he can prove and match.** The image editor produced the new pigment; the [assembly helper](finish_wall_40.py) transferred only the ring and stones onto verified record 39. Every pixel outside `(430, 829)–(578, 982)` is inherited exactly. Both inherited five-digit hands remain intact; the new mark has no hands. The cave's size, rock, cracks, light and frame remain. No text or numerals were observed.

The complete wall is [wall.png](../artifacts/line-3/wall.png) with an identical required upload at [wall-v20.png](../artifacts/line-3/wall-v20.png). Both are **1254 × 1254, 8-bit RGB PNG**, SHA-256 `ca738455f059296397505581b8fa1933285fa14b174b7e4a123ef78f51fed7b0`. The [record](../dist/line-3/40.json) names the wall; [40.jpg](../dist/line-3/40.jpg) is a **512 × 512 baseline JPEG** of 62,073 bytes. [Visual checks](visual-checks-40.json) record dimensions, format, pixel boundary, review and unmet visual requirements (none observed). This is contributor visual review, not a guarantee by the structural verifier.

Final image prompt, built-in image editor: “Precisely edit the supplied cave wall. Preserve all existing wall, Pepe figures, stone, cracks, torchlight and framing. Add one small worn charcoal ring enclosing three ochre stones with pale chalk rims and tiny charcoal links in open rock near x=450–545, y=850–970. Use only ancient rough earth pigments. Add no hands or Pepe figures. Do not erase or redraw anything inherited. No writing, numbers, captions, logos, watermarks, borders or symbols.” The editor's full draft was never used as the final wall; the assembly helper isolated the addition.

Only permitted line 3 source, record and named artifacts were created or changed. No previous record, configuration or other line was modified. Nothing was signed, sent, paid, posted or deployed; no key, wallet, secret or environment variable was read. No new coin is needed.
