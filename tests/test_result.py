import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from protocolcompiler.cli import main as cli_main
from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import giwi
from protocolcompiler.result import ResultRecordError, validate_result_record


class ResultRecordTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.protocol = compile_protocol(giwi())
        self.protocol_path = self.root / "compiled.json"
        self.protocol_path.write_text(json.dumps(self.protocol), encoding="utf-8")

    def write_result(self, *, result=None, artifact_bytes=b"synthetic evidence fixture\n", name="run"):
        directory = self.root / name
        directory.mkdir()
        evidence = directory / "evidence.txt"
        evidence.write_bytes(artifact_bytes)
        gates = []
        for step in self.protocol["schedule"]:
            for gate in step["gates"]:
                record = {"step_id": step["id"], "gate": gate}
                if not gates:
                    record.update({"status": "measured_pass", "observed_value": "present",
                                   "unit": "categorical", "method": "synthetic review fixture",
                                   "evidence_artifact_id": "evidence-1"})
                else:
                    record.update({"status": "not_measured", "reason": "synthetic test fixture"})
                gates.append(record)
        if not gates:
            self.fail("GiWi checklist fixture must contain at least one compiled gate")
        expected = {
            "schema_version": 1,
            "protocol_id": self.protocol["id"],
            "protocol_sha256": self.protocol["protocol_sha256"],
            "compiled_protocol_sha256": self.protocol["compiled_sha256"],
            "run_id": "synthetic-run-001",
            "disposition": "partial",
            "evidence_artifacts": [{"id": "evidence-1", "kind": "text_record", "path": "evidence.txt",
                                    "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                                    "size_bytes": len(artifact_bytes)}],
            "gate_results": gates,
            "deviations": [],
        }
        if result is not None:
            expected = result
        result_path = directory / "result.json"
        result_path.write_text(json.dumps(expected), encoding="utf-8")
        return result_path, expected

    def test_valid_result_links_every_gate_and_hashes_evidence(self):
        result_path, _ = self.write_result()
        report = validate_result_record(self.protocol_path, result_path)
        self.assertEqual(report["validation_status"], "record_integrity_valid")
        self.assertEqual(report["n_compiled_gates"], report["n_measured_gates"] + report["n_not_measured_gates"])
        self.assertGreater(report["n_measured_gates"], 0)
        self.assertEqual(report["n_evidence_artifacts"], 1)

        output = self.root / "validation.json"
        self.assertEqual(cli_main(["validate-result", "--compiled-protocol", str(self.protocol_path),
                                   "--result", str(result_path), "--out", str(output)]), 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)

    def test_missing_gate_tampered_protocol_and_artifact_paths_fail_closed(self):
        result_path, result = self.write_result(name="missing-gate")
        result["gate_results"].pop()
        result_path.write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaisesRegex(ResultRecordError, "every compiled gate"):
            validate_result_record(self.protocol_path, result_path)

        tampered_protocol = copy.deepcopy(self.protocol)
        tampered_protocol["schedule"][0]["title"] += " changed"
        tampered_protocol_path = self.root / "tampered-protocol.json"
        tampered_protocol_path.write_text(json.dumps(tampered_protocol), encoding="utf-8")
        valid_path, _ = self.write_result(name="valid-again")
        with self.assertRaisesRegex(ResultRecordError, "does not match compiled_sha256"):
            validate_result_record(tampered_protocol_path, valid_path)

        result_path, result = self.write_result(name="escaping-artifact")
        result["evidence_artifacts"][0]["path"] = "../outside.txt"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaisesRegex(ResultRecordError, "stay inside result directory"):
            validate_result_record(self.protocol_path, result_path)

    def test_artifact_byte_change_is_detected(self):
        result_path, _ = self.write_result()
        (result_path.parent / "evidence.txt").write_bytes(b"changed evidence\n")
        with self.assertRaisesRegex(ResultRecordError, "size is invalid|hash or byte count mismatch"):
            validate_result_record(self.protocol_path, result_path)


if __name__ == "__main__":
    unittest.main()
