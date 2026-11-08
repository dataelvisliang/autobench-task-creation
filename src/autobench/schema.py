"""Task package schema (METHOD.md Section 2.2, paper Appendix A.1 Stage 1-B).

A submission is a set of native tasks. Each task carries an instruction,
configuration, solver-visible assets, a deterministic reference solution,
and a verifier side: grading criteria, a judging context, and a private
reference answer.

Criteria are binary, Likert, or numeric items with positive weights and
stable identifiers. Regexes, required phrases, length targets, and
model-specific criteria are prohibited by the recipe and rejected here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CRITERION_KINDS = ("binary", "likert", "numeric")

# Keys that would smuggle a prohibited grading style into a criterion.
FORBIDDEN_CRITERION_KEYS = (
    "regex",
    "pattern",
    "required_phrases",
    "required_phrase",
    "length_target",
    "min_length",
    "max_length",
    "model_specific",
    "model_name",
)


@dataclass
class Criterion:
    """One grading criterion with a stable identifier and positive weight."""

    id: str
    kind: str
    weight: float
    description: str = ""
    points: int | None = None  # Likert only, must be >= 2
    value_range: tuple[float, float] | None = None  # numeric only, explicit

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id or not self.id.strip():
            errors.append("criterion id must be a non-empty stable identifier")
        if self.kind not in CRITERION_KINDS:
            errors.append(
                f"criterion {self.id!r}: kind must be one of {CRITERION_KINDS}, got {self.kind!r}"
            )
        if not (self.weight > 0):
            errors.append(f"criterion {self.id!r}: weight must be positive, got {self.weight}")
        if self.kind == "likert":
            if self.points is None or self.points < 2:
                errors.append(f"criterion {self.id!r}: Likert items need at least two points")
        if self.kind == "numeric":
            if self.value_range is None or self.value_range[0] >= self.value_range[1]:
                errors.append(f"criterion {self.id!r}: numeric items need an explicit range")
        return errors

    @classmethod
    def from_dict(cls, raw: dict) -> "Criterion":
        forbidden = [k for k in FORBIDDEN_CRITERION_KEYS if k in raw]
        if forbidden:
            raise ValueError(
                "criterion uses prohibited grading keys: " + ", ".join(sorted(forbidden))
            )
        value_range = raw.get("range")
        return cls(
            id=raw["id"],
            kind=raw["kind"],
            weight=float(raw["weight"]),
            description=raw.get("description", ""),
            points=raw.get("points"),
            value_range=tuple(value_range) if value_range is not None else None,
        )

    def to_dict(self) -> dict:
        out: dict = {
            "id": self.id,
            "kind": self.kind,
            "weight": self.weight,
            "description": self.description,
        }
        if self.points is not None:
            out["points"] = self.points
        if self.value_range is not None:
            out["range"] = list(self.value_range)
        return out


@dataclass
class TaskPackage:
    """One complete task in a benchmark submission."""

    name: str
    instruction: str
    criteria: list[Criterion]
    judging_context: str = ""
    reference_answer: str = ""
    reference_solution: str = ""  # file name inside the task directory
    assets: list[str] = field(default_factory=list)  # solver-visible file names

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name.strip():
            errors.append("task name must be non-empty")
        if not self.instruction.strip():
            errors.append(f"task {self.name!r}: instruction must be non-empty")
        if not self.criteria:
            errors.append(f"task {self.name!r}: at least one grading criterion is required")
        seen: set[str] = set()
        for criterion in self.criteria:
            errors.extend(criterion.validate())
            if criterion.id in seen:
                errors.append(f"task {self.name!r}: duplicate criterion id {criterion.id!r}")
            seen.add(criterion.id)
        return errors


def load_criteria(path: str | Path) -> list[Criterion]:
    """Load criteria from a criteria.json file (a list of criterion objects)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("criteria file must contain a JSON list")
    return [Criterion.from_dict(item) for item in raw]
