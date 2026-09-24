"""Reject protocols that skip sterile gates or invent out-of-range doses."""

from __future__ import annotations

from protocolcompiler.schema import Protocol, ProtocolError

MEDIUM_ACTIONS = {"medium_change", "passage", "seed"}
REQUIRED_NONCLAIM = "not for administration to humans"


def validate(protocol: Protocol) -> list[str]:
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
    for param in protocol.parameters:
        if not (param.low <= param.value <= param.high):
            errors.append(
                f"{param.name}={param.value} {param.unit} is outside {param.low}–{param.high}"
            )
    seen = set()
    for step in protocol.steps:
        if step.id in seen:
            errors.append(f"duplicate step id {step.id}")
        seen.add(step.id)
        if step.start_hour < 0:
            errors.append(f"{step.id} has a negative start")
        if step.hood_minutes < 0 or step.hood_minutes > 180:
            errors.append(f"{step.id} hood time is not plausible")
        if step.volume_ml is not None and not (0 < step.volume_ml <= 15):
            errors.append(f"{step.id} volume {step.volume_ml} mL is outside 0–15 mL per well")
        if step.action not in {
            "coat", "seed", "medium_change", "passage", "qc", "endpoint", "note",
        }:
            errors.append(f"{step.id} has unknown action {step.action}")
    _exclusive_overlap(protocol, errors)
    _feed_gaps(protocol, errors)
    if not any(step.action == "qc" or step.gates for step in protocol.steps):
        errors.append("no QC gate")
    if not any(step.action == "endpoint" for step in protocol.steps):
        errors.append("no endpoint")
    _dual_smad_warning(protocol, warnings)
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
    for (t0, a), (t1, b) in zip(feeds, feeds[1:]):
        gap = t1 - t0
        if gap > protocol.max_hours_between_medium_changes:
            errors.append(
                f"medium gap {gap:.1f} h between {a} and {b} exceeds "
                f"{protocol.max_hours_between_medium_changes:.0f} h"
            )


def _dual_smad_warning(protocol: Protocol, warnings: list[str]) -> None:
    names = {step.id for step in protocol.steps}
    joined = " ".join(step.detail.lower() for step in protocol.steps)
    if "noggin" in joined and "ldn" in joined and "substitute" not in joined:
        warnings.append("Noggin and LDN-193189 are both mentioned without saying one substitutes for the other.")
    if "ldn_and_noggin" in names:
        warnings.append("combined Noggin plus LDN was not the Chambers 2009 condition")
