"""Records for a research protocol checklist. Not a batch record."""

from __future__ import annotations

from dataclasses import dataclass, field


class ProtocolError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass
class Parameter:
    name: str
    value: float
    unit: str
    low: float
    high: float
    note: str


@dataclass
class FormulationComponent:
    name: str
    amount: float
    unit: str
    note: str = ""


@dataclass
class Step:
    id: str
    start_hour: float
    title: str
    detail: str
    action: str
    hood_minutes: float = 10.0
    volume_ml: float | None = None
    reagents: list[str] = field(default_factory=list)
    gates: list[str] = field(default_factory=list)
    required_gates: tuple[str, ...] = ()

    def __post_init__(self):
        # Freeze the authored checklist gates so later accidental deletion or
        # substitution cannot make an incomplete step validate itself.
        if not self.required_gates:
            self.required_gates = tuple(self.gates)


@dataclass
class Protocol:
    id: str
    title: str
    citation: str
    doi: str
    biosafety: str
    vessel: str
    max_hours_between_medium_changes: float
    summary: str
    parameters: list[Parameter] = field(default_factory=list)
    formulation: list[FormulationComponent] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    non_claims: list[str] = field(default_factory=list)
    required_parameters: tuple[str, ...] = ()
    compilable: bool = True
    compilability_note: str = ""

    def __post_init__(self):
        # The factory's parameter names form its required schema. Callers may
        # tune values, but removing one must be an explicit schema change.
        if not self.required_parameters:
            self.required_parameters = tuple(parameter.name for parameter in self.parameters)

    def parameter(self, name: str) -> Parameter:
        for item in self.parameters:
            if item.name == name:
                return item
        raise KeyError(name)
