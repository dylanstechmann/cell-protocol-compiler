import contextlib
import io
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from protocolcompiler import source_review as sr
from protocolcompiler.cli import main as cli_main
from protocolcompiler.library import LIBRARY
from protocolcompiler.schema import Parameter

# The encoded defaults and windows as of the 2026-10-07 source review. Widening a concentration
# window is a biological decision (AGENTS.md). If one of these changes on purpose, revisit the
# ledger entry for the same parameter in the same commit.
ENCODED = {
    ("e8_feeder_free_maintenance", "Y27632_uM"): (10, 5, 10),
    ("e8_feeder_free_maintenance", "passage_confluence_percent"): (80, 70, 85),
    ("dual_smad_neural", "SB431542_uM"): (10, 5, 10),
    ("dual_smad_neural", "Noggin_ng_per_mL"): (200, 100, 300),
    ("dual_smad_neural", "LDN193189_nM"): (0, 0, 250),
    ("giwi_cardiac", "CHIR99021_uM"): (6, 2, 12),
    ("giwi_cardiac", "IWP2_uM"): (5, 2, 5),
}


def library_with(protocol_id, mutate):
    """A library mapping whose one entry has been altered after construction."""
    original = LIBRARY[protocol_id]  # bound now, so patching LIBRARY later cannot recurse

    def factory():
        protocol = original()
        mutate(protocol)
        return protocol
    return {**LIBRARY, protocol_id: factory}


def run_cli(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli_main(list(argv))
    return code, out.getvalue()


class LedgerTests(unittest.TestCase):
    def test_the_ledger_is_internally_consistent(self):
        self.assertEqual(sr.ledger_problems(), [])

    def test_the_encoded_defaults_and_windows_have_not_moved(self):
        live = {}
        for protocol_id, factory in LIBRARY.items():
            protocol = factory()
            for parameter in protocol.parameters:
                live[(protocol_id, parameter.name)] = (parameter.value, parameter.low, parameter.high)
        self.assertEqual(live, ENCODED)

    def test_every_encoded_parameter_has_a_source_check(self):
        report = sr.audit()
        self.assertEqual(report["unreviewed_parameters"], [])
        self.assertEqual(report["counts"]["reviewed"], len(ENCODED))
        self.assertEqual({(row["protocol_id"], row["parameter"]) for row in report["reviews"]}, set(ENCODED))

    def test_recorded_disagreements_are_reported_and_leave_the_encoding_alone(self):
        report = sr.audit()
        self.assertEqual(report["status"], sr.STATUS_DISAGREEMENTS)
        counts = report["counts"]
        self.assertEqual((counts[sr.MATCHES], counts[sr.INSIDE_SOURCE_RANGE], counts[sr.DIFFERS],
                          counts[sr.NOT_STATED]), (2, 1, 2, 2))
        self.assertEqual(counts["stale_ledger_entries"], 0)
        rows = {(row["protocol_id"], row["parameter"]): row for row in report["reviews"]}
        sb = rows[("dual_smad_neural", "SB431542_uM")]
        self.assertAlmostEqual(sb["source_value_in_encoded_unit"], 0.01)
        self.assertFalse(sb["source_value_within_encoded_window"])
        noggin = rows[("dual_smad_neural", "Noggin_ng_per_mL")]
        self.assertEqual(noggin["source_value_in_encoded_unit"], 500)
        self.assertFalse(noggin["source_value_within_encoded_window"])
        chir = rows[("giwi_cardiac", "CHIR99021_uM")]
        self.assertTrue(chir["source_value_within_encoded_window"])
        self.assertFalse(chir["source_range_within_encoded_window"])
        self.assertTrue(chir["encoded_window_extends_beyond_source_range"])
        self.assertEqual(counts["window_conflicts_with_source"], 3)

    def test_not_stated_is_a_search_result_not_a_disagreement(self):
        rows = [row for row in sr.audit()["reviews"] if row["verdict"] == sr.NOT_STATED]
        self.assertEqual({row["parameter"] for row in rows}, {"passage_confluence_percent", "LDN193189_nM"})
        for row in rows:
            self.assertTrue(row["search_terms"])
            self.assertIsNone(row["source_value_in_encoded_unit"])

    def test_source_number_is_converted_by_arithmetic_not_typed(self):
        review = next(item for item in sr.all_reviews() if item.parameter == "SB431542_uM")
        self.assertEqual((review.source_number, review.source_unit, review.encoded_unit), (10.0, "nM", "µM"))
        self.assertAlmostEqual(review.source_value, 0.01)
        with self.assertRaises(ValueError):
            replace(review, source_unit="ng/mL").source_value

    def test_every_disagreement_is_visible_in_the_compiled_parameter_note(self):
        # A reader of the checklist should not need to run source-audit to learn a number is disputed.
        for review in sr.all_reviews():
            if review.verdict == sr.DIFFERS or review.parameter == "CHIR99021_uM":
                protocol = LIBRARY[review.protocol_id]()
                note = next(p.note for p in protocol.parameters if p.name == review.parameter)
                self.assertTrue("source-audit" in note or "paper" in note, (review.parameter, note))

    def test_audit_output_is_strict_json(self):
        text = json.dumps(sr.audit(), allow_nan=False)
        self.assertIn("500 ng/mL", text)


class AuditCatchesDriftTests(unittest.TestCase):
    def test_widening_a_window_without_revisiting_its_source_makes_the_ledger_stale(self):
        def widen(protocol):
            protocol.parameter("Noggin_ng_per_mL").high = 600.0

        report = sr.audit(library_with("dual_smad_neural", widen))
        self.assertEqual(report["status"], sr.STATUS_STALE)
        stale = [row for row in report["reviews"] if row["ledger_status"] == sr.STATUS_STALE]
        self.assertEqual([row["parameter"] for row in stale], ["Noggin_ng_per_mL"])
        self.assertEqual(stale[0]["live_encoded_window"], [100.0, 600.0])
        self.assertEqual(report["counts"]["stale_ledger_entries"], 1)

    def test_changing_a_default_is_also_stale(self):
        def change(protocol):
            protocol.parameter("CHIR99021_uM").value = 12.0

        self.assertEqual(sr.audit(library_with("giwi_cardiac", change))["status"], sr.STATUS_STALE)

    def test_a_removed_protocol_or_parameter_is_stale_not_ignored(self):
        without_giwi = {key: value for key, value in LIBRARY.items() if key != "giwi_cardiac"}
        report = sr.audit(without_giwi)
        statuses = {row["parameter"]: row["ledger_status"] for row in report["reviews"]
                    if row["protocol_id"] == "giwi_cardiac"}
        self.assertEqual(statuses, {"CHIR99021_uM": "protocol_absent", "IWP2_uM": "protocol_absent"})
        self.assertEqual(report["status"], sr.STATUS_STALE)

        def drop(protocol):
            protocol.parameters = [p for p in protocol.parameters if p.name != "IWP2_uM"]

        report = sr.audit(library_with("giwi_cardiac", drop))
        self.assertIn("parameter_absent", {row["ledger_status"] for row in report["reviews"]})

    def test_a_new_unreviewed_parameter_is_listed(self):
        def add(protocol):
            protocol.parameters.append(Parameter("new_factor_uM", 1.0, "µM", 0.5, 2.0, "added later"))

        report = sr.audit(library_with("dual_smad_neural", add))
        self.assertEqual(report["unreviewed_parameters"], ["dual_smad_neural.new_factor_uM"])

    def test_a_changed_unit_is_stale(self):
        def change(protocol):
            protocol.parameter("SB431542_uM").unit = "nM"

        self.assertEqual(sr.audit(library_with("dual_smad_neural", change))["status"], sr.STATUS_STALE)

    def test_a_quarantined_protocol_is_not_audited_as_if_it_had_parameters(self):
        report = sr.audit()
        self.assertNotIn("hepatocyte_differentiation", {row["protocol_id"] for row in report["reviews"]})
        self.assertFalse(any(name.startswith("hepatocyte_differentiation.")
                             for name in report["unreviewed_parameters"]))


class VerdictsFollowFromNumbersTests(unittest.TestCase):
    def audit_with(self, **changes):
        base = next(item for item in sr.all_reviews() if item.parameter == "IWP2_uM")
        altered = replace(base, **changes)
        record = replace(sr.GIWI, reviews=(altered,))
        with patch.object(sr, "SOURCE_RECORDS", (record,)):
            return sr.ledger_problems()

    def test_a_matches_verdict_with_different_numbers_is_caught(self):
        self.assertTrue(any("'matches'" in item for item in self.audit_with(source_number=3.0)))

    def test_a_differs_verdict_when_the_numbers_agree_is_caught(self):
        self.assertTrue(any("'differs'" in item for item in self.audit_with(verdict=sr.DIFFERS)))

    def test_a_token_missing_from_the_quote_is_caught(self):
        self.assertTrue(any("does not contain" in item for item in self.audit_with(source_tokens=("7 µM",))))

    def test_a_not_stated_verdict_needs_its_search_terms(self):
        problems = self.audit_with(verdict=sr.NOT_STATED, source_number=None, source_unit=None)
        self.assertTrue(any("search terms" in item for item in problems))

    def test_an_unknown_verdict_is_caught(self):
        self.assertTrue(any("unknown verdict" in item for item in self.audit_with(verdict="probably_fine")))

    def test_a_row_without_a_quote_is_caught(self):
        self.assertTrue(any("no source quote" in item for item in self.audit_with(source_quote=())))

    def test_an_inconsistent_ledger_fails_the_audit_status(self):
        base = next(item for item in sr.all_reviews() if item.parameter == "IWP2_uM")
        record = replace(sr.GIWI, reviews=(replace(base, source_number=3.0),))
        with patch.object(sr, "SOURCE_RECORDS", (record,)):
            self.assertEqual(sr.audit()["status"], sr.STATUS_INCONSISTENT)


class CommandTests(unittest.TestCase):
    def test_source_audit_prints_json_and_exits_zero_on_recorded_disagreements(self):
        code, text = run_cli("source-audit")
        self.assertEqual(code, 0)
        report = json.loads(text)
        self.assertEqual(report["status"], sr.STATUS_DISAGREEMENTS)
        self.assertEqual(len(report["reviews"]), len(ENCODED))
        self.assertTrue(report["limitations"])

    def test_source_audit_exits_one_when_the_ledger_is_stale(self):
        def widen(protocol):
            protocol.parameter("CHIR99021_uM").high = 14.0

        factory = library_with("giwi_cardiac", widen)["giwi_cardiac"]
        with patch.dict(LIBRARY, {"giwi_cardiac": factory}):
            code, text = run_cli("source-audit")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(text)["status"], sr.STATUS_STALE)

    def test_the_compile_commands_are_unaffected(self):
        for name in ("e8_feeder_free_maintenance", "dual_smad_neural", "giwi_cardiac"):
            code, text = run_cli(name, "--json")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(text)["id"], name)


if __name__ == "__main__":
    unittest.main()
