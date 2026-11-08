"""Tests for the AutoBenchmark scaffold. Run: PYTHONPATH=src python -m pytest"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from autobench import gates, integrity, loop, manifest, review, schema, spec  # noqa: E402


# ---------- schema ----------


def test_valid_binary_criterion():
    criterion = schema.Criterion(id="c1", kind="binary", weight=1.0)
    assert criterion.validate() == []


def test_likert_needs_two_points():
    criterion = schema.Criterion(id="c1", kind="likert", weight=1.0, points=1)
    assert any("two points" in e for e in criterion.validate())


def test_numeric_needs_range():
    criterion = schema.Criterion(id="c1", kind="numeric", weight=1.0)
    assert any("explicit range" in e for e in criterion.validate())


def test_weight_must_be_positive():
    criterion = schema.Criterion(id="c1", kind="binary", weight=0)
    assert any("positive" in e for e in criterion.validate())


def test_prohibited_criterion_keys_rejected():
    with pytest.raises(ValueError, match="prohibited"):
        schema.Criterion.from_dict(
            {"id": "c1", "kind": "binary", "weight": 1.0, "regex": "^ok$"}
        )


def test_duplicate_criterion_ids_rejected():
    package = schema.TaskPackage(
        name="t",
        instruction="do it",
        criteria=[
            schema.Criterion(id="dup", kind="binary", weight=1.0),
            schema.Criterion(id="dup", kind="binary", weight=1.0),
        ],
    )
    assert any("duplicate" in e for e in package.validate())


# ---------- manifest ----------


def test_freeze_and_verify_tree(tmp_path):
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    frozen = manifest.freeze_tree(tmp_path)
    assert manifest.verify_tree(tmp_path, frozen) == []
    (tmp_path / "a.txt").write_text("tampered", encoding="utf-8")
    problems = manifest.verify_tree(tmp_path, frozen)
    assert any("content changed" in p for p in problems)


def test_manifest_record_requires_license():
    record = manifest.ManifestRecord(
        origin="https://example.org/source",
        retrieved_utc="2026-11-08T17:00:00Z",
        local_path="grounding/source.txt",
        sha256="a" * 64,
        license_terms="",
    )
    assert any("license" in e for e in record.validate())


# ---------- gates ----------


def test_gate1_clean_tree_passes(tmp_path):
    (tmp_path / "instruction.md").write_text("task", encoding="utf-8")
    result = gates.structural_validate(tmp_path)
    assert result.passed, result.violations


def test_gate1_file_count_limit(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x", encoding="utf-8")
    result = gates.structural_validate(tmp_path, limits=gates.PackageLimits(max_files=3))
    assert not result.passed
    assert any("too many files" in v for v in result.violations)


def test_gate1_protected_file_must_match(tmp_path):
    protected = tmp_path / "verifier" / "run_verifier.sh"
    protected.parent.mkdir()
    protected.write_text("original", encoding="utf-8")
    expected = manifest.sha256_file(protected)
    assert gates.structural_validate(tmp_path, {"verifier/run_verifier.sh": expected}).passed
    protected.write_text("tampered", encoding="utf-8")
    result = gates.structural_validate(tmp_path, {"verifier/run_verifier.sh": expected})
    assert not result.passed
    assert any("protected file modified" in v for v in result.violations)


def test_gate1_rejects_symlink(tmp_path):
    (tmp_path / "real.txt").write_text("x", encoding="utf-8")
    os.symlink(tmp_path / "real.txt", tmp_path / "link.txt")
    result = gates.structural_validate(tmp_path)
    assert not result.passed
    assert any("symlink" in v or "non-regular" in v for v in result.violations)


def test_admission_threshold():
    assert gates.admit_reference(0.9, None).admitted
    assert not gates.admit_reference(0.89, None).admitted
    assert not gates.admit_reference(1.0, "verifier crashed").admitted


def test_run_admission_grader_error_blocks():
    def bad_grader(_path):
        raise RuntimeError("boom")

    result = gates.run_admission(bad_grader, "whatever")
    assert not result.admitted
    assert "verifier error" in (result.error or "")


# ---------- integrity ----------


def test_leak_detector_flags_planted_number_and_ngram():
    old = {"instruction.md": "Fix the training run so the metric improves."}
    feedback = (
        "The solver failed because the target value 0.8731 was hidden and "
        "the quick brown fox jumps over the lazy dog again today."
    )
    new = {
        "instruction.md": (
            "Fix the training run so the metric improves. Hint: 0.8731 matters. "
            "Remember the quick brown fox jumps over the lazy dog again today."
        )
    }
    flags = integrity.leak_flags(old, new, feedback)
    kinds = {(f.kind, f.value) for f in flags}
    assert ("number", "0.8731") in kinds
    assert any(kind == "ngram" for kind, _ in kinds)


def test_leak_detector_ignores_preexisting_content():
    text = "The value 42 was always here in the public file."
    flags = integrity.leak_flags({"a.md": text}, {"a.md": text}, "feedback mentions 42 too")
    assert flags == []


# ---------- review ----------


def _verdict(**overrides):
    base = dict(
        criterion="correctness",
        decision="pass",
        responsibility="submission",
        citations=["a", "b", "c"],
        strengths=["clear grounding"],
        weaknesses=["small scale"],
        required_fixes=[],
        confidence=0.8,
        rationale="checked against the bundle",
    )
    base.update(overrides)
    return review.Verdict(**base)


def test_verdict_valid():
    assert _verdict().validate() == []


def test_verdict_needs_three_citations():
    assert any("three artifact citations" in e for e in _verdict(citations=["a"]).validate())


def test_fail_verdict_needs_required_fixes():
    errors = _verdict(decision="fail", required_fixes=[]).validate()
    assert any("required fixes" in e for e in errors)


def test_all_passed_requires_all_five():
    verdicts = {name: _verdict(criterion=name) for name in review.CRITERIA}
    assert review.all_passed(verdicts)
    verdicts["overall"] = _verdict(criterion="overall", decision="fail", required_fixes=["fix"])
    assert not review.all_passed(verdicts)


# ---------- loop ----------


def _record(iteration, passed, complete, reward):
    return loop.IterationRecord(
        iteration=iteration,
        all_verdicts_pass=passed,
        eval_complete=complete,
        selection_reward=reward,
    )


def test_checkpoint_picks_lowest_eligible_reward():
    history = [_record(1, True, True, 0.8), _record(2, True, True, 0.5), _record(3, False, True, 0.2)]
    choice = loop.select_checkpoint(history)
    assert (choice.iteration, choice.label) == (2, "selected")


def test_checkpoint_tie_breaks_toward_later():
    history = [_record(1, True, True, 0.5), _record(2, True, True, 0.5)]
    assert loop.select_checkpoint(history).iteration == 2


def test_checkpoint_fallback_is_repair():
    history = [_record(1, False, True, 0.3), _record(2, False, False, 0.1)]
    choice = loop.select_checkpoint(history)
    assert (choice.iteration, choice.label) == (1, "repair_fallback")


def test_feedback_bundle_blocks_secrets(tmp_path):
    with pytest.raises(ValueError, match="secret scan"):
        loop.write_feedback_bundle(tmp_path / "b", {"notes.txt": "api_key = hunter2hunter2"})


def test_feedback_bundle_writes_index(tmp_path):
    out = loop.write_feedback_bundle(tmp_path / "b", {"report.txt": "clean"})
    assert (out / "index.json").is_file()
    assert (out / "report.txt").read_text(encoding="utf-8") == "clean"


# ---------- spec ----------


def test_spec_settings_validation():
    assert spec.TaskSpec(rules="general rules").validate() == []
    coarse = spec.TaskSpec(rules="r", setting=spec.HumanSetting.COARSE, direction="Measure X.")
    assert coarse.validate() == []
    fine = spec.TaskSpec(rules="r", setting=spec.HumanSetting.FINE, direction="detailed")
    assert any("grounding" in e for e in fine.validate())
