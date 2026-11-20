"""The indexed workflow and recorded status belonging to one pipeline."""
from copy import deepcopy

from .storage import Storage
from .cohort import Cohort
from daqr.config.tae_workflow import status as summarize_status
from daqr.config.tae_workflow import allocator_document
from daqr.config.tae_workflow import default_pipeline_status
from daqr.config.tae_workflow import initialize_pipeline_status


class Workflow(Storage):
    def __init__(self, pipeline_id, *, registry=None):
        super().__init__(pipeline_id, registry=registry)
        self._workflow_entry = deepcopy(self._resources['workflow_entry'])
        self._workflow_reference = deepcopy(self._resources['workflow_reference'])
        self._workflow_document = None
        self._cohorts = self._initialize_cohorts()
        self._cohort_index = {cohort.name: cohort for cohort in self._cohorts}

    def _initialize_cohorts(self):
        document = allocator_document(self.read_workflow()) if self._workflow_reference is not None else {}
        nodes = document.get('allocators', {})
        plan = document.get('plan') or {}
        definitions = document.get('objectDefinitions') or {}
        names = plan.get('cohorts', definitions.get('cohorts'))
        group = (((self._workflow_entry or {}).get('pipelineStatus') or {}).get('migration') or {}).get('group')
        if group is None:
            spectrum = (self._resources['record'].get('status') or {}).get('spectrum')
            group = 'Spectrum' if spectrum is True else 'nonSpectrum' if spectrum is False else None
        levels = {}
        if names is None:
            base = ['S1T', 'S1.5T', 'S2T', 'S1Tb', 'S1.5Tb', 'S2Tb']
            if group == 'nonSpectrum':
                names = base
            elif group == 'Spectrum':
                levels = {level + ':' + name: level
                    for level in default_pipeline_status(group)['templateProvenance']['levels'] for name in base}
                names = list(levels)
            else:
                names = list(dict.fromkeys(name for node in nodes.values() for name in node.get('cohorts', {})))
        if (not isinstance(names, list) or any(not isinstance(name, str) for name in names)
                or len(set(names)) != len(names)):
            raise ValueError('A unique recorded or registered cohort roster is required')
        for name in names:
            level, separator, _ = name.partition(':')
            if separator and level in ('m2', 'm3'):
                levels[name] = level
        allocator_names = plan['allocators'] if 'allocators' in plan else definitions.get('allocators', (
            ['Default', 'Random', 'Dynamic', 'ThompsonSampling'] if group in ('nonSpectrum', 'Spectrum') else None))
        configured_models = (self._resources['record'].get('settings') or {}).get('models')
        if (not isinstance(configured_models, (list, tuple))
                or any(not isinstance(name, str) for name in configured_models)):
            configured_models = definitions.get('models')
        model_names = plan['models'] if 'models' in plan else configured_models
        return tuple(Cohort(name, pipeline_id=self.pipeline_id, spectrum_level=levels.get(name),
            allocator_names=allocator_names, model_names=model_names,
            allocators={allocator: node['cohorts'][name] for allocator, node in nodes.items()
                if name in node.get('cohorts', {})}) for name in names)

    @property
    def cohorts(self):
        return self._cohorts

    def get_cohort(self, name):
        return self._cohort_index[name]

    def __iter__(self):
        return iter(self.cohorts)

    def __str__(self):
        return '[' + ', '.join(str(cohort) for cohort in self.cohorts) + ']'

    def __repr__(self):
        return type(self).__name__ + '(' + self.pipeline_key + ', cohorts=' + str(self) + ')'

    @property
    def workflow_reference(self):
        return deepcopy(self._workflow_reference)

    @property
    def workflow_version(self):
        return self._workflow_reference['commit'] if self._workflow_reference is not None else None

    @property
    def workflow_index_reference(self):
        return deepcopy(self._resources['workflow_index_reference'])

    @property
    def workflow_status_reference(self):
        return deepcopy(self._resources['workflow_status_reference'])

    @property
    def status(self):
        entry = self._workflow_entry or {}
        prior = entry.get('pipelineStatus') or {}
        group = (prior.get('migration') or {}).get('group')
        if group is None:
            spectrum = (self._resources['record'].get('status') or {}).get('spectrum')
            group = 'Spectrum' if spectrum is True else 'nonSpectrum' if spectrum is False else None
        if group in ('Spectrum', 'nonSpectrum'):
            return initialize_pipeline_status(group, prior)
        return deepcopy(entry['pipelineStatus'] if 'pipelineStatus' in entry else entry.get('table'))

    def read_workflow(self):
        if self._workflow_reference is None:
            raise LookupError('No workflow is registered for ' + self.pipeline_key)
        if self._workflow_document is None:
            document = self._registry.read_json(self._workflow_reference)
            if document.get('pipeline') != self.pipeline_key:
                raise ValueError('Saved workflow belongs to a different pipeline')
            self._workflow_document = document
        return deepcopy(self._workflow_document)

    @staticmethod
    def _component_snapshot(node, levels, plan):
        recorded = node.get('status')
        state = node.get('state')
        result = {}
        if levels:
            name = levels[0]
            children = {key: Workflow._component_snapshot(value, levels[1:], plan)
                for key, value in node.get(name, {}).items()}
            result[name] = children
            expected = ([str(position) for position in range(1, plan['runs'] + 1)]
                if name == 'experiments' and type(plan.get('runs')) is int else plan.get(name))
            if isinstance(expected, list):
                known = len(children) == len(expected) and set(children) == set(expected)
                values = [dict(state=child['state']) for child in children.values()]
                if known and all(child['state'] is not None for child in children.values()):
                    summary = summarize_status(values)
                else:
                    summary = dict(state=None, current=sum(child['state'] == 'done'
                        for child in children.values()), expected=len(expected), observed=False)
                if recorded is None:
                    recorded = summary
                if state is None:
                    state = summary['state']
        if state is None and isinstance(recorded, dict):
            state = recorded.get('state')
        if recorded is None and state is not None:
            recorded = dict(state=state)
        result.update(state=state, status=deepcopy(recorded))
        return result

    def get_workflow(self):
        return self

    def get_status(self):
        document = allocator_document(self.read_workflow())
        recorded = self.status
        state = recorded.get('status', recorded.get('state')) if isinstance(recorded, dict) else None
        return dict(pipeline_id=self.pipeline_id, pipeline=self.pipeline_key,
            version=self.workflow_version, source='pinned-git', live=False,
            state=state, status=recorded,
            stage_status=deepcopy(((self._workflow_entry or {}).get('table') or {}).get('stageStatus')),
            components=self._component_snapshot(document,
                ('allocators', 'cohorts', 'threats', 'experiments', 'models'), document.get('plan') or {}))
