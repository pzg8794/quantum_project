"""Allocator metadata and its own models inside one cohort."""
from copy import deepcopy
from types import MappingProxyType

from .model import Model
from .registry import normalize_pipeline_id, validate_component_name


# WE ALREADY HAVE AN ALLOCATOR OBJECT, WHAT IS THIS FOR???
class Allocator:
    def __init__(self, name, *, pipeline_id, cohort_name, info=None, model_names=None):
        self._name = validate_component_name(name)
        self._pipeline_id = normalize_pipeline_id(pipeline_id)
        self._cohort_name = validate_component_name(cohort_name)
        self._info = deepcopy(info or {})
        records = {}
        for threat, node in self._info.get('threats', {}).items():
            for position, experiment in node.get('experiments', {}).items():
                for model_name, value in experiment.get('models', {}).items():
                    records.setdefault(model_name, {}).setdefault(threat, {})[str(position)] = value
        declared_models = model_names if model_names is not None else (
            (self._info.get('settings') or {}).get('models') or [])
        if not isinstance(declared_models, (list, tuple)) or len(set(declared_models)) != len(declared_models):
            raise ValueError('A unique model name roster is required')
        names = list(dict.fromkeys([*declared_models, *records]))
        self._models = {model_name: Model(model_name, pipeline_id=pipeline_id,
            cohort_name=cohort_name, allocator_name=name, records=records.get(model_name))
            for model_name in names}

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
    def info(self):
        return deepcopy(self._info)

    @property
    def settings(self):
        return deepcopy(self._info.get('settings'))

    @property
    def models(self):
        return MappingProxyType(self._models)

    def get_model(self, name):
        return self._models[name]

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
