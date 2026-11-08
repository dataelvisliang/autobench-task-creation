"""Grounding provenance and tree freezing (METHOD.md Sections 2.2 and 7).

Every grounding record carries an origin, a UTC retrieval time, a local
path, a SHA-256 hash, and license terms. Self-generated data additionally
retains the executable generator, its parameters and seed. Before a
session starts, the harness hashes every supplied source and snapshots
it read-only; freeze_tree and verify_tree implement that pair.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class ManifestRecord:
    """Provenance for one retained grounding source."""

    origin: str
    retrieved_utc: str  # ISO 8601, e.g. 2026-11-08T17:00:00Z
    local_path: str
    sha256: str
    license_terms: str
    # Self-generated data only:
    generator: str | None = None
    parameters: dict | None = None
    seed: int | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.origin.strip():
            errors.append("manifest record: origin is required")
        if not self.retrieved_utc.strip():
            errors.append(f"manifest record {self.local_path!r}: retrieval time is required")
        if len(self.sha256) != 64:
            errors.append(f"manifest record {self.local_path!r}: sha256 must be 64 hex chars")
        if not self.license_terms.strip():
            errors.append(f"manifest record {self.local_path!r}: license terms are required")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


def freeze_tree(root: str | Path) -> dict[str, str]:
    """Hash every regular file under root. Returns {relative_path: sha256}."""
    root = Path(root)
    frozen: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            frozen[path.relative_to(root).as_posix()] = sha256_file(path)
    return frozen


def verify_tree(root: str | Path, frozen: dict[str, str]) -> list[str]:
    """Compare a tree against a frozen snapshot. Returns mismatch descriptions."""
    root = Path(root)
    problems: list[str] = []
    current = freeze_tree(root)
    for rel, expected in frozen.items():
        if rel not in current:
            problems.append(f"missing file: {rel}")
        elif current[rel] != expected:
            problems.append(f"content changed: {rel}")
    for rel in current:
        if rel not in frozen:
            problems.append(f"unexpected file: {rel}")
    return problems


def write_manifest(records: list[ManifestRecord], path: str | Path) -> None:
    payload = [record.to_dict() for record in records]
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
