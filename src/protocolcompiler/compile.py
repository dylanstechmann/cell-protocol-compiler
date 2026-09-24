"""Turn a validated protocol into a checklist, a schedule, and a reagent list."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from protocolcompiler.schema import Protocol
from protocolcompiler.validate import validate


def compile_protocol(protocol: Protocol) -> dict:
    warnings = validate(protocol)
    schedule = []
    for step in sorted(protocol.steps, key=lambda item: (item.start_hour, item.id)):
        day = int(step.start_hour // 24)
        hour = step.start_hour - 24 * day
        schedule.append({
            "id": step.id,
            "day": day,
            "hour": round(hour, 2),
            "start_hour": step.start_hour,
            "action": step.action,
            "title": step.title,
            "hood_minutes": step.hood_minutes,
            "volume_ml": step.volume_ml,
            "reagents": list(step.reagents),
            "gates": list(step.gates),
            "detail": step.detail,
        })
    bom: dict[str, list[str]] = {}
    for step in protocol.steps:
        for reagent in step.reagents:
            bom.setdefault(reagent, []).append(step.id)
    checklist = _markdown(protocol, schedule, warnings)
    return {
        "schema_version": 1,
        "protocol_sha256": hashlib.sha256(json.dumps(asdict(protocol), sort_keys=True,
                                                     allow_nan=False).encode()).hexdigest(),
        "id": protocol.id,
        "title": protocol.title,
        "citation": protocol.citation,
        "doi": protocol.doi,
        "warnings": warnings,
        "parameters": [
            {
                "name": param.name,
                "value": param.value,
                "unit": param.unit,
                "low": param.low,
                "high": param.high,
                "note": param.note,
            }
            for param in protocol.parameters
        ],
        "formulation": [
            {"name": row.name, "amount": row.amount, "unit": row.unit, "note": row.note}
            for row in protocol.formulation
        ],
        "schedule": schedule,
        "bom": bom,
        "critical_control_points": _controls(),
        "checklist_markdown": checklist,
    }


def _controls() -> list[str]:
    return [
        "Work in a certified Class II biosafety cabinet. A perfusion pump is not a cabinet.",
        "Identity (STR or equivalent), karyotype, and mycoplasma are vendor or core assays. This compiler does not perform them.",
        "Small-molecule windows are line-dependent. A value inside the published range can still kill a given line.",
        "Nothing in this checklist is a GMP batch record, an IND section, or a procedure for putting cells into a person.",
    ]


def _markdown(protocol: Protocol, schedule: list[dict], warnings: list[str]) -> str:
    lines = [
        f"# {protocol.title}",
        "",
        protocol.summary,
        "",
        f"Source: {protocol.citation}",
        f"DOI: https://doi.org/{protocol.doi}",
        f"Vessel assumption: {protocol.vessel}",
        f"Biosafety: {protocol.biosafety}",
        "",
        "## Not this",
    ]
    lines.extend(f"- {claim}" for claim in protocol.non_claims)
    if protocol.parameters:
        lines.extend(["", "## Parameters (published windows, not prescriptions)"])
        for param in protocol.parameters:
            lines.append(
                f"- {param.name}: {param.value:g} {param.unit} "
                f"(allowed here {param.low:g}–{param.high:g}). {param.note}"
            )
    if protocol.formulation:
        lines.extend(["", "## Published formulation snapshot"])
        for row in protocol.formulation:
            extra = f" {row.note}" if row.note else ""
            lines.append(f"- {row.name}: {row.amount:g} {row.unit}.{extra}")
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(["", "## Schedule"])
    for row in schedule:
        vol = f", {row['volume_ml']} mL/well" if row["volume_ml"] else ""
        gates = f" Gates: {', '.join(row['gates'])}." if row["gates"] else ""
        lines.append(
            f"- Day {row['day']} + {row['hour']:.1f} h ({row['action']}, "
            f"{row['hood_minutes']:.0f} min hands-on{vol}): {row['title']}. {row['detail']}{gates}"
        )
    lines.extend(["", "## Critical control points"])
    lines.extend(f"- {item}" for item in _controls())
    lines.append("")
    return "\n".join(lines)
