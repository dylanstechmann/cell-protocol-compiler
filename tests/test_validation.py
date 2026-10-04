import unittest

from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import dual_smad, giwi, hepatocytes
from protocolcompiler.schema import ProtocolError, Step
from protocolcompiler.validate import validate


class ValidationTests(unittest.TestCase):
    def test_nonfinite_schedule_and_limits_rejected(self):
        for attr in ["start_hour", "hood_minutes", "volume_ml"]:
            protocol = giwi()
            setattr(protocol.steps[0], attr, float("nan"))
            with self.assertRaises(ProtocolError):
                validate(protocol)
        protocol = giwi()
        protocol.max_hours_between_medium_changes = float("inf")
        with self.assertRaises(ProtocolError):
            validate(protocol)

    def test_final_feed_to_endpoint_gap_is_checked(self):
        protocol = giwi()
        protocol.steps[-1].start_hour += 100
        with self.assertRaisesRegex(ProtocolError, "medium gap"):
            validate(protocol)

    def test_compiled_digest_is_stable_and_tracks_changes(self):
        protocol = giwi()
        digest = compile_protocol(protocol)["protocol_sha256"]
        self.assertEqual(digest, compile_protocol(giwi())["protocol_sha256"])
        protocol.steps[0].title = "Reviewed coat step"
        self.assertNotEqual(digest, compile_protocol(protocol)["protocol_sha256"])

    def test_multiple_endpoints_are_rejected(self):
        protocol = giwi()
        protocol.steps.append(Step("early_endpoint", 300, "Earlier endpoint", "Review.",
                                   "endpoint", hood_minutes=0))
        with self.assertRaisesRegex(ProtocolError, "exactly one endpoint"):
            validate(protocol)

    def test_active_step_after_endpoint_is_rejected(self):
        protocol = giwi()
        protocol.steps.append(Step("late_qc", 456, "Late QC", "Review.", "qc",
                                   hood_minutes=0, gates=["review"]))
        with self.assertRaisesRegex(ProtocolError, "after endpoint"):
            validate(protocol)

    def test_note_with_gate_is_not_a_qc_action(self):
        protocol = giwi()
        for step in protocol.steps:
            step.gates = []
            if step.action == "qc":
                step.action = "note"
                step.hood_minutes = 0
                step.gates = ["mentioned but not performed"]
        with self.assertRaisesRegex(ProtocolError, "no QC gate"):
            validate(protocol)

    def test_qc_action_without_an_explicit_gate_is_rejected(self):
        protocol = giwi()
        for step in protocol.steps:
            step.gates = []
        with self.assertRaisesRegex(ProtocolError, "no QC gate"):
            validate(protocol)

    def test_blank_or_nontext_entries_cannot_satisfy_the_qc_gate_requirement(self):
        for gate in ["", "   ", "\t\n", "\u2003", None, 0, True, []]:
            with self.subTest(gate=gate):
                protocol = giwi()
                for step in protocol.steps:
                    step.gates = []
                protocol.steps[0].gates = [gate]
                with self.assertRaisesRegex(ProtocolError, "no QC gate"):
                    validate(protocol)

    def test_malformed_gate_fields_are_rejected_before_compilation(self):
        for gates in [None, 1, "review", {"review": True}, ["review", " "], ["review", 1]]:
            with self.subTest(gates=gates):
                protocol = giwi()
                protocol.steps[0].gates = gates
                with self.assertRaisesRegex(ProtocolError, "gates must be a list of nonblank strings"):
                    compile_protocol(protocol)

    def test_nonblank_gate_on_an_executable_step_is_preserved(self):
        protocol = giwi()
        protocol.steps[0].gates = ["  documented review  "]
        compiled = compile_protocol(protocol)
        step = next(row for row in compiled["schedule"] if row["id"] == protocol.steps[0].id)
        self.assertEqual(step["gates"], ["  documented review  "])

class SourceContractTests(unittest.TestCase):
    def test_mutable_requirement_lists_cannot_bypass_published_workflow(self):
        protocol = giwi()
        protocol.required_parameters = ()
        protocol.parameters = []
        with self.assertRaisesRegex(ProtocolError, "missing required parameter"):
            validate(protocol)
        protocol = giwi()
        for step in protocol.steps:
            step.required_gates = ()
            step.gates = ["arbitrary review"]
        with self.assertRaisesRegex(ProtocolError, "missing required gate"):
            validate(protocol)
        protocol = dual_smad()
        protocol.required_step_reagents = {}
        for step in protocol.steps:
            step.reagents = []
        with self.assertRaisesRegex(ProtocolError, "missing required reagent"):
            validate(protocol)

    def test_window_units_and_feed_limit_cannot_be_widened(self):
        for field, value, expected in (("high", 1000, "source-reviewed parameter window"),
                                       ("unit", "mM", "unit must remain")):
            protocol = giwi()
            setattr(protocol.parameter("CHIR99021_uM"), field, value)
            with self.subTest(field=field), self.assertRaisesRegex(ProtocolError, expected):
                validate(protocol)
        protocol = giwi()
        protocol.max_hours_between_medium_changes = 1000
        with self.assertRaisesRegex(ProtocolError, "source-reviewed limit"):
            validate(protocol)

    def test_inactive_alternative_cannot_bypass_nonfinite_bounds(self):
        for field, value in (("low", float("nan")), ("high", float("inf")), ("low", 1000)):
            protocol = dual_smad()
            setattr(protocol.parameter("LDN193189_nM"), field, value)
            with self.subTest(field=field), self.assertRaises(ProtocolError):
                validate(protocol)

    def test_clearing_reagent_rules_cannot_hide_an_inconsistent_narrative(self):
        protocol = dual_smad()
        protocol.parameter("Noggin_ng_per_mL").value = 0
        protocol.parameter("LDN193189_nM").value = 100
        for step in protocol.steps:
            step.reagents = ["LDN-193189" if name == "Noggin" else name
                             for name in step.reagents]
        protocol.required_step_reagents = {}
        with self.assertRaisesRegex(ProtocolError, "still lists or describes Noggin"):
            validate(protocol)

    def test_named_qc_action_cannot_be_demoted_to_a_note(self):
        protocol = giwi()
        step = next(step for step in protocol.steps if step.id == "beating")
        step.action = "note"
        with self.assertRaisesRegex(ProtocolError, "source-reviewed QC action"):
            validate(protocol)

    def test_source_quarantine_cannot_be_cleared_on_a_candidate(self):
        protocol = hepatocytes()
        protocol.compilable = True
        with self.assertRaisesRegex(ProtocolError, "not eligible for compilation"):
            validate(protocol)
