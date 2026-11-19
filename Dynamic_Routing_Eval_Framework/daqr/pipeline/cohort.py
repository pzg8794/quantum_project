"""A named cohort in one pipeline's workflow structure."""
from copy import deepcopy

from .registry import normalize_pipeline_id, validate_component_name
from .allocator import Allocator
from types import MappingProxyType


class Cohort:
    def __init__(self, name, *, pipeline_id, allocators=None, spectrum_level=None,
                 allocator_names=None, model_names=None):
        self._name = validate_component_name(name)
        self._pipeline_id = normalize_pipeline_id(pipeline_id)
        records = deepcopy(allocators or {})

        # THIS IS BAD, A PIPELINE COHORT SHOULD ONLY HAVE ONE ALLOCATOR.
        if allocator_names is not None and (not isinstance(allocator_names, (list, tuple))
                or len(set(allocator_names)) != len(allocator_names)):
            raise ValueError('A unique allocator name roster is required')
        
        names = list(dict.fromkeys([*(allocator_names or []), *records]))
        self._allocators = {allocator_name: Allocator(allocator_name, pipeline_id=self.pipeline_id,
            cohort_name=name, info=records.get(allocator_name), model_names=model_names)
            for allocator_name in names}
        self._spectrum_level = spectrum_level

    @property
    def name(self):
        return self._name

    @property
    def pipeline_id(self):
        return self._pipeline_id

    # THIS IS WRONG, A PIPELINE COHORT ONLY HAS ONE ALLOCATOR. DID YOU MEAN THREATS OR ATTACKS????
    @property
    def allocators(self):
        return MappingProxyType(self._allocators)

    @property
    def models(self):
        return MappingProxyType({name: allocator.models for name, allocator in self._allocators.items()})

    def get_allocator(self, name):
        return self._allocators[name]

    @property
    def spectrum_level(self):
        return self._spectrum_level

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
