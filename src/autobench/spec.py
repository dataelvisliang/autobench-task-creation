"""Task specification and human feedback settings (METHOD.md Section 6).

The proposer receives a task spec: a file with the general rules of the
task and, depending on the setting, human direction. The paper varies
what the human supplies across four settings, from fully autonomous to
fine-grained direction both before and during the loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HumanSetting(Enum):
    NONE = "none"  # (i) fully autonomous, rules only
    COARSE = "coarse"  # (ii) one-sentence intent at proposal
    FINE = "fine"  # (iii) detailed spec + curated grounding at proposal
    FINE_EXECUTION = "fine_execution"  # (iv) fine, plus guidance during the loop


@dataclass
class TaskSpec:
    rules: str  # the general rules every setting receives
    setting: HumanSetting = HumanSetting.NONE
    direction: str | None = None  # human direction text, settings (ii) to (iv)
    grounding_dir: str | None = None  # curated grounding, settings (iii) and (iv)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.rules.strip():
            errors.append("task spec: general rules are required in every setting")
        if self.setting is HumanSetting.COARSE:
            if not self.direction or not self.direction.strip():
                errors.append("coarse setting: a one-sentence statement of intent is required")
            elif "\n" in self.direction.strip():
                errors.append("coarse setting: direction must be a single sentence in one line")
        if self.setting in (HumanSetting.FINE, HumanSetting.FINE_EXECUTION):
            if not self.direction or not self.direction.strip():
                errors.append("fine setting: a detailed task specification is required")
            if not self.grounding_dir:
                errors.append("fine setting: a curated grounding directory is required")
        if self.setting is HumanSetting.NONE and self.direction:
            errors.append("no-feedback setting: direction must be empty")
        return errors
