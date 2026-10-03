"""Reject protocols that skip sterile gates or invent out-of-range doses."""

from __future__ import annotations

import math

from protocolcompiler.schema import Protocol, ProtocolError

MEDIUM_ACTIONS = {"medium_change", "passage", "seed"}
REQUIRED_NONCLAIM = "not for administration to humans"


def validate(protocol: Protocol) -> list[str]:
    if not protocol.compilable:
        note = protocol.compilability_note or "source review has not cleared this protocol for compilation"
        raise ProtocolError([f"protocol is not eligible for compilation: {note}"])
    errors: list[str] = []
    warnings: list[str] = []
    if not protocol.doi.startswith("10."):
        errors.append("doi is missing")
    if "BSL-2" not in protocol.biosafety:
        errors.append("biosafety line must name BSL-2")
    if not any(REQUIRED_NONCLAIM in claim.lower() for claim in protocol.non_claims):
        errors.append("non_claims must state the work is not for administration to humans")
    if not protocol.steps:
        errors.append("no steps")
    if (not math.isfinite(protocol.max_hours_between_medium_changes)
            or protocol.max_hours_between_medium_changes <= 0):
        errors.append("maximum medium-change gap must be finite and positive")
    if len({p.name for p in protocol.parameters}) != len(protocol.parameters):
        errors.append("duplicate parameter names")
    present_parameters = {parameter.name for parameter in protocol.parameters}
    for name in protocol.required_parameters:
        if name not in present_parameters:
            errors.append(f"missing required parameter: {name}")
    for param in protocol.parameters:
        if not all(math.isfinite(v) for v in (param.low, param.value, param.high)) or not (param.low <= param.value <= param.high):
            errors.append(
                f"{param.name}={param.value} {param.unit} is outside {param.low}–{param.high}"
            )
    seen = set()
    has_qc_gate = False
    for step in protocol.steps:
        if step.id in seen:
            errors.append(f"duplicate step id {step.id}")
        seen.add(step.id)
        if not math.isfinite(step.start_hour) or step.start_hour < 0:
            errors.append(f"{step.id} must have a finite nonnegative start")
        if not math.isfinite(step.hood_minutes) or step.hood_minutes < 0 or step.hood_minutes > 180:
            errors.append(f"{step.id} hood time is not plausible")
        if step.volume_ml is not None and (not math.isfinite(step.volume_ml) or not (0 < step.volume_ml <= 15)):
            errors.append(f"{step.id} volume {step.volume_ml} mL is outside 0–15 mL per well")
        if step.action not in {
            "coat", "seed", "medium_change", "passage", "qc", "endpoint", "note",
        }:
            errors.append(f"{step.id} has unknown action {step.action}")
        if not isinstance(step.gates, list) or any(
                not isinstance(gate, str) or not gate.strip() for gate in step.gates):
            errors.append(f"{step.id} gates must be a list of nonblank strings")
        elif step.action != "note" and step.gates:
            has_qc_gate = True
        if isinstance(step.gates, list) and all(isinstance(gate, str) and gate.strip() for gate in step.gates):
            missing_gates = set(step.required_gates) - set(step.gates)
            if missing_gates:
                errors.append(f"{step.id} is missing required gate(s): {', '.join(sorted(missing_gates))}")
    for row in protocol.formulation:
        if not math.isfinite(row.amount) or row.amount <= 0:
            errors.append(f"{row.name} formulation amount must be finite and positive")
    if not errors:
        _exclusive_overlap(protocol, errors)
        _feed_gaps(protocol, errors)
    if not has_qc_gate:
        errors.append("no QC gate")
    endpoints = [step for step in protocol.steps if step.action == "endpoint"]
    if len(endpoints) != 1:
        errors.append("exactly one endpoint is required")
    elif any(step.action != "note" and step.start_hour > endpoints[0].start_hour
             for step in protocol.steps):
        errors.append("active step occurs after endpoint")
    _validate_dual_smad_constraints(protocol, errors)
    if errors:
        raise ProtocolError(errors)
    return warnings


def _exclusive_overlap(protocol: Protocol, errors: list[str]) -> None:
    windows = []
    for step in protocol.steps:
        if step.hood_minutes <= 0 or step.action == "note":
            continue
        start = step.start_hour
        end = step.start_hour + step.hood_minutes / 60.0
        windows.append((start, end, step.id))
    windows.sort()
    for i in range(len(windows) - 1):
        if windows[i][1] > windows[i + 1][0] + 1e-9:
            errors.append(f"hood overlap: {windows[i][2]} and {windows[i + 1][2]}")


def _feed_gaps(protocol: Protocol, errors: list[str]) -> None:
    feeds = sorted(
        (step.start_hour, step.id)
        for step in protocol.steps
        if step.action in MEDIUM_ACTIONS
    )
    if not feeds:
        errors.append("no seed, passage, or medium change")
        return
    # The interval after the final feed matters as much as interior intervals.
    endpoints = [s for s in protocol.steps if s.action == "endpoint"]
    if endpoints:
        final = max(endpoints, key=lambda s: s.start_hour)
        if final.start_hour < feeds[-1][0]:
            errors.append("endpoint occurs before the final medium action")
        elif final.start_hour > feeds[-1][0]:
            feeds.append((final.start_hour, final.id))
    for (t0, a), (t1, b) in zip(feeds, feeds[1:]):
        gap = t1 - t0
        if gap > protocol.max_hours_between_medium_changes:
            errors.append(
                f"medium gap {gap:.1f} h between {a} and {b} exceeds "
                f"{protocol.max_hours_between_medium_changes:.0f} h"
            )


def _validate_dual_smad_constraints(protocol: Protocol, errors: list[str]) -> None:
    parameters = {parameter.name.casefold(): parameter for parameter in protocol.parameters}
    noggin = next((p for name, p in parameters.items() if "noggin" in name), None)
    ldn = next((p for name, p in parameters.items() if "ldn193189" in name or "ldn_193189" in name), None)
    if noggin is not None and ldn is not None and noggin.value > 0 and ldn.value > 0:
        errors.append("Noggin and LDN-193189 are mutually exclusive in the encoded dual-SMAD workflow")
    if ldn is not None and ldn.value > 0:
        noggin_references = [step.id for step in protocol.steps if "noggin" in " ".join(step.reagents).casefold()]
        if noggin_references:
            errors.append("LDN-193189 is set positive while steps still list Noggin; update structured reagents and narrative together")
