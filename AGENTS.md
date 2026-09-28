# Agent instructions — cell-protocol-compiler

Work only in this repository. Three published workflows are encoded:
`e8_feeder_free_maintenance` (Chen 2011), `dual_smad_neural` (Chambers 2009),
`giwi_cardiac` (Lian 2013). The validator refuses out-of-window concentrations,
missing QC gates, absurd volumes, and feed gaps. LDN defaults to 0 and is not
stacked on Noggin.

## Do not

- Invent a new biological protocol or widen a concentration window.
- Set GiWi CHIR default to 12 µM. The encoded default is 6 µM inside 2–12, with the paper's 12 µM called out as line-dependent.
- Add GMP, IND, or “put cells in a person” text.
- Treat a passing checklist as proof the culture will work.
- Silently rewrite narrative steps when a numeric parameter changes. The validator does not keep those in sync; a change must update both and the hash test.

## First commands

```bash
python -m unittest discover -s tests -v
PYTHONPATH=src python3 -m protocolcompiler.cli giwi_cardiac --markdown
```

## Improve, in this order

1. Add a failing test for any rule you tighten (non-finite value, feed gap, missing gate).
2. If a number disagrees with the cited paper, fix the encoding or the comment, and say which sentence in the paper you used. Do not “update” from a blog.
3. Optional integration: export the legal box in a form `diffmedia-loop` can read, without searching doses here.
4. No new workflow ids in a drive-by commit.

## Done when

Tests pass and `protocol_sha256` still covers the full input dataclass.
