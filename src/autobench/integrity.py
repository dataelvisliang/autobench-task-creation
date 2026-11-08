"""Gate 2 support: the static leak detector (METHOD.md Section 2.4).

The revision-integrity judge applies a counterfactual test to every
material public change: would an independent author still make this
change from the construct, the grounding, or a genuine ambiguity alone?
Making an observed solver error less likely is not a justification.

This module implements the deterministic half of that gate. It flags
numbers and long n-grams that newly appear in solver-visible files and
also appear in the feedback the proposer could read. The flags are
advisory input to the judge, whose verdict stays binding and human or
model driven.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_WORD_RE = re.compile(r"[A-Za-z0-9']+")


@dataclass
class LeakFlag:
    kind: str  # "number" or "ngram"
    value: str
    file: str


def _ngrams(text: str, n: int) -> set[str]:
    words = _WORD_RE.findall(text.lower())
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _numbers(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(text))


def leak_flags(
    old_public: dict[str, str],
    new_public: dict[str, str],
    feedback: str,
    ngram_size: int = 8,
) -> list[LeakFlag]:
    """Flag feedback content that newly appears in solver-visible files.

    old_public and new_public map file names to their text content for
    the checkpoint and the current submission. Only content that is new
    relative to the checkpoint and present in the feedback is flagged.
    """
    feedback_numbers = _numbers(feedback)
    feedback_ngrams = _ngrams(feedback, ngram_size)
    flags: list[LeakFlag] = []

    for name, new_text in new_public.items():
        old_text = old_public.get(name, "")
        old_numbers = _numbers(old_text)
        old_ngrams = _ngrams(old_text, ngram_size)

        for number in sorted(_numbers(new_text) - old_numbers):
            if number in feedback_numbers:
                flags.append(LeakFlag(kind="number", value=number, file=name))
        for gram in sorted(_ngrams(new_text, ngram_size) - old_ngrams):
            if gram in feedback_ngrams:
                flags.append(LeakFlag(kind="ngram", value=gram, file=name))

    return flags
