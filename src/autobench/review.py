"""Benchmark review (METHOD.md Section 4, paper Appendix A.3).

Five judges, one per criterion, run in isolation. The criterion wording
is canonical and is disclosed verbatim to the proposing agent. Each
judge returns a JSON verdict in a fixed format, validated here.
"""

from __future__ import annotations

from dataclasses import dataclass

CRITERIA: dict[str, str] = {
    "construct_validity": (
        "The benchmark measures the research-agent capability claimed in the brief "
        "and the specification, not an incidental proxy or an evaluator quirk."
    ),
    "correctness": (
        "Task artifacts, private references, rubric semantics, score calculation, "
        "and reproducibility are internally correct and free of leakage."
    ),
    "feasibility": (
        "A genuinely stronger research agent could solve the benchmark with the "
        "supplied evidence, resources, and rules; difficulty from missing evidence, "
        "impossible requirements, or circular evaluation is rejected."
    ),
    "usefulness": (
        "Progress would transfer to meaningful scientific work or provide valuable "
        "evidence about research-agent capability."
    ),
    "overall": (
        "The integrated contribution has no serious red flags and is a credible "
        "publication-quality benchmark design at the current scale."
    ),
}

RESPONSIBILITIES = ("submission", "harness")
DECISIONS = ("pass", "fail")


@dataclass
class Verdict:
    criterion: str
    decision: str  # "pass" or "fail"
    responsibility: str  # "submission" or "harness"
    citations: list[str]
    strengths: list[str]
    weaknesses: list[str]
    required_fixes: list[str]
    confidence: float  # 0..1
    rationale: str

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.criterion not in CRITERIA:
            errors.append(f"unknown criterion: {self.criterion!r}")
        if self.decision not in DECISIONS:
            errors.append(f"verdict {self.criterion}: decision must be one of {DECISIONS}")
        if self.responsibility not in RESPONSIBILITIES:
            errors.append(
                f"verdict {self.criterion}: responsibility must separate submission "
                f"defects from harness faults, one of {RESPONSIBILITIES}"
            )
        if len(self.citations) < 3:
            errors.append(f"verdict {self.criterion}: at least three artifact citations required")
        if not self.strengths:
            errors.append(f"verdict {self.criterion}: at least one strength required")
        if not self.weaknesses:
            errors.append(f"verdict {self.criterion}: at least one weakness required")
        if self.decision == "fail" and not self.required_fixes:
            errors.append(f"verdict {self.criterion}: a fail verdict needs required fixes")
        if not (0.0 <= self.confidence <= 1.0):
            errors.append(f"verdict {self.criterion}: confidence must be in [0, 1]")
        if not self.rationale.strip():
            errors.append(f"verdict {self.criterion}: rationale is required")
        return errors

    @classmethod
    def from_dict(cls, criterion: str, raw: dict) -> "Verdict":
        return cls(
            criterion=criterion,
            decision=raw["decision"],
            responsibility=raw["responsibility"],
            citations=list(raw.get("citations", [])),
            strengths=list(raw.get("strengths", [])),
            weaknesses=list(raw.get("weaknesses", [])),
            required_fixes=list(raw.get("required_fixes", [])),
            confidence=float(raw.get("confidence", 0.0)),
            rationale=raw.get("rationale", ""),
        )


def all_passed(verdicts: dict[str, Verdict]) -> bool:
    """True when every one of the five criteria has a passing verdict."""
    if set(verdicts) != set(CRITERIA):
        return False
    return all(v.decision == "pass" for v in verdicts.values())
