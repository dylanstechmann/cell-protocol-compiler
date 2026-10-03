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
    parameters = {parameter.name: parameter for parameter in protocol.parameters}
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
                "required": parameter.name in protocol.required_parameters,
                "note": parameter.note,
            }
            for parameter in protocol.parameters
        ],
        "required_gates": {
            step.id: sorted(step.required_gates)
            for step in sorted(protocol.steps, key=lambda item: (item.start_hour, item.id))
            if step.required_gates
        },
        "required_step_reagents": {
            step_id: list(reagents)
            for step_id, reagents in sorted(protocol.required_step_reagents.items())
        },
        "exclusivity": exclusivity,
        "max_hours_between_medium_changes": protocol.max_hours_between_medium_changes,
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "non_claims": list(protocol.non_claims),
    }
