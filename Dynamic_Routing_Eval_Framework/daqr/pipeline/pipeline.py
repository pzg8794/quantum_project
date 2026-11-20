"""One pipeline identity with inherited workflow and storage capabilities."""
from copy import deepcopy
from collections.abc import Mapping

from .options import PipelineOptions
from .workflow import Workflow
from .registry import PipelineRegistry, normalize_pipeline_id


class Pipeline(Workflow):
    def prepare_adoption(self, target_runs, own_tracker_ref):
        from .adoption import prepare_adoption
        return prepare_adoption(self.pipeline_record, self.read_workflow(),
            self._workflow_entry, target_runs, own_tracker_ref)

    @property
    def target_runs(self):
        return (self.pipeline_record.get('infrastructure') or {}).get('targetRuns')

    @property
    def infrastructure(self):
        return deepcopy(self._resources['record'].get('infrastructure') or {})

    @classmethod
    def create(cls, settings, *, drive_service, request_id, creator=None):
        from .creation import PipelineCreator
        creator = creator if creator is not None else PipelineCreator(drive_service=drive_service)
        number = creator.create(settings, request_id)
        registry = PipelineRegistry(pipeline_store=creator.pipelines, workflow_store=creator.workflows)
        return cls(number, registry=registry, options=settings.options)

    @classmethod
    def list_pipelines(cls, pipeline_ids=None, *, registry=None, options=None):
        registry = registry if registry is not None else PipelineRegistry()
        identities = registry.pipeline_ids() if pipeline_ids is None else [
            normalize_pipeline_id(value) for value in pipeline_ids]
        if len(set(identities)) != len(identities):
            raise ValueError('A pipeline list must have unique IDs')
        return [cls(identity, registry=registry, options=options) for identity in identities]

    def __init__(self, pipeline_id, *, registry=None, options=None):
        """Attach requests without execution or changing saved settings.

        Explicit PipelineOptions override settings['options']; otherwise that
        mapping supplies defaults. Absent saved options mean all False. Other
        settings and recorded modules/status never imply option values.
        """
        if options is not None and not isinstance(options, PipelineOptions):
            raise TypeError('options must be PipelineOptions or None')
        super().__init__(pipeline_id, registry=registry)
        record = self._resources['record']
        self.name = record.get('pipelineName') or self.pipeline_key
        self.display_name = record.get('display_name') or self.name
        self._settings = deepcopy(record.get('settings') or {})
        if options is None:
            saved_options = self._settings.get('options', {})
            if not isinstance(saved_options, Mapping):
                raise TypeError("settings['options'] must be a mapping")
            options = PipelineOptions(**saved_options)
        self.options = options
        self._features = deepcopy(record.get('modules') or {})
        self._runner_reference = deepcopy(self._resources['runner_reference'])
        self.runner_execution_id = self._resources['runner_execution_id']

    @property
    def pipeline_record(self):
        return deepcopy(self._resources['record'])

    @property
    def settings(self):
        return deepcopy(self._settings)

    @property
    def features(self):
        return deepcopy(self._features)

    @property
    def runner_reference(self):
        return deepcopy(self._runner_reference)

    def describe(self):
        return dict(pipeline_id=self.pipeline_id, pipeline_key=self.pipeline_key,
            target_runs=self.target_runs, infrastructure=self.infrastructure,
            name=self.name, display_name=self.display_name, settings=self.settings,
            features=self.features, options=self.options.to_dict(), pipeline_reference=self.pipeline_reference,
            storage=self.storage_binding, workflow_reference=self.workflow_reference,
            runner_reference=self.runner_reference, runner_execution_id=self.runner_execution_id)
