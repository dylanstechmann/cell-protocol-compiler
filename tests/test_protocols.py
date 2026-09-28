import io
import json
import unittest
from unittest.mock import patch

from protocolcompiler.cli import main as cli_main
from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import LIBRARY, giwi, hepatocytes
from protocolcompiler.schema import ProtocolError, Step
from protocolcompiler.validate import validate


class LibraryTests(unittest.TestCase):
    def test_all_library_protocols_compile(self):
        self.assertGreaterEqual(len(LIBRARY), 4)
        for name, factory in LIBRARY.items():
            compiled = compile_protocol(factory())
            self.assertEqual(compiled["id"], name)
            self.assertTrue(compiled["doi"].startswith("10."))
            self.assertIn("not for administration to humans", compiled["checklist_markdown"].lower())
            self.assertIn("Class II", " ".join(compiled["critical_control_points"]))
            self.assertGreaterEqual(len(compiled["schedule"]), 5)

    def test_hepatocyte_protocol_details(self):
        proto = hepatocytes()
        self.assertEqual(proto.id, "hepatocyte_differentiation")
        compiled = compile_protocol(proto)
        self.assertEqual(compiled["id"], "hepatocyte_differentiation")
        self.assertIn("Albumin", [gate for step in compiled["schedule"] for gate in step["gates"]])
        self.assertIn("SOX17", [gate for step in compiled["schedule"] for gate in step["gates"]])

    def test_hepatocyte_parameter_out_of_range(self):
        proto = hepatocytes()
        proto.parameter("ActivinA_ng_per_mL").value = 500
        with self.assertRaises(ProtocolError) as caught:
            validate(proto)
        self.assertTrue(any("ActivinA_ng_per_mL" in err for err in caught.exception.errors))

    def test_chir_out_of_range_is_rejected(self):
        protocol = giwi()
        protocol.parameter("CHIR99021_uM").value = 40
        with self.assertRaises(ProtocolError) as caught:
            validate(protocol)
        self.assertTrue(any("CHIR99021" in err for err in caught.exception.errors))

    def test_missing_qc_is_rejected(self):
        protocol = giwi()
        for step in protocol.steps:
            step.gates = []
            if step.action == "qc":
                step.action = "note"
                step.hood_minutes = 0
        with self.assertRaises(ProtocolError) as caught:
            validate(protocol)
        self.assertTrue(any("QC" in err for err in caught.exception.errors))

    def test_feed_gap_is_rejected(self):
        protocol = giwi()
        protocol.steps = [step for step in protocol.steps if step.id not in {"chir_off", "iwp", "iwp_off"}]
        with self.assertRaises(ProtocolError) as caught:
            validate(protocol)
        self.assertTrue(any("medium gap" in err for err in caught.exception.errors))

    def test_hood_overlap_is_rejected(self):
        protocol = giwi()
        protocol.steps.append(Step(
            "clash", 96, "Second person in the same cabinet slot",
            "This should not schedule.", "qc", hood_minutes=30, gates=["morphology"],
        ))
        with self.assertRaises(ProtocolError) as caught:
            validate(protocol)
        self.assertTrue(any("hood overlap" in err for err in caught.exception.errors))

    def test_cli_json_and_markdown(self):
        stdout_json = io.StringIO()
        with patch("sys.stdout", stdout_json):
            rc = cli_main(["hepatocyte_differentiation", "--json"])
            self.assertEqual(rc, 0)
        parsed = json.loads(stdout_json.getvalue())
        self.assertEqual(parsed["id"], "hepatocyte_differentiation")

        stdout_md = io.StringIO()
        with patch("sys.stdout", stdout_md):
            rc = cli_main(["hepatocyte_differentiation", "--markdown"])
            self.assertEqual(rc, 0)
        self.assertIn("# Directed differentiation of human PSCs into hepatocyte-like cells", stdout_md.getvalue())


if __name__ == "__main__":
    unittest.main()

