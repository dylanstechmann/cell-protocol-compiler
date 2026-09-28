"""Abridged checklists of three published workflows.

Concentrations are taken from the cited papers so they can be checked.
They are not optimized for a cell line you have not tested, and they are
not instructions for clinical manufacturing.
"""

from __future__ import annotations

from protocolcompiler.schema import FormulationComponent, Parameter, Protocol, Step

NONCLAIMS = [
    "Research checklist only. Not for administration to humans.",
    "Not a GMP batch record, not an IND section, and not a biosafety approval.",
    "Line-to-line behavior is not guaranteed by a concentration that worked in the source paper.",
]


def maintenance() -> Protocol:
    return Protocol(
        id="e8_feeder_free_maintenance",
        title="Feeder-free pluripotent maintenance (published E8 formulation)",
        citation="Chen et al., Nature Methods 2011; passaging context Beers et al., Nature Protocols 2012; ROCK inhibitor Watanabe et al., Nature Biotechnology 2007.",
        doi="10.1038/nmeth.1593",
        biosafety="BSL-2 human pluripotent cell culture in a certified Class II cabinet.",
        vessel="One well of a 6-well plate, 2 mL medium exchanges.",
        max_hours_between_medium_changes=30,
        summary=(
            "Daily feeding of a published E8-class formulation on a recombinant matrix, "
            "enzyme-free EDTA passage around 80% confluence. Abridged. Confirm coating "
            "and contact times against the papers and the lot of matrix you actually have."
        ),
        parameters=[
            Parameter("Y27632_uM", 10, "µM", 5, 10,
                      "First 24 h after passage only. Watanabe et al. 2007."),
            Parameter("passage_confluence_percent", 80, "%", 70, 85,
                      "Passage on morphology, not on a clock, if the culture disagrees with this target."),
        ],
        formulation=[
            FormulationComponent("DMEM/F12", 1, "base", "Chen et al. 2011."),
            FormulationComponent("L-ascorbic acid-2-phosphate magnesium", 64, "mg/L"),
            FormulationComponent("sodium selenite (paper wording: sodium selenium)", 14, "µg/L"),
            FormulationComponent("insulin", 19.4, "mg/L"),
            FormulationComponent("holo-transferrin", 10.7, "mg/L"),
            FormulationComponent("sodium bicarbonate", 543, "mg/L"),
            FormulationComponent("FGF2", 100, "µg/L"),
            FormulationComponent("TGFβ1 (or NODAL 100 µg/L)", 2, "µg/L"),
            FormulationComponent("osmolarity target", 340, "mOsm", "pH 7.4 in the paper."),
        ],
        steps=[
            Step("coat", 0, "Coat the well",
                 "Recombinant vitronectin or laminin-521 per the matrix vendor. Do not reuse a coating time from memory.",
                 "coat", hood_minutes=15, reagents=["matrix"]),
            Step("seed", 0.5, "Seed",
                 "Enzyme-free EDTA dissociation (0.5 mM is the common published condition; titrate contact time). "
                 "Resuspend in maintenance medium with Y-27632.",
                 "seed", hood_minutes=20, volume_ml=2,
                 reagents=["E8 formulation", "Y-27632", "0.5 mM EDTA"],
                 gates=["morphology"]),
            Step("feed_24", 24, "Daily feed",
                 "Full medium exchange. Rock inhibitor comes off after the first day.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["E8 formulation"],
                 gates=["morphology"]),
            Step("feed_48", 48, "Daily feed", "Full medium exchange.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["E8 formulation"],
                 gates=["morphology"]),
            Step("feed_72", 72, "Daily feed", "Full medium exchange. Plan the passage if confluence is in range.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["E8 formulation"],
                 gates=["morphology"]),
            Step("passage", 96, "Passage",
                 "EDTA passage into a fresh coated well. Send a sister well to identity/karyotype on the lab schedule, not every passage by default.",
                 "passage", hood_minutes=25, volume_ml=2,
                 reagents=["E8 formulation", "Y-27632", "0.5 mM EDTA"],
                 gates=["morphology", "confluence"]),
            Step("mycoplasma", 97, "Sterility gate",
                 "Mycoplasma PCR or a validated biochemical assay on a schedule (monthly is a common floor, not a regulation cited here). Quarantine if positive.",
                 "qc", hood_minutes=15, gates=["mycoplasma"]),
            Step("endpoint", 98, "Culture is maintained, not differentiated",
                 "Endpoint of this checklist is an undifferentiated culture with a fresh passage. It is not a differentiated product.",
                 "endpoint", hood_minutes=5, gates=["morphology"]),
        ],
        non_claims=list(NONCLAIMS) + [
            "Essential 8 is a trademark of a commercial medium. This list is the academic formulation in Chen et al. 2011, not a commercial batch record.",
        ],
    )


def dual_smad() -> Protocol:
    return Protocol(
        id="dual_smad_neural",
        title="Adherent neural induction by dual SMAD inhibition",
        citation="Chambers et al., Nature Biotechnology 2009. LDN-193189 is noted only as a substitute some later protocols use in place of Noggin.",
        doi="10.1038/nbt.1529",
        biosafety="BSL-2 human pluripotent cell culture in a certified Class II cabinet.",
        vessel="Adherent well, induction volumes matched to the vessel (2 mL shown).",
        max_hours_between_medium_changes=50,
        summary=(
            "Abridged Chambers dual-SMAD induction: SB431542 plus Noggin, then a graded "
            "shift from KSR-based SRM toward N2. Their day 0 is hour 24 on this clock "
            "because plating happens first. PAX6 up and OCT4 down by about day 7 of induction "
            "is the paper's phenotype, not a yield you can assume."
        ),
        parameters=[
            Parameter("SB431542_uM", 10, "µM", 5, 10, "Chambers et al. 2009 used 10 µM."),
            Parameter("Noggin_ng_per_mL", 200, "ng/mL", 100, 300, "Chambers et al. 2009 used 200 ng/mL."),
            Parameter("LDN193189_nM", 0, "nM", 0, 250,
                      "Leave at 0 to follow Chambers (Noggin). 100 nM is a later substitute for Noggin, not an addition to it."),
        ],
        steps=[
            Step("coat", 0, "Coat", "Matrigel or the matrix used in the lab's approved SOP.",
                 "coat", hood_minutes=15, reagents=["matrix"]),
            Step("seed", 0.5, "Plate pluripotent cells",
                 "Density changes the CNS versus neural-crest ratio in this protocol family. Record the cells/cm2 you actually plate.",
                 "seed", hood_minutes=20, volume_ml=2, reagents=["maintenance medium", "Y-27632"],
                 gates=["morphology"]),
            Step("induct_0", 24, "Induction day 0",
                 "Switch to KSR-based SRM with SB431542 and Noggin. LDN-193189 is not combined with Noggin here; it is a substitute in later writeups.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["SRM", "SB431542", "Noggin"]),
            Step("induct_1", 48, "Induction day 1", "Fresh SRM with the same two inhibitors.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["SRM", "SB431542", "Noggin"]),
            Step("induct_2", 72, "Induction day 2", "Fresh SRM with the same two inhibitors.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["SRM", "SB431542", "Noggin"]),
            Step("induct_4", 120, "Induction day 4", "SRM:N2 at 3:1, inhibitors still present.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["SRM", "N2", "SB431542", "Noggin"]),
            Step("induct_6", 168, "Induction day 6", "SRM:N2 at 1:1.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["SRM", "N2", "SB431542", "Noggin"]),
            Step("pax6_gate", 192, "Marker gate",
                 "Paper's early phenotype is OCT4 down and PAX6 up by about day 7. Use qPCR or immunostaining. Do not call the well neural from morphology alone.",
                 "qc", hood_minutes=20, gates=["OCT4", "PAX6"]),
            Step("induct_8", 216, "Induction day 8", "SRM:N2 at 1:3.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["SRM", "N2", "SB431542", "Noggin"]),
            Step("passage_10", 264, "Induction day 10 passage",
                 "Passage en bloc or as single cells onto fresh matrix, as in the two variations of the protocol. This checklist stops at the passage decision.",
                 "passage", hood_minutes=25, volume_ml=2, reagents=["N2"], gates=["morphology"]),
            Step("endpoint", 265, "Neurectoderm checkpoint",
                 "Endpoint is a research intermediate, not a graft.",
                 "endpoint", hood_minutes=5, gates=["PAX6"]),
        ],
        non_claims=list(NONCLAIMS),
    )


def giwi() -> Protocol:
    return Protocol(
        id="giwi_cardiac",
        title="Wnt-modulated cardiomyocyte differentiation (GiWi)",
        citation="Lian et al., Nature Protocols 2013. CHIR99021 is line-dependent; the protocol's worked example used 12 µM on their lines.",
        doi="10.1038/nprot.2012.150",
        biosafety="BSL-2 human pluripotent cell culture in a certified Class II cabinet.",
        vessel="One well of a 6-well plate.",
        max_hours_between_medium_changes=50,
        summary=(
            "Abridged GiWi: expand to confluence, 24 h of a GSK3 inhibitor (CHIR99021) in RPMI/B-27 "
            "minus insulin, then a Wnt inhibitor (IWP2) starting at differentiation day 3. "
            "Beating and cardiac troponin are the paper's readouts. Titrate CHIR per line."
        ),
        parameters=[
            Parameter("CHIR99021_uM", 6, "µM", 2, 12,
                      "Default is mid-window, not the paper's 12 µM example. Titrate. Lian et al. 2013."),
            Parameter("IWP2_uM", 5, "µM", 2, 5,
                      "Lian et al. applied 5 µM IWP2 at differentiation day 3 for 48 h."),
        ],
        steps=[
            Step("coat", 0, "Coat", "Matrix used for the maintenance culture.",
                 "coat", hood_minutes=15, reagents=["matrix"]),
            Step("seed", 0.5, "Seed for expansion",
                 "Seed so the well is confluent at hour 96. The differentiation does not start at plating.",
                 "seed", hood_minutes=20, volume_ml=2, reagents=["maintenance medium", "Y-27632"]),
            Step("feed_24", 24, "Maintenance feed", "Full exchange.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["maintenance medium"]),
            Step("feed_48", 48, "Maintenance feed", "Full exchange.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["maintenance medium"]),
            Step("feed_72", 72, "Maintenance feed", "Confirm the well will be confluent tomorrow.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["maintenance medium"],
                 gates=["confluence"]),
            Step("chir", 96, "Differentiation day 0",
                 "RPMI + B-27 minus insulin + CHIR99021 for 24 h. CHIR is unstable to extra freeze-thaws.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["RPMI", "B-27 minus insulin", "CHIR99021"]),
            Step("chir_off", 120, "Differentiation day 1",
                 "RPMI + B-27 minus insulin, no CHIR.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["RPMI", "B-27 minus insulin"]),
            Step("iwp", 168, "Differentiation day 3",
                 "RPMI + B-27 minus insulin + IWP2.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["RPMI", "B-27 minus insulin", "IWP2"]),
            Step("iwp_off", 216, "Differentiation day 5",
                 "RPMI + B-27 minus insulin, no IWP2.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["RPMI", "B-27 minus insulin"]),
            Step("insulin", 264, "Differentiation day 7",
                 "Switch to RPMI + B-27 with insulin.",
                 "medium_change", hood_minutes=12, volume_ml=2, reagents=["RPMI", "B-27 with insulin"]),
            Step("feed_10", 312, "Feed", "Exchange RPMI + B-27 with insulin.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["RPMI", "B-27 with insulin"]),
            Step("beating", 336, "Beating gate",
                 "Look for spontaneous contraction. Absence is a failed or delayed differentiation, not a cue to change the dose mid-stream without a record.",
                 "qc", hood_minutes=15, gates=["beating"]),
            Step("feed_12", 360, "Feed", "Exchange.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["RPMI", "B-27 with insulin"]),
            Step("feed_14prep", 408, "Feed", "Exchange.",
                 "medium_change", hood_minutes=10, volume_ml=2, reagents=["RPMI", "B-27 with insulin"]),
            Step("endpoint", 432, "Purity gate",
                 "Flow or immunostaining for cardiac troponin T is the paper's purity readout. This checklist ends there.",
                 "endpoint", hood_minutes=20, gates=["cTnT"]),
        ],
        non_claims=list(NONCLAIMS) + [
            "Not a recipe for an allogeneic cardiomyocyte product.",
        ],
    )


def hepatocytes() -> Protocol:
    return Protocol(
        id="hepatocyte_differentiation",
        title="Directed differentiation of human PSCs into hepatocyte-like cells",
        citation="Hannan et al., Nature Protocols 2013; endoderm specification D'Amour et al., Nature Biotechnology 2005.",
        doi="10.1038/nprot.2012.153",
        biosafety="BSL-2 human pluripotent cell culture in a certified Class II cabinet.",
        vessel="One well of a 6-well plate, 2 mL medium exchanges.",
        max_hours_between_medium_changes=48,
        summary=(
            "Abridged 4-stage differentiation of hPSCs into functional hepatocyte-like cells: "
            "definitive endoderm induction (Activin A), hepatic specification (BMP4, FGF2), "
            "hepatoblast commitment (HGF), and maturation (Oncostatin M, Dexamethasone). "
            "Albumin secretion and HNF4A expression are key benchmark readouts."
        ),
        parameters=[
            Parameter("ActivinA_ng_per_mL", 100, "ng/mL", 50, 100,
                      "Day 0-3 definitive endoderm induction. Hannan et al. 2013."),
            Parameter("BMP4_ng_per_mL", 10, "ng/mL", 5, 20,
                      "Day 3-8 hepatic specification."),
            Parameter("FGF2_ng_per_mL", 10, "ng/mL", 5, 20,
                      "Day 3-8 hepatic specification."),
            Parameter("HGF_ng_per_mL", 20, "ng/mL", 10, 40,
                      "Day 8-13 hepatoblast commitment."),
            Parameter("OncostatinM_ng_per_mL", 20, "ng/mL", 10, 30,
                      "Day 13-18 maturation."),
            Parameter("Dexamethasone_uM", 0.1, "µM", 0.05, 0.2,
                      "Day 13-18 maturation."),
        ],
        steps=[
            Step("coat", 0, "Coat the well",
                 "Matrigel or vitronectin coating per vendor instructions.",
                 "coat", hood_minutes=15, reagents=["matrix"]),
            Step("seed", 0.5, "Seed pluripotent cells",
                 "Seed at high density (~50,000 cells/cm2) with Y-27632.",
                 "seed", hood_minutes=20, volume_ml=2,
                 reagents=["maintenance medium", "Y-27632"], gates=["morphology"]),
            Step("feed_confluence", 24, "Pre-differentiation feed",
                 "Exchange medium without Y-27632. Culture until 70-80% confluence.",
                 "medium_change", hood_minutes=10, volume_ml=2,
                 reagents=["maintenance medium"], gates=["confluence"]),
            Step("endo_d0", 48, "Definitive endoderm day 0",
                 "RPMI 1640 + B-27 minus insulin + 100 ng/mL Activin A + Wnt3a.",
                 "medium_change", hood_minutes=15, volume_ml=2,
                 reagents=["RPMI", "B-27 minus insulin", "Activin A", "Wnt3a"]),
            Step("endo_d1", 72, "Definitive endoderm day 1",
                 "RPMI 1640 + B-27 minus insulin + 100 ng/mL Activin A.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["RPMI", "B-27 minus insulin", "Activin A"]),
            Step("endo_d2", 96, "Definitive endoderm day 2",
                 "RPMI 1640 + B-27 minus insulin + 100 ng/mL Activin A.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["RPMI", "B-27 minus insulin", "Activin A"]),
            Step("sox17_gate", 118, "Endoderm QC gate",
                 "Flow or qPCR for SOX17 and FOXA2 expression (>80% positive).",
                 "qc", hood_minutes=15, gates=["SOX17", "FOXA2"]),
            Step("spec_d3", 120, "Hepatic specification day 3",
                 "KO-DMEM + 20% KSR + 10 ng/mL BMP4 + 10 ng/mL FGF2.",
                 "medium_change", hood_minutes=15, volume_ml=2,
                 reagents=["KO-DMEM", "KSR", "BMP4", "FGF2"]),
            Step("spec_d5", 168, "Hepatic specification day 5",
                 "Fresh specification medium.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["KO-DMEM", "KSR", "BMP4", "FGF2"]),
            Step("spec_d7", 216, "Hepatic specification day 7",
                 "Fresh specification medium.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["KO-DMEM", "KSR", "BMP4", "FGF2"]),
            Step("blast_d9", 264, "Hepatoblast expansion day 9",
                 "HepatoZYME medium + 20 ng/mL HGF.",
                 "medium_change", hood_minutes=15, volume_ml=2,
                 reagents=["HepatoZYME", "HGF"]),
            Step("blast_d11", 312, "Hepatoblast expansion day 11",
                 "Fresh HepatoZYME medium + 20 ng/mL HGF.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["HepatoZYME", "HGF"]),
            Step("afp_gate", 350, "Hepatoblast QC gate",
                 "Verify emergence of HNF4A and AFP positive cells.",
                 "qc", hood_minutes=15, gates=["HNF4A", "AFP"]),
            Step("mature_d13", 360, "Maturation day 13",
                 "HepatoZYME + 20 ng/mL Oncostatin M + 0.1 µM Dexamethasone.",
                 "medium_change", hood_minutes=15, volume_ml=2,
                 reagents=["HepatoZYME", "Oncostatin M", "Dexamethasone"]),
            Step("mature_d15", 408, "Maturation day 15",
                 "Fresh maturation medium.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["HepatoZYME", "Oncostatin M", "Dexamethasone"]),
            Step("mature_d17", 456, "Maturation day 17",
                 "Fresh maturation medium.",
                 "medium_change", hood_minutes=12, volume_ml=2,
                 reagents=["HepatoZYME", "Oncostatin M", "Dexamethasone"]),
            Step("endpoint", 480, "Hepatocyte endpoint",
                 "Mature hepatocyte-like cells: assay albumin secretion and CYP3A4 activity.",
                 "endpoint", hood_minutes=20, gates=["Albumin", "CYP3A4"]),
        ],
        non_claims=list(NONCLAIMS) + [
            "Not an in vitro model for clinical toxicology clearance without secondary metabolic validation.",
        ],
    )


LIBRARY = {
    "e8_feeder_free_maintenance": maintenance,
    "dual_smad_neural": dual_smad,
    "giwi_cardiac": giwi,
    "hepatocyte_differentiation": hepatocytes,
}

