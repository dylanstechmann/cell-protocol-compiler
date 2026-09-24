import unittest

from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import giwi
from protocolcompiler.schema import ProtocolError
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
