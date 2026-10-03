"""Reject protocols that skip sterile gates or invent out-of-range doses."""

from __future__ import annotations

import math

from protocolcompiler.schema import Protocol, ProtocolError

MEDIUM_ACTIONS = {"medium_change", "passage", "seed"}
REQUIRED_NONCLAIM = "not for administration to humans"

# Shared with the constraints export so planners and the validator describe
# the same action vocabulary.
ALLOWED_ACTIONS = {
    "coat", "seed", "medium_change", "passage", "qc", "endpoint", "note",
}

# Mutually exclusive alternatives. protocolcompiler.constraints exports these
# to planners; validate() enforces the same rules at compile time, and both
# read this single table. An inactive value marks the explicit "not used"
# state for a member while one alternative is positive (for example Noggin 0
# while LDN-193189 carries the BMP inhibition).
EXCLUSIVITY_RULES: dict[str, list[dict]] = {
    "dual_smad_neural": [
        {
            "parameters": ["Noggin_ng_per_mL", "LDN193189_nM"],
            "rule": "at_most_one_positive",
            "minimum_positive": 1,
            "inactive_values": {"Noggin_ng_per_mL": 0, "LDN193189_nM": 0},
            "rationale": (
                "Noggin (Chambers et al. 2009) and LDN-193189 are substitutes for the same "
                "BMP-signal inhibition; the encoded dual-SMAD workflow never stacks them."
            ),
        }
    ],
}


def _parameter_value(protocol: Protocol, name: str) -> float | None:
    for parameter in protocol.parameters:
        if parameter.name == name:
            return parameter.value
    return None


def _inactive_alternative_values(protocol: Protocol) -> dict[str, float]:
    """Inactive values members may take while one alternative is positive.

    The constraints export promises planners the same semantics: a member can
    sit at its declared inactive value (for example Noggin 0 while LDN-193189
    is used) even though that value sits outside its published window, because
    the window describes the factor only when it is in use.
    """
    exceptions: dict[str, float] = {}
    for rule in EXCLUSIVITY_RULES.get(protocol.id, []):
        members = rule.get("parameters", [])
        inactive = dict(rule.get("inactive_values", {}))
        positives = [
            name for name in members
            if (value := _parameter_value(protocol, name)) is not None
            and value > inactive.get(name, 0.0)
        ]
        if not positives:
            continue
        for name in members:
            if name in positives or name not in inactive:
                continue
            exceptions[name] = float(inactive[name])
    return exceptions


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
    inactive_alternatives = _inactive_alternative_values(protocol)
    for param in protocol.parameters:
        in_window = (
            all(math.isfinite(v) for v in (param.low, param.value, param.high))
            and param.low <= param.value <= param.high
        )
        if in_window:
            continue
        inactive = inactive_alternatives.get(param.name)
        if inactive is not None and math.isclose(param.value, inactive, rel_tol=0.0, abs_tol=1e-12):
            # An exclusivity member resting at its declared inactive value
            # while one alternative is positive is not a window violation.
            continue
        errors.append(
            f"{param.name}={param.value} {param.unit} is outside {param.low}–{param.high}"
        )
    seen = set()
    has_qc_gate = False
    # Hood-overlap and feed-gap checks are derived from step timing and from
    # the medium-gap limit. Track whether those primitives are usable; unrelated
    # structural errors (for example a stripped required-reagent rule) must not
    # mask a feed-gap safeguard violation.
    derived_inputs_valid = (
        math.isfinite(protocol.max_hours_between_medium_changes)
        and protocol.max_hours_between_medium_changes > 0
    )

    step_by_id = {step.id: step for step in protocol.steps}
    for unknown in sorted(set(protocol.required_step_reagents) - set(step_by_id)):
        errors.append(f"required reagent rule references unknown step {unknown}")
    ldn = next((p for p in protocol.parameters
                if "ldn193189" in p.name.casefold().replace("_", "")), None)
    use_ldn_substitute = ldn is not None and ldn.value > 0
    for step in protocol.steps:
        if step.id in seen:
            errors.append(f"duplicate step id {step.id}")
        seen.add(step.id)
        if not math.isfinite(step.start_hour) or step.start_hour < 0:
            errors.append(f"{step.id} must have a finite nonnegative start")
            derived_inputs_valid = False
        if not math.isfinite(step.hood_minutes) or step.hood_minutes < 0 or step.hood_minutes > 180:
            errors.append(f"{step.id} hood time is not plausible")
            derived_inputs_valid = False
        if step.volume_ml is not None and (not math.isfinite(step.volume_ml) or not (0 < step.volume_ml <= 15)):
            errors.append(f"{step.id} volume {step.volume_ml} mL is outside 0–15 mL per well")
        if step.action not in ALLOWED_ACTIONS:
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
        actual_reagents = {reagent.casefold() for reagent in step.reagents if isinstance(reagent, str)}
        for reagent in protocol.required_step_reagents.get(step.id, ()):
            expected = "LDN-193189" if use_ldn_substitute and reagent.casefold() == "noggin" else reagent
            if expected.casefold() not in actual_reagents:
                errors.append(f"{step.id} is missing required reagent: {expected}")
    for row in protocol.formulation:
        if not math.isfinite(row.amount) or row.amount <= 0:
            errors.append(f"{row.name} formulation amount must be finite and positive")
    if derived_inputs_valid:
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
    if noggin is not None and ldn is not None and noggin.value <= 0 and ldn.value <= 0:
        errors.append("dual-SMAD induction requires one positive BMP-inhibition alternative: Noggin or LDN-193189")
    if ldn is not None and ldn.value > 0:
        noggin_references = [
            step.id for step in protocol.steps
            if "noggin" in " ".join(step.reagents).casefold()
            or (step.id in protocol.required_step_reagents and "noggin" in step.detail.casefold())
        ]
        if noggin_references:
            errors.append("LDN-193189 is set positive while an induction step still lists or describes Noggin; update structured reagents and narrative together")
