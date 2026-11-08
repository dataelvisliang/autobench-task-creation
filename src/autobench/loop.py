"""The iteration loop (METHOD.md Section 5, paper Appendix A.4).

Checkpoint selection: an iteration is eligible when all five review
verdicts passed and its solver evaluation is complete. Among eligible
iterations the loop takes the lowest mean reward on the designated
selection solver, breaking ties toward the later iteration. With nothing
eligible it falls back to the latest fully evaluated iteration and
labels the session a repair.

Feedback: one curated, secret-scanned bundle per iteration. Only files
named by the bundle index may be read by the next session.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IterationRecord:
    iteration: int
    all_verdicts_pass: bool
    eval_complete: bool
    selection_reward: float | None  # mean reward of the selection solver


@dataclass
class CheckpointChoice:
    iteration: int | None
    label: str  # "selected", "repair_fallback", or "none"


def select_checkpoint(history: list[IterationRecord]) -> CheckpointChoice:
    eligible = [
        record
        for record in history
        if record.all_verdicts_pass and record.eval_complete and record.selection_reward is not None
    ]
    if eligible:
        # Lowest reward wins; ties break toward the later iteration.
        best = min(eligible, key=lambda r: (r.selection_reward, -r.iteration))
        return CheckpointChoice(iteration=best.iteration, label="selected")
    fully_evaluated = [record for record in history if record.eval_complete]
    if fully_evaluated:
        latest = max(fully_evaluated, key=lambda r: r.iteration)
        return CheckpointChoice(iteration=latest.iteration, label="repair_fallback")
    return CheckpointChoice(iteration=None, label="none")


_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style key
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),  # GitHub personal token
]


def scan_for_secrets(name: str, content: str) -> list[str]:
    hits = [pattern.pattern for pattern in _SECRET_PATTERNS if pattern.search(content)]
    return [f"{name}: matches secret pattern {hit}" for hit in hits]


def write_feedback_bundle(out_dir: str | Path, files: dict[str, str]) -> Path:
    """Write a feedback bundle: the given files plus an index.json.

    Raises ValueError if any file looks like it contains a secret, so a
    bundle is never published with credentials inside it.
    """
    problems: list[str] = []
    for name, content in files.items():
        problems.extend(scan_for_secrets(name, content))
    if problems:
        raise ValueError("feedback bundle blocked by secret scan: " + "; ".join(problems))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    index = {"files": sorted(files)}
    (out / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return out
