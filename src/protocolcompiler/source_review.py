"""Per-parameter source review: what the paper says, checked against what is encoded.

A citation on a protocol says only that a paper exists. It does not say that the
number beside it came from that paper. For each reviewed parameter this ledger
records the sentence(s) quoted from the primary source, where they sit, the
number the source gives, the encoded value and window when the review was made,
and a verdict. ``audit()`` re-checks the ledger against the live library, so
editing a parameter without revisiting its source fails the audit instead of
drifting quietly.

What a clean row means: the encoded number agrees with the quoted sentence. It
does not mean the protocol works, that the paper is right, or that a reviewer
with wet-lab judgement signed the encoding off. A recorded disagreement is left in
place; changing a concentration or widening a window is a biological decision
that belongs to a reviewer, not to this ledger.

Quotes are short extracts of the article text, with whitespace normalized and
in-text citation numbers omitted, kept so a reader can find the sentence. They
are not a substitute for the article.
"""

from __future__ import annotations

from dataclasses import dataclass

REVIEW_DATE = "2026-10-07"
REVIEW_METHOD = (
    "Full text of each article was retrieved from PubMed Central through NCBI E-utilities "
    "(efetch, db=pmc, retmode=xml) on 2026-10-07 and read directly. Each encoded quantity was "
    "located by searching the article text. Supplementary methods, errata and later corrections "
    "were not read."
)

MATCHES = "matches_source"
INSIDE_SOURCE_RANGE = "inside_source_range"
DIFFERS = "differs_from_source"
NOT_STATED = "not_stated_in_source"
VERDICTS = frozenset({MATCHES, INSIDE_SOURCE_RANGE, DIFFERS, NOT_STATED})

STATUS_STALE = "ledger_stale"
STATUS_INCONSISTENT = "ledger_inconsistent"
STATUS_DISAGREEMENTS = "disagreements_recorded"
STATUS_CLEAN = "no_disagreements_recorded"

_MOLAR = {"nM": 1e-9, "µM": 1e-6, "mM": 1e-3, "M": 1.0}


@dataclass(frozen=True)
class ParameterReview:
    """One parameter checked against one source.

    ``source_number``/``source_unit`` are the source's number as printed. They are
    converted to the encoded unit by ``source_value`` below, so a unit slip (nM against
    µM) shows up as arithmetic rather than as a hand-typed conversion.
    """

    protocol_id: str
    parameter: str
    encoded_value: float
    encoded_unit: str
    encoded_window: tuple[float, float]
    source_locator: str
    source_quote: tuple[str, ...]
    source_tokens: tuple[str, ...]
    source_number: float | None
    source_unit: str | None
    source_range: tuple[float, float] | None
    verdict: str
    note: str
    search_terms: tuple[str, ...] = ()

    @property
    def source_value(self) -> float | None:
        """The source's number expressed in the encoded unit."""
        if self.source_number is None:
            return None
        if self.source_unit == self.encoded_unit:
            return self.source_number
        if self.source_unit in _MOLAR and self.encoded_unit in _MOLAR:
            return self.source_number * _MOLAR[self.source_unit] / _MOLAR[self.encoded_unit]
        raise ValueError(f"no conversion from {self.source_unit} to {self.encoded_unit}")


@dataclass(frozen=True)
class SourceRecord:
    pmcid: str
    pmid: str
    doi: str
    title: str
    retrieval_url: str
    retrieved_xml_sha256: str
    retrieved_xml_bytes: int
    pmc_license_statement: str
    reviews: tuple[ParameterReview, ...]


E8 = SourceRecord(
    pmcid="PMC3084903", pmid="21478862", doi="10.1038/nmeth.1593",
    title="Chemically defined conditions for human iPS cell derivation and culture",
    retrieval_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=3084903&retmode=xml",
    retrieved_xml_sha256="e9c450b80256cc574c747ce0d423b2807d6c92ad6ff2b9d8fe3fe6aeb5db2ca8",
    retrieved_xml_bytes=79074,
    pmc_license_statement=(
        "Users may view, print, copy, download and text and data- mine the content in such documents, "
        "for the purposes of academic research, subject always to the full Conditions of use: "
        "http://www.nature.com/authors/editorial_policies/license.html#terms"
    ),
    reviews=(
        ParameterReview(
            "e8_feeder_free_maintenance", "Y27632_uM", 10.0, "µM", (5.0, 10.0),
            "METHODS > Cloning Assay",
            ("Chemical concentrations for cloning assays in this report: 10 µM Blebbistatin, "
             "10 µM Y27632, or 10 µM HA100.",),
            ("10 µM Y27632",), 10.0, "µM", None, MATCHES,
            "The paper states 10 µM Y27632 for its cloning assays. It gives no duration, so the "
            "encoded 'first 24 h after passage only' restriction comes from the separately cited "
            "ROCK-inhibitor literature (Watanabe et al. 2007), which this ledger did not read. The "
            "5 µM window floor is an authoring convention.",
        ),
        ParameterReview(
            "e8_feeder_free_maintenance", "passage_confluence_percent", 80.0, "%", (70.0, 85.0),
            "METHODS > Human ES Cell Culture",
            ("Briefly, cells were washed twice with PBS/EDTA medium (0.5 mM EDTA in PBS, osmolarity "
             "340 mOsm), then incubated with PBS/EDTA for 5 minutes at 37°C.",),
            (), None, None, None, NOT_STATED,
            "The passaging description gives no confluence percentage. The only 'confluen' matches "
            "in the article text concern reprogramming (about 20% confluency before removing "
            "hydrocortisone), not passaging. The encoded 80% target with a 70-85% window is not "
            "sourced here; the library cites Beers et al. 2012 for passaging context, which this "
            "ledger did not read. The parameter note already says to passage on morphology.",
            search_terms=("confluen",),
        ),
    ),
)

DUAL_SMAD = SourceRecord(
    pmcid="PMC2756723", pmid="19252484", doi="10.1038/nbt.1529",
    title="Highly efficient neural conversion of human ES and iPS cells by dual inhibition of SMAD signaling",
    retrieval_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=2756723&retmode=xml",
    retrieved_xml_sha256="7679ea5a85a138cfbff247113b76b59310fa3c19cf25decf802a5f655a2a358c",
    retrieved_xml_bytes=55758,
    pmc_license_statement=(
        "Users may view, print, copy, and download text and data-mine the content in such documents, "
        "for the purposes of academic research, subject always to the full Conditions of use:"
        "http://www.nature.com/authors/editorial_policies/license.html#terms"
    ),
    reviews=(
        ParameterReview(
            "dual_smad_neural", "SB431542_uM", 10.0, "µM", (5.0, 10.0),
            "Materials and Methods > Neural Induction",
            ("The initial differentiation media conditions included knock out serum replacement (KSR) "
             "media with 10 nM TGF-b inhibitor (SB431542, Tocris) and 500 ng/mL of Noggin (R&D).",),
            ("10 nM",), 10.0, "nM", None, DIFFERS,
            "This is the only concentration the article text gives for SB431542. 10 nM is 0.01 µM, "
            "a thousandfold below the encoded 10 µM, and the 5-10 µM window excludes it. The encoded "
            "number is not changed on one sentence, and this ledger holds no second source for it. "
            "Resolving the disagreement needs a reviewer with the paper's supplementary methods or "
            "another primary source.",
        ),
        ParameterReview(
            "dual_smad_neural", "Noggin_ng_per_mL", 200.0, "ng/mL", (100.0, 300.0),
            "Materials and Methods > Neural Induction",
            ("The initial differentiation media conditions included knock out serum replacement (KSR) "
             "media with 10 nM TGF-b inhibitor (SB431542, Tocris) and 500 ng/mL of Noggin (R&D).",
             "Upon day 5 of differentiation, the TGF-b inhibitor was withdrawn and increasing amounts of "
             "N2 media (25%, 50%, 75%) was added to the KSR media every two days while maintaining "
             "500 ng/mL of Noggin."),
            ("500 ng/mL",), 500.0, "ng/mL", None, DIFFERS,
            "The article states 500 ng/mL twice. The encoded default of 200 ng/mL sits in a "
            "100-300 ng/mL window that excludes the source value, so a planner bound by this window "
            "cannot reproduce the cited condition. Widening a concentration window is a biological "
            "change and is left to a reviewer; the exclusion is surfaced here and by source-audit.",
        ),
        ParameterReview(
            "dual_smad_neural", "LDN193189_nM", 0.0, "nM", (0.0, 250.0),
            "Materials and Methods > Neural Induction",
            ("The initial differentiation media conditions included knock out serum replacement (KSR) "
             "media with 10 nM TGF-b inhibitor (SB431542, Tocris) and 500 ng/mL of Noggin (R&D).",),
            (), None, None, None, NOT_STATED,
            "The article uses Noggin as the BMP inhibitor and never mentions LDN-193189 or "
            "dorsomorphin, so the default of 0 follows the paper's design. The 250 nM window ceiling "
            "and the idea of LDN-193189 as a Noggin substitute come from later literature that this "
            "ledger did not read.",
            search_terms=("LDN", "dorsomorphin"),
        ),
    ),
)

GIWI = SourceRecord(
    pmcid="PMC3612968", pmid="23257984", doi="10.1038/nprot.2012.150",
    title="Directed cardiomyocyte differentiation from human pluripotent stem cells by modulating "
          "Wnt/β-catenin signaling under fully defined conditions",
    retrieval_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=3612968&retmode=xml",
    retrieved_xml_sha256="6bc3ffddb5c73429e7ce9f51bf565f2d15540f035689c3c349412798b0380562",
    retrieved_xml_bytes=106119,
    pmc_license_statement=(
        "This file is available for text mining. It may also be used consistent with the principles of "
        "fair use under the copyright law."
    ),
    reviews=(
        ParameterReview(
            "giwi_cardiac", "CHIR99021_uM", 6.0, "µM", (2.0, 12.0),
            "PROCEDURE > Cardiac differentiation with Gsk3 inhibitor and Wnt inhibitor (GiWi protocol), CRITICAL STEP note on the CHIR99021 addition",
            ("Though we identified 12 μM CHIR99021 as the optimal concentration for the six lines that "
             "we tested, other lines may respond to CHIR99021 treatment differently. Thus, optimization "
             "of CHIR99021 concentration may be required. We recommend testing 6–14 μM CHIR99021.",),
            ("12 μM", "6–14 μM"), 12.0, "µM", (6.0, 14.0), INSIDE_SOURCE_RANGE,
            "The paper's optimum for its six lines is 12 µM and its recommended test range is "
            "6-14 µM. The encoded default of 6 µM is the bottom of that range, not the optimum. The "
            "encoded 2-12 µM window admits 2-5 µM, which the paper does not recommend, and excludes "
            "13-14 µM, which it does. The line-dependence is the paper's own statement.",
        ),
        ParameterReview(
            "giwi_cardiac", "IWP2_uM", 5.0, "µM", (2.0, 5.0),
            "PROCEDURE > Cardiac differentiation with Gsk3 inhibitor and Wnt inhibitor (GiWi protocol), day 3 and day 5 steps",
            ("Day 3 (72 hours post addition of CHIR99021), prepare combined medium",
             "Add 2 μl of 5 mM IWP2 (final concentration is 5 μM) into the 2 ml combined medium.",
             "Day 5, Aspirate the medium from each well of the 12-well plate and add 2 ml/well room "
             "temperature RPMI/B27-insulin."),
            ("5 μM",), 5.0, "µM", None, MATCHES,
            "The encoded value, the day-3 addition and the 48-hour exposure (day 3 to the day-5 medium "
            "change) agree with the procedure. The paper gives no lower bound, so the 2 µM window "
            "floor is an authoring convention.",
        ),
    ),
)

SOURCE_RECORDS = (E8, DUAL_SMAD, GIWI)


def all_reviews() -> list[ParameterReview]:
    return [review for record in SOURCE_RECORDS for review in record.reviews]


def _same_glyph(text: str) -> str:
    """Treat the micro sign and the Greek mu as the same character when comparing."""
    return text.replace("μ", "µ")


def ledger_problems() -> list[str]:
    """Internal inconsistencies in the hand-authored ledger, independent of the live library.

    A verdict must follow from the numbers beside it, every non-'not stated' row must carry a
    quote that contains the tokens it relies on, and every 'not stated' row must say what was
    searched for. These checks keep the verdicts from drifting away from their own evidence.
    """
    problems = []
    seen = set()
    for review in all_reviews():
        label = f"{review.protocol_id}.{review.parameter}"
        if (review.protocol_id, review.parameter) in seen:
            problems.append(f"{label}: reviewed twice")
        seen.add((review.protocol_id, review.parameter))
        if review.verdict not in VERDICTS:
            problems.append(f"{label}: unknown verdict {review.verdict!r}")
            continue
        value, encoded = review.source_value, review.encoded_value
        if not review.source_quote:
            problems.append(f"{label}: no source quote")
        joined = _same_glyph(" ".join(review.source_quote))
        for token in review.source_tokens:
            if _same_glyph(token) not in joined:
                problems.append(f"{label}: quote does not contain {token!r}")
        if review.verdict == NOT_STATED:
            if value is not None or review.source_range is not None:
                problems.append(f"{label}: 'not stated' but a source value is recorded")
            if not review.search_terms:
                problems.append(f"{label}: 'not stated' without the search terms used")
            continue
        if value is None:
            problems.append(f"{label}: {review.verdict} needs a source value")
            continue
        low, high = review.source_range if review.source_range else (None, None)
        in_range = low is not None and low <= encoded <= high
        if review.verdict == MATCHES and encoded != value:
            problems.append(f"{label}: 'matches' but encoded {encoded} != source {value}")
        if review.verdict == INSIDE_SOURCE_RANGE and not (in_range and encoded != value):
            problems.append(f"{label}: 'inside source range' needs a range containing the encoded "
                            "value that is not the source's own value")
        if review.verdict == DIFFERS and (encoded == value or in_range):
            problems.append(f"{label}: 'differs' but the encoded value equals or lies inside the source")
    return problems


def _compiled_parameters(library):
    """Map protocol id -> {parameter name: Parameter} for every compilable library entry."""
    result = {}
    for protocol_id, factory in library.items():
        protocol = factory()
        if getattr(protocol, "compilable", True):
            result[protocol_id] = {item.name: item for item in protocol.parameters}
    return result


def audit(library=None) -> dict:
    """Check every recorded review against the live protocol encodings.

    ``library`` maps protocol id to a zero-argument factory returning a ``Protocol``
    (the shape of ``protocolcompiler.library.LIBRARY``). A review whose recorded encoded
    value or window no longer matches the library is ``ledger_stale``: the parameter
    changed without its source being revisited.
    """
    if library is None:
        from protocolcompiler.library import LIBRARY as library
    live = _compiled_parameters(library)
    rows, stale, conflicts = [], [], []
    for record in SOURCE_RECORDS:
        for review in record.reviews:
            window = (float(review.encoded_window[0]), float(review.encoded_window[1]))
            row = {
                "protocol_id": review.protocol_id,
                "parameter": review.parameter,
                "source_pmcid": record.pmcid,
                "source_locator": review.source_locator,
                "source_quote": list(review.source_quote),
                "search_terms": list(review.search_terms),
                "source_number": review.source_number,
                "source_unit": review.source_unit,
                "source_value_in_encoded_unit": review.source_value,
                "source_range": list(review.source_range) if review.source_range else None,
                "ledger_encoded_value": review.encoded_value,
                "ledger_encoded_unit": review.encoded_unit,
                "ledger_encoded_window": list(window),
                "verdict": review.verdict,
                "note": review.note,
            }
            parameters = live.get(review.protocol_id)
            parameter = parameters.get(review.parameter) if parameters is not None else None
            if parameters is None:
                row["ledger_status"] = "protocol_absent"
            elif parameter is None:
                row["ledger_status"] = "parameter_absent"
            else:
                live_window = (float(parameter.low), float(parameter.high))
                row.update(live_encoded_value=float(parameter.value), live_encoded_unit=parameter.unit,
                           live_encoded_window=list(live_window))
                same = (float(parameter.value) == review.encoded_value and live_window == window
                        and parameter.unit == review.encoded_unit)
                row["ledger_status"] = "current" if same else STATUS_STALE
            if row["ledger_status"] != "current":
                stale.append(row)
            value, source_range = review.source_value, review.source_range
            row["source_value_within_encoded_window"] = (
                None if value is None else window[0] <= value <= window[1])
            row["source_range_within_encoded_window"] = (
                None if source_range is None else window[0] <= source_range[0] and source_range[1] <= window[1])
            row["encoded_window_extends_beyond_source_range"] = (
                None if source_range is None else window[0] < source_range[0] or window[1] > source_range[1])
            if (row["source_value_within_encoded_window"] is False
                    or row["source_range_within_encoded_window"] is False
                    or row["encoded_window_extends_beyond_source_range"] is True):
                conflicts.append(row)
            rows.append(row)

    reviewed = {(review.protocol_id, review.parameter) for review in all_reviews()}
    unreviewed = sorted(f"{protocol_id}.{name}" for protocol_id, parameters in live.items()
                        for name in parameters if (protocol_id, name) not in reviewed)
    inconsistent = ledger_problems()
    n_differs = sum(1 for row in rows if row["verdict"] == DIFFERS)
    if stale:
        status = STATUS_STALE
    elif inconsistent:
        status = STATUS_INCONSISTENT
    elif n_differs or conflicts:
        status = STATUS_DISAGREEMENTS
    else:
        status = STATUS_CLEAN
    return {
        "schema_version": 1,
        "status": status,
        "review_date": REVIEW_DATE,
        "review_method": REVIEW_METHOD,
        "sources": [
            {"pmcid": record.pmcid, "pmid": record.pmid, "doi": record.doi, "title": record.title,
             "retrieval_url": record.retrieval_url, "retrieved_xml_sha256": record.retrieved_xml_sha256,
             "retrieved_xml_bytes": record.retrieved_xml_bytes,
             "pmc_license_statement": record.pmc_license_statement,
             "n_reviewed_parameters": len(record.reviews)}
            for record in SOURCE_RECORDS
        ],
        "counts": {
            "reviewed": len(rows),
            MATCHES: sum(1 for row in rows if row["verdict"] == MATCHES),
            INSIDE_SOURCE_RANGE: sum(1 for row in rows if row["verdict"] == INSIDE_SOURCE_RANGE),
            DIFFERS: n_differs,
            NOT_STATED: sum(1 for row in rows if row["verdict"] == NOT_STATED),
            "window_conflicts_with_source": len(conflicts),
            "stale_ledger_entries": len(stale),
        },
        "unreviewed_parameters": unreviewed,
        "ledger_problems": inconsistent,
        "reviews": rows,
        "limitations": [
            "A matching value means the encoded number agrees with the quoted sentence. It does not "
            "establish that the protocol works, that the source is correct, or that a qualified "
            "reviewer approved the encoding.",
            "Quotes come from the article text retrieved on the review date; the retrieved bytes are "
            "identified by hash, and PubMed Central may since have changed. Supplementary methods, "
            "errata and later corrections were not read.",
            "Recorded disagreements are left in place rather than silently resolved. Changing a "
            "concentration or a window is a biological decision for a reviewer.",
            "'Not stated' means a text search of the retrieved article found no such value, not that "
            "the authors never used one.",
            "Parameters listed as unreviewed have no source check at all; a citation on the protocol "
            "is not a check of the value beside it.",
        ],
    }
