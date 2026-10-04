# Cell protocol compiler

Machine-readable research checklists for three published pluripotent-cell workflows, plus a fail-closed source-audit record for one hepatocyte outline. The validator rejects missing QC gates, absurd well volumes, hood collisions, and small-molecule values outside the encoded source window.

This is a protocol formalization exercise. It is not a lab and it does not authorize one.

## Workflows

| id | What it abridges | Source |
|---|---|---|
| `e8_feeder_free_maintenance` | Feeder-free maintenance on the academic E8 formulation (Chen 2011), EDTA passage context, ROCK inhibitor for 24 h | [10.1038/nmeth.1593](https://doi.org/10.1038/nmeth.1593) |
| `dual_smad_neural` | Adherent neural induction, 10 µM SB431542 + 200 ng/mL Noggin, SRM toward N2 | [10.1038/nbt.1529](https://doi.org/10.1038/nbt.1529) |
| `giwi_cardiac` | Wnt activation then Wnt inhibition. CHIR defaults to 6 µM inside 2–12, not to the paper's 12 µM example | [10.1038/nprot.2012.150](https://doi.org/10.1038/nprot.2012.150) |
| `hepatocyte_differentiation` | Quarantined source-audit record; it emits no recipe until a fresh transcription is reviewed | [Source audit](docs/hepatocyte-source-audit.md) |

LDN-193189 is a parameter on the neural checklist and defaults to **0**. Later protocols use ~100 nM as a **substitute** for Noggin. This compiler does not stack them.

## Non-goals

- GMP batch records, IND text, or biosafety approval
- Instructions for putting cells, genes, or media into a person
- A claim that a concentration inside the published window will work on your line
- Proprietary medium recipes beyond the academic formulation printed in Chen et al. 2011. "Essential 8" is a commercial trademark; the table in this repo is the paper's list

## Run

```bash
make test
PYTHONPATH=src python3 -m protocolcompiler.cli giwi_cardiac --markdown
PYTHONPATH=src python3 -m protocolcompiler.cli dual_smad_neural
PYTHONPATH=src python3 -m protocolcompiler.cli dual_smad_neural --constraints
```

`hepatocyte_differentiation` intentionally exits with an error. The previous
outline materially diverged from its cited source and must not be used as a
laboratory instruction. See the [source audit](docs/hepatocyte-source-audit.md).

Python 3.10+. No third-party packages.

The validator's feed-gap rule is there because a checklist that skips from day 0 to day 7 without a medium change is how cultures die. It is not a new biological finding.

## Where this sits

Pair it with [brightfield-colony-qc](https://github.com/dylanstechmann/brightfield-colony-qc) for a morphology gate and [diffmedia-loop](https://github.com/dylanstechmann/diffmedia-loop) when the next plate of doses is the actual question. The compiler does not search doses. It refuses ones outside the encoded window.

## License

MIT.

## Reproducible validation (v0.2)

Install with `python -m pip install -e .`. Compiled JSON now contains a canonical
`protocol_sha256` over the complete input dataclass. Archive it with a review
so the reviewed checklist can be identified exactly.

Validation rejects nonfinite schedule/parameter/formulation values, duplicate
parameter names and invalid feed-gap limits. It checks the interval from the
last feed to the endpoint as well as intervals between feeds.
It also requires exactly one endpoint, no active step after it, and an explicit
QC gate on an executable step. Gates must be lists of nonblank strings. A
narrative note, blank gate label, or empty `qc` step does not count as a gate.

This checks encoded consistency, not the accuracy of a source transcription.
Programmatically changing a parameter does not rewrite the narrative steps;
review them together. No new biological protocol or parameter range was added
in this revision.

## Versioned planner constraints (v0.3)

`--constraints` prints a machine-readable export of the same published
windows: parameter name, unit, `low`–`high`, the compiled default, required
flags, per-step required gates and reagents, the allowed action vocabulary,
the medium-change gap limit, and mutually exclusive alternatives (Noggin and
LDN-193189) as data. It carries the `protocol_sha256` of the exact source
record so a planner can pin which checklist version bounded its search. A
quarantined source record exports nothing.

[diffmedia-loop](https://github.com/dylanstechmann/diffmedia-loop) consumes
this export instead of maintaining a divergent copy of the windows. A
widening of any window here requires regenerating that bundle; its sync test
fails first. The export states limits a search is allowed to use. It is not
an optimum, and it is not a dose.

Known workflows are checked against their source-reviewed factory requirements.
Clearing a candidate's required-field metadata cannot remove gates or reagents;
changing units, widening parameter windows, or relaxing the feed-gap limit is
rejected. Inactive alternatives still require finite, ordered bounds. Narrower
windows and valid parameter values remain available for an explicit checklist
variant; numeric and narrative changes still require review together.
