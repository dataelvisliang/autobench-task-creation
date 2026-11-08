#!/usr/bin/env python3
"""Quickstart: run one example task through the AutoBenchmark gates and loop.

No API keys and no model calls. The grader really executes the reference
solution; solvers and review judges are deterministic stubs that stand in
for the model roles described in METHOD.md.

Run:  PYTHONPATH=src python examples/quickstart.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from autobench import gates, loop, review, schema  # noqa: E402

TASK_DIR = Path(__file__).resolve().parent / "example_task"


def real_grader(solution_path: Path) -> float:
    """Execute the reference solution and compare with the private reference."""
    completed = subprocess.run(
        [sys.executable, str(solution_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"solution exited with {completed.returncode}")
    expected = (TASK_DIR / "private_reference.txt").read_text(encoding="utf-8").strip()
    return 1.0 if completed.stdout.strip() == expected else 0.0


def stub_verdicts(decision: str) -> dict[str, review.Verdict]:
    return {
        criterion: review.Verdict(
            criterion=criterion,
            decision=decision,
            responsibility="submission",
            citations=["instruction.md", "criteria.json", "private_reference.txt"],
            strengths=["grounding is retained and hashed"],
            weaknesses=["only one task in this demo package"],
            required_fixes=[] if decision == "pass" else ["see METHOD.md Section 4"],
            confidence=0.9,
            rationale="stub verdict for the offline quickstart",
        )
        for criterion in review.CRITERIA
    }


def main() -> int:
    print("== AutoBenchmark scaffold quickstart ==")

    criteria = schema.load_criteria(TASK_DIR / "criteria.json")
    package = schema.TaskPackage(
        name="sum-integers",
        instruction=(TASK_DIR / "instruction.md").read_text(encoding="utf-8"),
        criteria=criteria,
        judging_context=(TASK_DIR / "judging_context.md").read_text(encoding="utf-8"),
        reference_answer=(TASK_DIR / "private_reference.txt").read_text(encoding="utf-8").strip(),
        reference_solution="reference_solution.py",
        assets=["assets/input.txt"],
    )
    errors = package.validate()
    print(f"schema validation: {'ok' if not errors else errors}")
    if errors:
        return 1

    gate1 = gates.structural_validate(TASK_DIR)
    print(f"gate 1 structural validation: {'pass' if gate1.passed else gate1.violations}")
    if not gate1.passed:
        return 1

    admission = gates.run_admission(real_grader, TASK_DIR / "reference_solution.py")
    print(
        f"gate 3 reference admission: admitted={admission.admitted} "
        f"reward={admission.reward} error={admission.error}"
    )
    if not admission.admitted:
        return 1

    history = [
        loop.IterationRecord(iteration=1, all_verdicts_pass=True, eval_complete=True, selection_reward=0.82),
        loop.IterationRecord(iteration=2, all_verdicts_pass=False, eval_complete=True, selection_reward=0.40),
        loop.IterationRecord(iteration=3, all_verdicts_pass=True, eval_complete=True, selection_reward=0.65),
    ]
    choice = loop.select_checkpoint(history)
    print(
        "checkpoint selection: iteration "
        f"{choice.iteration} ({choice.label}); iteration 2 scored lower but a "
        "review verdict failed, so it is not eligible"
    )

    verdicts = stub_verdicts("pass")
    print(f"review: all five criteria pass = {review.all_passed(verdicts)}")

    with tempfile.TemporaryDirectory() as tmp:
        bundle = loop.write_feedback_bundle(
            Path(tmp) / "feedback-iteration-3",
            {
                "validation_report.txt": f"reference reward: {admission.reward}\n",
                "verdicts.txt": "all five criteria: pass\n",
            },
        )
        index = (bundle / "index.json").read_text(encoding="utf-8").strip()
        print(f"feedback bundle written with index: {index}")

    print("done: the example task passed the gates and one loop turn completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
