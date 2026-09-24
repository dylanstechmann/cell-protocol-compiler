import unittest

from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import LIBRARY, giwi
from protocolcompiler.schema import ProtocolError, Step
from protocolcompiler.validate import validate


class LibraryTests(unittest.TestCase):
    def test_all_three_compile(self):
        for name, factory in LIBRARY.items():
            compiled = compile_protocol(factory())
            self.assertEqual(compiled["id"], name)
            self.assertTrue(compiled["doi"].startswith("10."))
            self.assertIn("not for administration to humans", compiled["checklist_markdown"].lower())
            self.assertIn("Class II", " ".join(compiled["critical_control_points"]))
            self.assertGreaterEqual(len(compiled["schedule"]), 5)

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


if __name__ == "__main__":
    unittest.main()
