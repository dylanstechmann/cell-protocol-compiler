"""Validate source-linked records returned after a compiled checklist is used."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath

MAX_EVIDENCE_BYTES = 200_000_000


class ResultRecordError(ValueError):
    """The supplied result record does not match its protocol or evidence."""


def _read_json(path: Path) -> dict:
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ResultRecordError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ResultRecordError(f"non-finite JSON number is not allowed: {value}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResultRecordError(f"cannot read JSON record {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResultRecordError(f"JSON record must be an object: {path}")
    return value


def _nonblank(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ResultRecordError(f"{field} must be nonempty text")


def _finite_value(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ResultRecordError(f"{field} must be a finite number or nonempty text")
    if isinstance(value, str):
        _nonblank(value, field)
    elif not math.isfinite(value):
        raise ResultRecordError(f"{field} must be finite")


def validate_result_record(protocol_path: str | Path, result_path: str | Path) -> dict:
    """Check one observation record against compiled gates and hashed artifacts.

    Passing this check means the record is structurally linked and intact. It
    does not determine whether a protocol was executed correctly or whether an
    assay result is biologically meaningful.
    """
    protocol_path = Path(protocol_path).resolve(strict=True)
    result_path = Path(result_path).resolve(strict=True)
    protocol = _read_json(protocol_path)
    result = _read_json(result_path)
    if protocol.get("schema_version") != 1 or result.get("schema_version") != 1:
        raise ResultRecordError("compiled protocol and result record must use schema version 1")
    for field in ("id", "protocol_sha256", "compiled_sha256", "schedule"):
        if field not in protocol:
            raise ResultRecordError(f"compiled protocol is missing {field}")
    compiled_digest = protocol["compiled_sha256"]
    if (not isinstance(compiled_digest, str) or len(compiled_digest) != 64
            or any(character not in "0123456789abcdef" for character in compiled_digest)):
        raise ResultRecordError("compiled protocol compiled_sha256 must be a lowercase SHA-256 digest")
    compiled_payload = {key: value for key, value in protocol.items()
                        if key not in {"compiled_sha256", "checklist_markdown"}}
    try:
        actual_compiled_digest = hashlib.sha256(json.dumps(
            compiled_payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as exc:
        raise ResultRecordError(f"compiled protocol cannot be canonically hashed: {exc}") from exc
    if actual_compiled_digest != compiled_digest:
        raise ResultRecordError("compiled protocol content does not match compiled_sha256")
    if result.get("protocol_id") != protocol["id"]:
        raise ResultRecordError("result protocol_id does not match compiled protocol")
    if result.get("protocol_sha256") != protocol["protocol_sha256"]:
        raise ResultRecordError("result protocol_sha256 does not match compiled protocol")
    if result.get("compiled_protocol_sha256") != compiled_digest:
        raise ResultRecordError("result compiled_protocol_sha256 does not match compiled checklist")
    _nonblank(result.get("run_id"), "run_id")
    if result.get("disposition") not in ("completed", "partial", "aborted"):
        raise ResultRecordError("disposition must be completed, partial or aborted")

    if not isinstance(protocol["schedule"], list):
        raise ResultRecordError("compiled protocol schedule must be a list")
    steps = set()
    expected_gates = set()
    for index, step in enumerate(protocol["schedule"]):
        if not isinstance(step, dict):
            raise ResultRecordError(f"compiled protocol schedule[{index}] must be an object")
        step_id, gates = step.get("id"), step.get("gates", [])
        _nonblank(step_id, f"compiled protocol schedule[{index}].id")
        if step_id in steps:
            raise ResultRecordError("compiled protocol schedule must contain unique step IDs")
        if not isinstance(gates, list) or any(not isinstance(gate, str) or not gate.strip() for gate in gates):
            raise ResultRecordError(f"compiled protocol schedule[{index}].gates must be nonblank text labels")
        steps.add(step_id)
        expected_gates.update((step_id, gate) for gate in gates)

    artifacts = result.get("evidence_artifacts")
    if not isinstance(artifacts, list):
        raise ResultRecordError("evidence_artifacts must be a list")
    root = result_path.parent.resolve()
    artifacts_by_id = {}
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ResultRecordError(f"evidence_artifacts[{index}] must be an object")
        artifact_id = artifact.get("id")
        _nonblank(artifact_id, f"evidence_artifacts[{index}].id")
        if artifact_id in artifacts_by_id:
            raise ResultRecordError(f"duplicate evidence artifact ID: {artifact_id}")
        relative = PurePosixPath(str(artifact.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ResultRecordError(f"artifact path must stay inside result directory: {artifact.get('path')}")
        try:
            path = (root / Path(*relative.parts)).resolve(strict=True)
            path.relative_to(root)
            size_bytes = artifact.get("size_bytes")
            if (isinstance(size_bytes, bool) or not isinstance(size_bytes, int)
                    or not 0 <= size_bytes <= MAX_EVIDENCE_BYTES or path.stat().st_size != size_bytes):
                raise ResultRecordError(f"evidence artifact size is invalid or exceeds 200 MB: {artifact_id}")
            raw = path.read_bytes()
        except (OSError, ValueError) as exc:
            if isinstance(exc, ResultRecordError):
                raise
            raise ResultRecordError(f"evidence artifact is missing or outside result directory: {artifact.get('path')}") from exc
        digest = hashlib.sha256(raw).hexdigest()
        if artifact.get("sha256") != digest or artifact.get("size_bytes") != len(raw):
            raise ResultRecordError(f"evidence artifact hash or byte count mismatch: {artifact_id}")
        _nonblank(artifact.get("kind"), f"evidence_artifacts[{index}].kind")
        artifacts_by_id[artifact_id] = artifact

    gate_results = result.get("gate_results")
    if not isinstance(gate_results, list):
        raise ResultRecordError("gate_results must be a list")
    seen_gates = set()
    measured_count = 0
    not_measured_count = 0
    for index, gate_result in enumerate(gate_results):
        if not isinstance(gate_result, dict):
            raise ResultRecordError(f"gate_results[{index}] must be an object")
        step_id, gate = gate_result.get("step_id"), gate_result.get("gate")
        _nonblank(step_id, f"gate_results[{index}].step_id")
        _nonblank(gate, f"gate_results[{index}].gate")
        key = (step_id, gate)
        if key not in expected_gates:
            raise ResultRecordError(f"gate result does not match a compiled step and gate: {key}")
        if key in seen_gates:
            raise ResultRecordError(f"duplicate result for step/gate: {key}")
        seen_gates.add(key)
        status = gate_result.get("status")
        if status not in ("measured_pass", "measured_fail", "indeterminate", "not_measured", "not_applicable"):
            raise ResultRecordError(f"unknown gate result status for {key}")
        if status in {"measured_pass", "measured_fail", "indeterminate"}:
            _finite_value(gate_result.get("observed_value"), f"gate_results[{index}].observed_value")
            _nonblank(gate_result.get("unit"), f"gate_results[{index}].unit")
            _nonblank(gate_result.get("method"), f"gate_results[{index}].method")
            _nonblank(gate_result.get("evidence_artifact_id"), f"gate_results[{index}].evidence_artifact_id")
            if gate_result["evidence_artifact_id"] not in artifacts_by_id:
                raise ResultRecordError(f"gate result references an undeclared artifact: {key}")
            measured_count += 1
        else:
            _nonblank(gate_result.get("reason"), f"gate_results[{index}].reason")
            not_measured_count += status == "not_measured"
    if seen_gates != expected_gates:
        missing = sorted(expected_gates - seen_gates)
        raise ResultRecordError(f"result must explicitly record every compiled gate; missing: {missing}")

    deviations = result.get("deviations")
    if not isinstance(deviations, list):
        raise ResultRecordError("deviations must be a list")
    for index, deviation in enumerate(deviations):
        if not isinstance(deviation, dict):
            raise ResultRecordError(f"deviations[{index}] must be an object")
        _nonblank(deviation.get("step_id"), f"deviations[{index}].step_id")
        if deviation["step_id"] not in steps:
            raise ResultRecordError(f"deviations[{index}] references an unknown protocol step")
        for field in ("item", "unit", "reason", "evidence_artifact_id"):
            _nonblank(deviation.get(field), f"deviations[{index}].{field}")
        _finite_value(deviation.get("planned_value"), f"deviations[{index}].planned_value")
        _finite_value(deviation.get("observed_value"), f"deviations[{index}].observed_value")
        if deviation["evidence_artifact_id"] not in artifacts_by_id:
            raise ResultRecordError(f"deviation references an undeclared artifact at row {index}")

    return {
        "schema_version": 1,
        "validation_status": "record_integrity_valid",
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["protocol_sha256"],
        "compiled_protocol_sha256": compiled_digest,
        "run_id": result["run_id"],
        "disposition": result["disposition"],
        "n_compiled_gates": len(expected_gates),
        "n_measured_gates": measured_count,
        "n_not_measured_gates": not_measured_count,
        "n_deviations": len(deviations),
        "n_evidence_artifacts": len(artifacts_by_id),
        "note": "Structural, reference and local hash checks passed. This does not certify execution, gate quality, culture success or suitability for use.",
    }
