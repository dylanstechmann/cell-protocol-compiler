import io
import json
import unittest
from unittest.mock import patch

from protocolcompiler.cli import main as cli_main
from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import LIBRARY, dual_smad, giwi, hepatocytes
from protocolcompiler.schema import ProtocolError, Step
from protocolcompiler.validate import validate


class LibraryTests(unittest.TestCase):
    def test_all_library_protocols_compile(self):
        self.assertGreaterEqual(len(LIBRARY), 4)
        for name, factory in LIBRARY.items():
            if not factory().compilable:
                with self.assertRaises(ProtocolError):
                    compile_protocol(factory())
                continue
            compiled = compile_protocol(factory())
            self.assertEqual(compiled["id"], name)
            self.assertTrue(compiled["doi"].startswith("10."))
            self.assertIn("not for administration to humans", compiled["checklist_markdown"].lower())
            self.assertIn("Class II", " ".join(compiled["critical_control_points"]))
            self.assertGreaterEqual(len(compiled["schedule"]), 5)

    def test_hepatocyte_source_mismatch_blocks_recipe_compilation(self):
        proto = hepatocytes()
        self.assertEqual(proto.id, "hepatocyte_differentiation")
        with self.assertRaises(ProtocolError) as caught:
            compile_protocol(proto)
        self.assertTrue(any("not eligible for compilation" in err for err in caught.exception.errors))
        self.assertEqual(proto.parameters, [])
        self.assertEqual(proto.steps, [])
        self.assertIn("not an experimental recipe", " ".join(proto.non_claims))

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

    def test_removing_parameters_or_replacing_required_gates_is_rejected(self):
        protocol = giwi()
        protocol.parameters = []
        with self.assertRaises(ProtocolError) as caught:
            validate(protocol)
        self.assertTrue(any("missing required parameter" in err for err in caught.exception.errors))

        protocol = giwi()
        for step in protocol.steps:
            step.gates = []
        protocol.steps[0].gates = ["arbitrary"]
        with self.assertRaises(ProtocolError) as caught:
            validate(protocol)
        self.assertTrue(any("missing required gate" in err for err in caught.exception.errors))

    def test_ldn_and_noggin_values_and_reagent_record_must_agree(self):
        protocol = dual_smad()
        protocol.parameter("LDN193189_nM").value = 100
        with self.assertRaises(ProtocolError) as caught:
            validate(protocol)
        self.assertTrue(any("mutually exclusive" in err for err in caught.exception.errors))
        self.assertTrue(any("still list Noggin" in err for err in caught.exception.errors))

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
            rc = cli_main(["giwi_cardiac", "--json"])
            self.assertEqual(rc, 0)
        parsed = json.loads(stdout_json.getvalue())
        self.assertEqual(parsed["id"], "giwi_cardiac")

        stdout_md = io.StringIO()
        with patch("sys.stdout", stdout_md):
            rc = cli_main(["giwi_cardiac", "--markdown"])
            self.assertEqual(rc, 0)
        self.assertIn("# Wnt-modulated cardiomyocyte differentiation (GiWi)", stdout_md.getvalue())

        with self.assertRaises(SystemExit) as caught:
            cli_main(["hepatocyte_differentiation", "--json"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

