"""Submission gates (METHOD.md Sections 2.3 and 2.5).

Gate 1, structural validation: the frozen tree is checked without being
executed. Protected content must be byte-identical to the harness
template, package size limits apply, and only regular files are allowed.

Gate 3, reference-solution admission: the proposer's own reference
solution is graded by the real grader. Admission requires no grader
error and a reward of at least 0.9.

Gate 2 (revision integrity) lives in integrity.py.

NOP check (scaffold-only, not in the paper): an empty submission is
graded by the real grader and must score 0. A non-zero reward means
the grader awards points for doing nothing, so the task fails even
though it passed the three paper gates.
"""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .manifest import sha256_file

ADMISSION_THRESHOLD = 0.9
MAX_SUBMISSION_ATTEMPTS = 10

# Files whose executable bit is legitimate inside a task package.
ALLOWED_EXECUTABLES = {"reference_solution.py", "reference_solution.sh", "run_verifier.sh"}


@dataclass
class PackageLimits:
    max_files: int = 1024
    max_total_bytes: int = 2 * 1024**3  # 2 GiB
    max_file_bytes: int = 256 * 1024**2  # 256 MiB
    max_path_bytes: int = 240


@dataclass
class GateResult:
    passed: bool
    violations: list[str] = field(default_factory=list)


def structural_validate(
    task_dir: str | Path,
    protected_hashes: dict[str, str] | None = None,
    limits: PackageLimits | None = None,
) -> GateResult:
    """Validate a frozen task tree without executing any of it.

    protected_hashes maps relative paths of harness-owned files to the
    SHA-256 they must match byte for byte (verifier launcher, judge
    prompt template, and similar fixed wiring).
    """
    limits = limits or PackageLimits()
    root = Path(task_dir)
    violations: list[str] = []
    protected_hashes = protected_hashes or {}

    files: list[Path] = []
    total_bytes = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for dirname in dirnames:
            entry = Path(dirpath) / dirname
            if entry.is_symlink():
                violations.append(f"symlink not allowed: {entry.relative_to(root).as_posix()}")
        for filename in filenames:
            path = Path(dirpath) / filename
            rel = path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_file():
                violations.append(f"non-regular file not allowed: {rel}")
                continue
            if len(rel.encode("utf-8")) > limits.max_path_bytes:
                violations.append(f"path too long ({limits.max_path_bytes} bytes max): {rel}")
            size = path.stat().st_size
            total_bytes += size
            if size > limits.max_file_bytes:
                violations.append(f"file too large ({limits.max_file_bytes} bytes max): {rel}")
            mode = path.stat().st_mode
            if mode & stat.S_IXUSR and path.name not in ALLOWED_EXECUTABLES:
                violations.append(f"executable bit not allowed on: {rel}")
            files.append(path)

    if len(files) > limits.max_files:
        violations.append(f"too many files: {len(files)} > {limits.max_files}")
    if total_bytes > limits.max_total_bytes:
        violations.append(f"package too large: {total_bytes} > {limits.max_total_bytes} bytes")

    for rel, expected in protected_hashes.items():
        target = root / rel
        if not target.is_file():
            violations.append(f"protected file missing: {rel}")
        elif sha256_file(target) != expected:
            violations.append(f"protected file modified: {rel}")

    return GateResult(passed=not violations, violations=violations)


@dataclass
class AdmissionResult:
    admitted: bool
    reward: float | None
    error: str | None


def admit_reference(reward: float | None, error: str | None) -> AdmissionResult:
    """Decide admission from a finished reference-solution grading run."""
    if error is not None:
        return AdmissionResult(admitted=False, reward=reward, error=error)
    if reward is None:
        return AdmissionResult(admitted=False, reward=None, error="no reward produced")
    if reward < ADMISSION_THRESHOLD:
        return AdmissionResult(
            admitted=False,
            reward=reward,
            error=f"reference reward {reward} below threshold {ADMISSION_THRESHOLD}",
        )
    return AdmissionResult(admitted=True, reward=reward, error=None)


def run_admission(grader, solution_path: str | Path) -> AdmissionResult:
    """Run a grader callable on the reference solution and apply the rule.

    grader(solution_path) must return a float reward in [0, 1]. Any
    exception it raises counts as a grader error and blocks admission.
    """
    try:
        reward = grader(solution_path)
    except Exception as exc:  # a verifier error blocks admission by design
        return AdmissionResult(admitted=False, reward=None, error=f"verifier error: {exc}")
    return admit_reference(reward, None)


# An empty submission must earn nothing. The paper does not use a NOP
# check (full-text search of arXiv:2610.38882 finds "NOP" zero times),
# so this is a scaffold-only addition, not a paper gate.
NOP_REWARD_LIMIT = 0.0


@dataclass
class NopResult:
    passed: bool
    reward: float | None
    error: str | None


def check_nop_reward(reward: float | None, error: str | None) -> NopResult:
    """Decide the NOP check from a finished empty-submission grading run."""
    if error is not None:
        return NopResult(passed=False, reward=reward, error=error)
    if reward is None:
        return NopResult(passed=False, reward=None, error="no reward produced")
    if reward > NOP_REWARD_LIMIT:
        return NopResult(
            passed=False,
            reward=reward,
            error=(
                f"empty submission scored {reward}, expected "
                f"{NOP_REWARD_LIMIT}: grader awards points for doing nothing"
            ),
        )
    return NopResult(passed=True, reward=reward, error=None)


def run_nop_check(grader) -> NopResult:
    """Grade an empty submission with the real grader and apply the rule.

    grader(path) must return a float reward in [0, 1] for the file at
    path. The empty file is written to a temporary directory so the
    check never touches a real task package. A grader error on the empty
    submission fails the check: the grader must handle doing nothing
    without crashing, as well as without awarding points.
    """
    with tempfile.TemporaryDirectory(prefix="autobench-nop-") as tmp:
        empty = Path(tmp) / "empty_submission.py"
        empty.write_text("", encoding="utf-8")
        try:
            reward = grader(empty)
        except Exception as exc:  # noqa: BLE001 - a grader error fails the check
            return NopResult(
                passed=False,
                reward=None,
                error=f"grader error on empty submission: {exc}",
            )
        return check_nop_reward(reward, None)
