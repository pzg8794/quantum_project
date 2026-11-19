"""Validated run requests only; these options do not execute pipeline stages."""
from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True)
class PipelineOptions:
    """Opt-in requests, independent of recorded execution or completion state.

    Preparation subflags strictly require prepare_data=True; they are never
    silently disabled. prep_cohort_set requests cohort datasets, while
    prep_allocator_set requests merging all cohort datasets for each allocator.
    Neither flag implies the other. All defaults are False.
    """

    fairness: bool = False
    prepare_data: bool = False
    prep_cohort_set: bool = False
    prep_allocator_set: bool = False

    def __post_init__(self):
        for field in fields(self):
            if type(getattr(self, field.name)) is not bool:
                raise TypeError(field.name + ' must be an exact bool')
        if not self.prepare_data and (self.prep_cohort_set or self.prep_allocator_set):
            raise ValueError('prep_cohort_set and prep_allocator_set require prepare_data=True')

    def to_dict(self):
        """Return a detached JSON-compatible settings value, not an execution receipt."""
        return asdict(self)
