# Hepatocyte outline source audit

Reviewed 2026-10-03 against Hannan et al., *Production of hepatocyte-like cells
from human pluripotent stem cells*, *Nature Protocols* 8, 430–437 (2013),
[PubMed PMID 23424751](https://pubmed.ncbi.nlm.nih.gov/23424751/) and the
[full article in PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3673228/).

The local `hepatocyte_differentiation` outline is not a faithful abridgment of
that paper. The cited protocol describes a 25-day method and explicitly
distinguishes definitive endoderm, anterior definitive endoderm, hepatoblast
specification, and maturation. Its maturation stage begins on differentiation
day 12 and continues beyond day 25 for some functional readouts. The local
outline omitted the anterior-endoderm stage, used a different factor and medium
sequence, allowed a complex matrix despite the cited source's matrix-free
method, and stopped at hour 480 (20 days from its local clock, 18 days after
its encoded induction start). The source trail for these substitutions was
not recorded.

The article also distinguishes fetal-like marker expression from adult-like
function. It recommends primary hepatocytes as a positive control and describes
functional readouts as time-dependent. The local title and endpoint text did
not preserve those limits.

The compiler now marks this entry non-compilable and stores no parameters,
formulation, or experimental steps. The CLI fails closed with the review note;
the record cannot produce a checklist. This is a provenance correction, not a
replacement recipe. Reinstatement requires a fresh transcription with exact
source locators for media, matrix, developmental stages, timing, controls and
endpoints, followed by an independent source review. No wet-lab validation was
performed.
