"""Versioned constraint export for downstream planners.

The compiled checklist is for humans. This export is for a planner such as
diffmedia-loop: it states, per protocol, the published factor windows a search
may use, the required parameters and gates, and mutually exclusive
alternatives. It never widens or invents a window, and a quarantined source
record exports nothing.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from protocolcompiler.schema import Protocol, ProtocolError
from protocolcompiler.validate import ALLOWED_ACTIONS, EXCLUSIVITY_RULES, validate

CONSTRAINTS_SCHEMA_VERSION = 1


def protocol_hash(protocol: Protocol) -> str:
    """Canonical content hash, identical to the one in compiled output."""
    payload = json.dumps(asdict(protocol), sort_keys=True, allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def export_constraints(protocol: Protocol) -> dict:
    """Return a validated, deterministic, machine-readable constraint set."""
    # A quarantined or inconsistent record exports nothing.
    validate(protocol)
    from protocolcompiler.library import LIBRARY
    canonical = LIBRARY[protocol.id]() if protocol.id in LIBRARY else None
    required_parameters = set(protocol.required_parameters)
    required_gates = {step.id: set(step.required_gates) for step in protocol.steps}
    required_reagents = {step_id: set(reagents) for step_id, reagents in protocol.required_step_reagents.items()}
    if canonical is not None:
        required_parameters.update(canonical.required_parameters)
        for step in canonical.steps:
            required_gates.setdefault(step.id, set()).update(step.required_gates)
        for step_id, reagents in canonical.required_step_reagents.items():
            required_reagents.setdefault(step_id, set()).update(reagents)
    parameters = {parameter.name: parameter for parameter in protocol.parameters}
    use_ldn_substitute = any(
        "ldn193189" in parameter.name.casefold().replace("_", "") and parameter.value > 0
        for parameter in protocol.parameters
    )
    exclusivity = EXCLUSIVITY_RULES.get(protocol.id, [])
    for rule in exclusivity:
        unknown = [name for name in rule["parameters"] if name not in parameters]
        if unknown:
            raise ProtocolError(
                [f"exclusivity rule references unknown parameters: {', '.join(unknown)}"]
            )
    return {
        "schema_version": CONSTRAINTS_SCHEMA_VERSION,
        "protocol_id": protocol.id,
        "title": protocol.title,
        "doi": protocol.doi,
        "protocol_sha256": protocol_hash(protocol),
        "parameters": [
            {
                "name": parameter.name,
                "unit": parameter.unit,
                "low": parameter.low,
                "high": parameter.high,
                "value": parameter.value,
                "required": parameter.name in required_parameters,
                "note": parameter.note,
            }
            for parameter in protocol.parameters
        ],
        "required_gates": {
            step.id: sorted(required_gates[step.id])
            for step in sorted(protocol.steps, key=lambda item: (item.start_hour, item.id))
            if required_gates[step.id]
        },
        "required_step_reagents": {
            step_id: sorted(
                "LDN-193189" if use_ldn_substitute and reagent.casefold() == "noggin" else reagent
                for reagent in reagents
            )
            for step_id, reagents in sorted(required_reagents.items())
        },
        "exclusivity": exclusivity,
        "max_hours_between_medium_changes": protocol.max_hours_between_medium_changes,
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "non_claims": list(protocol.non_claims),
    }
