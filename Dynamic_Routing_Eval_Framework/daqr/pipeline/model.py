"""Model metadata owned by one cohort and allocator, without model execution."""
from copy import deepcopy
from .registry import normalize_pipeline_id, validate_component_name


# WHAT IS THIS FOR??? I AM SO CONFUSED.
class Model:
    def __init__(self, name, *, pipeline_id, cohort_name, allocator_name, records=None):
        self._name = validate_component_name(name)
        self._pipeline_id = normalize_pipeline_id(pipeline_id)
        self._cohort_name = validate_component_name(cohort_name)
        self._allocator_name = validate_component_name(allocator_name)
        self._records = deepcopy(records or {})

    @property
    def name(self):
        return self._name

    @property
    def pipeline_id(self):
        return self._pipeline_id

    @property
    def cohort_name(self):
        return self._cohort_name

    @property
    def allocator_name(self):
        return self._allocator_name

    @property
    def records(self):
        return deepcopy(self._records)

    def get_status(self, threat, position):
        return deepcopy(self._records[threat][str(position)])

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
