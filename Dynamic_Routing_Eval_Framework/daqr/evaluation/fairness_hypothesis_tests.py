from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Any


@dataclass(frozen=True)
class PermutationTestResult:
    metric: str
    observed_gap: float | None
    p_value: float | None
    permutation_count: int
    group_a: str | None
    group_b: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FairnessHypothesisTester:
    """Governed permutation-style hypothesis testing for group mean gaps."""

    def __init__(self, *, permutation_count: int = 500, random_seed: int = 12345) -> None:
        self.permutation_count = permutation_count
        self.random_seed = random_seed

    def test_group_gap(
        self,
        metric: str,
        values_by_group: dict[str, list[float]],
    ) -> PermutationTestResult:
        valid_groups = {group: values for group, values in values_by_group.items() if values}
        if len(valid_groups) < 2:
            return PermutationTestResult(
                metric=metric,
                observed_gap=None,
                p_value=None,
                permutation_count=self.permutation_count,
                group_a=None,
                group_b=None,
            )

        ordered = sorted(valid_groups.items(), key=lambda item: sum(item[1]) / len(item[1]))
        group_a, values_a = ordered[0]
        group_b, values_b = ordered[-1]
        observed_gap = abs((sum(values_b) / len(values_b)) - (sum(values_a) / len(values_a)))

        combined = list(values_a) + list(values_b)
        size_a = len(values_a)
        exceed_count = 0
        rng = random.Random(self.random_seed)

        for _ in range(self.permutation_count):
            shuffled = combined[:]
            rng.shuffle(shuffled)
            perm_a = shuffled[:size_a]
            perm_b = shuffled[size_a:]
            perm_gap = abs((sum(perm_b) / len(perm_b)) - (sum(perm_a) / len(perm_a)))
            if perm_gap >= observed_gap:
                exceed_count += 1

        p_value = (exceed_count + 1) / (self.permutation_count + 1)
        return PermutationTestResult(
            metric=metric,
            observed_gap=observed_gap,
            p_value=p_value,
            permutation_count=self.permutation_count,
            group_a=group_a,
            group_b=group_b,
        )
