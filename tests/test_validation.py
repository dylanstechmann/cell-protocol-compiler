import unittest

from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import giwi
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
