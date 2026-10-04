import io
import json
import unittest
from unittest.mock import patch

from protocolcompiler.cli import main as cli_main
from protocolcompiler.compile import compile_protocol
from protocolcompiler.constraints import (
    CONSTRAINTS_SCHEMA_VERSION,
    EXCLUSIVITY_RULES,
    export_constraints,
    protocol_hash,
)
from protocolcompiler.library import LIBRARY, dual_smad, giwi, hepatocytes
from protocolcompiler.schema import ProtocolError


class ConstraintExportTests(unittest.TestCase):
    def test_windows_match_the_compiled_checklist(self):
        for name, factory in LIBRARY.items():
            protocol = factory()
            if not protocol.compilable:
                continue
            export = export_constraints(protocol)
            compiled = compile_protocol(protocol)
            self.assertEqual(export["schema_version"], CONSTRAINTS_SCHEMA_VERSION)
            self.assertEqual(export["protocol_id"], name)
            self.assertEqual(export["protocol_sha256"], compiled["protocol_sha256"])
            by_name = {row["name"]: row for row in export["parameters"]}
            self.assertEqual(
                set(by_name), {row["name"] for row in compiled["parameters"]}
            )
            for row in compiled["parameters"]:
                with self.subTest(protocol=name, parameter=row["name"]):
                    exported = by_name[row["name"]]
                    self.assertEqual(exported["low"], row["low"])
                    self.assertEqual(exported["high"], row["high"])
                    self.assertEqual(exported["unit"], row["unit"])
                    self.assertEqual(exported["value"], row["value"])
                    self.assertTrue(exported["required"])

    def test_required_gates_are_exported_per_step(self):
        export = export_constraints(giwi())
        self.assertIn("beating", export["required_gates"]["beating"])
        self.assertIn("cTnT", export["required_gates"]["endpoint"])
        self.assertIn("OCT4", export_constraints(dual_smad())["required_gates"]["pax6_gate"])

    def test_dual_smad_exclusivity_is_exported(self):
        export = export_constraints(dual_smad())
        self.assertEqual(len(export["exclusivity"]), 1)
        rule = export["exclusivity"][0]
        self.assertEqual(set(rule["parameters"]), {"Noggin_ng_per_mL", "LDN193189_nM"})
        self.assertEqual(rule["rule"], "at_most_one_positive")
        self.assertIn("substitut", rule["rationale"].lower())

    def test_exclusivity_rules_must_reference_real_parameters(self):
        broken = {"giwi_cardiac": [{
            "parameters": ["CHIR99021_uM", "not_a_parameter"],
            "rule": "at_most_one_positive",
            "rationale": "self-check fixture",
        }]}
        with patch.dict(EXCLUSIVITY_RULES, broken, clear=False):
            with self.assertRaises(ProtocolError) as caught:
                export_constraints(giwi())
        self.assertTrue(any("unknown parameters" in err for err in caught.exception.errors))

    def test_quarantined_source_records_export_nothing(self):
        with self.assertRaises(ProtocolError) as caught:
            export_constraints(hepatocytes())
        self.assertTrue(
            any("not eligible for compilation" in err for err in caught.exception.errors)
        )

    def test_export_keeps_source_requirements_when_candidate_metadata_is_cleared(self):
        protocol = giwi()
        expected = export_constraints(protocol)
        protocol.required_parameters = ()
        protocol.required_step_reagents = {}
        for step in protocol.steps:
            step.required_gates = ()
        actual = export_constraints(protocol)
        self.assertTrue(all(item["required"] for item in actual["parameters"]))
        self.assertEqual(actual["required_gates"], expected["required_gates"])
        self.assertEqual(actual["required_step_reagents"], expected["required_step_reagents"])

    def test_export_resolves_the_active_ldn_reagent_alternative(self):
        protocol = dual_smad()
        protocol.parameter("Noggin_ng_per_mL").value = 0
        protocol.parameter("LDN193189_nM").value = 100
        for step in protocol.steps:
            step.reagents = ["LDN-193189" if name == "Noggin" else name
                             for name in step.reagents]
        next(step for step in protocol.steps if step.id == "induct_0").detail = (
            "Switch to KSR-based SRM with SB431542 and LDN-193189.")
        export = export_constraints(protocol)
        self.assertEqual(export["required_step_reagents"]["induct_0"],
                         ["LDN-193189", "SB431542"])

    def test_export_is_deterministic(self):
        self.assertEqual(export_constraints(giwi()), export_constraints(giwi()))
        self.assertEqual(protocol_hash(dual_smad()), protocol_hash(dual_smad()))

    def test_non_claims_travel_with_the_export(self):
        export = export_constraints(giwi())
        self.assertTrue(any("humans" in claim.lower() for claim in export["non_claims"]))

    def test_cli_constraints_mode(self):
        buffer = io.StringIO()
        with patch("sys.stdout", buffer):
            self.assertEqual(cli_main(["giwi_cardiac", "--constraints"]), 0)
        parsed = json.loads(buffer.getvalue())
        self.assertEqual(parsed["protocol_id"], "giwi_cardiac")
        self.assertTrue(parsed["parameters"])

        with self.assertRaises(SystemExit) as caught:
            cli_main(["hepatocyte_differentiation", "--constraints"])
        self.assertEqual(caught.exception.code, 2)

        with self.assertRaises(SystemExit) as caught:
            cli_main(["giwi_cardiac", "--constraints", "--markdown"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
