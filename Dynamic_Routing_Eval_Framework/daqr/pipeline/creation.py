"""Explicit, recoverable pipeline registration using the existing Git/Drive stores."""
import base64
from copy import deepcopy
from dataclasses import dataclass, field, replace
import hashlib
import json
import math
import re
from uuid import UUID

from daqr.config.pipeline_backup_index import GitHubBackupIndexStore, encoded_index
from daqr.config.pipeline_storage import provision_pipeline_storage
from daqr.config.tae_workflow import WorkflowStore, TAEWorkflow, default_pipeline_status
from .options import PipelineOptions

ALLOCATORS = ('Default', 'Random', 'Dynamic', 'ThompsonSampling')
MODELS = ('Oracle', 'GNeuralUCB', 'EXPNeuralUCB', 'CPursuitNeuralUCB', 'iCPursuitNeuralUCB')
THREATS = ('none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive')
SCALES = (1, 1.5, 2)


@dataclass(frozen=True)
class PipelineSettings:
    name: str
    physics_model: str | None = None
    spectrum: bool = False
    runs: int = 3
    base_frames: int = 4000
    frame_step: int = 2000
    base_seed: int = 12345
    attack_intensity: float | None = None
    threats: tuple = THREATS
    allocators: tuple = ALLOCATORS
    models: tuple = MODELS
    scales: tuple = SCALES
    last_backup: bool = True
    overwrite: bool = False
    prepare_dataset: str | None = None
    shared_settings: dict = field(default_factory=dict)
    options: PipelineOptions = field(default_factory=PipelineOptions)

    def __post_init__(self):
        if self.physics_model is None:
            object.__setattr__(self, 'physics_model', 'layered_primary_spectrum' if self.spectrum else 'paper7')
        for name in ('name', 'physics_model'):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 200 or any(ord(char) < 32 for char in value):
                raise ValueError(name + ' must be a nonempty bounded label')
        if type(self.spectrum) is not bool:
            raise TypeError('spectrum must be Boolean')
        for name in ('last_backup', 'overwrite'):
            if type(getattr(self, name)) is not bool:
                raise TypeError(name + ' must be Boolean')
        for name, allowed in (('threats', THREATS), ('allocators', ALLOCATORS), ('models', MODELS), ('scales', SCALES)):
            selected = getattr(self, name)
            if (not isinstance(selected, (list, tuple)) or not selected
                    or len(selected) != len(set(selected))
                    or any(type(item) is bool or item not in allowed for item in selected)):
                raise ValueError('Explicit supported unique selection required: ' + name)
            object.__setattr__(self, name, tuple(selected))
        for name, minimum in (('runs', 1), ('base_frames', 1), ('frame_step', 0), ('base_seed', 0)):
            if type(getattr(self, name)) is not int or getattr(self, name) < minimum:
                raise ValueError(name + ' must be an integer in range')
        if self.runs > 10:
            raise ValueError('runs must be at most 10')
        if self.spectrum and 1.5 in self.scales and any((self.base_frames + self.frame_step * position) % 2 for position in range(self.runs)):
            raise ValueError('The full Spectrum matrix includes scale 1.5 and requires even frame horizons')
        if self.attack_intensity is not None and (type(self.attack_intensity) not in (int, float) or not math.isfinite(self.attack_intensity) or not 0 <= self.attack_intensity <= 1):
            raise ValueError('attack_intensity must be between zero and one')
        if not isinstance(self.options, PipelineOptions) or type(self.shared_settings) is not dict:
            raise TypeError('Explicit PipelineOptions and shared settings dictionary required')
        if self.prepare_dataset not in (None, 'cohorts_split', 'cohorts_combined'):
            raise ValueError('prepare_dataset must be cohorts_split or cohorts_combined')
        if self.prepare_dataset is not None:
            object.__setattr__(self, 'options', replace(self.options, prepare_data=True,
                prep_cohort_set=self.prepare_dataset == 'cohorts_split',
                prep_allocator_set=self.prepare_dataset == 'cohorts_combined'))
        encoded = json.dumps(self.shared_settings, allow_nan=False)
        if len(encoded.encode()) > 32768:
            raise ValueError('Shared settings exceed the metadata limit')
        def check(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if not isinstance(key, str) or re.search(r'password|credential|secret|token|private.?key', key, re.I):
                        raise ValueError('Credentials must not enter pipeline Git settings')
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(self.shared_settings)
        object.__setattr__(self, 'shared_settings', deepcopy(self.shared_settings))

    def to_dict(self):
        return dict(physics_model=self.physics_model, spectrum=self.spectrum,
            runs=self.runs, base_frames=self.base_frames, frame_step=self.frame_step,
            scales=list(self.scales), base_capacity=[False, True],
            topology_levels=[2, 3] if self.spectrum else [],
            base_seed=self.base_seed, attack_intensity=self.attack_intensity,
            threat_settings_source='native-threat-defaults' if self.attack_intensity is None else 'explicit',
            last_backup=self.last_backup, use_last_backup=self.last_backup, overwrite=self.overwrite,
            prepare_dataset=self.prepare_dataset,
            shared_settings=deepcopy(self.shared_settings), options=self.options.to_dict(),
            allocators=list(self.allocators), models=list(self.models), threats=list(self.threats))


def initial_workflow(number, settings):
    values = settings.to_dict()
    group = 'Spectrum' if settings.spectrum else 'nonSpectrum'
    defaults = default_pipeline_status(group)
    base = ['S' + format(scale, 'g') + replay for replay in ('T', 'Tb') for scale in settings.scales]
    cohorts = [level + ':' + name for level in defaults['templateProvenance']['levels'] for name in base] if settings.spectrum else base
    document = dict(pipeline='Pipeline_' + str(number), displayName=settings.name,
        plan=dict(allocators=values['allocators'], cohorts=cohorts,
            threats=values['threats'], models=values['models'], runs=settings.runs),
        settings=values, allocators={}, readiness=dict(fairnessComplete=False, preparedComplete=False))
    stages = {plural: dict(completed=0, expected=defaults[singular]['expected'])
        for singular, plural in (('allocator', 'allocators'), ('cohort', 'cohorts'),
                                ('experiment', 'experiments'), ('model', 'models'))}
    stages['allocators']['expected'] = len(settings.allocators)
    stages['cohorts']['expected'] = len(settings.allocators) * len(cohorts)
    stages['experiments']['expected'] = stages['cohorts']['expected'] * len(settings.threats)
    stages['models']['expected'] = stages['experiments']['expected'] * len(settings.models)
    stages['evaluators'] = {name: deepcopy(stages[name]) for name in ('allocators', 'experiments', 'models')}
    document['stageStatus'] = stages
    for allocator in values['allocators']:
        document['allocators'][allocator] = dict(cohorts={})
        for cohort in cohorts:
            label = cohort.split(':')[-1]
            replay_b = label.endswith('Tb')
            scale = float(label[1:-2] if replay_b else label[1:-1])
            document['allocators'][allocator]['cohorts'][cohort] = dict(
                settings=dict(scale=scale, base_capacity=replay_b, runs=settings.runs, models=values['models']),
                sharedSettings=deepcopy(values),
                threats={threat: dict(experiments={str(position): dict(state='none',
                    models={model: dict(state='none') for model in values['models']})
                    for position in range(1, settings.runs + 1)}) for threat in values['threats']})
    return document


class PipelineCreationStore(GitHubBackupIndexStore):
    def management(self):
        head = self.api('git/ref/heads/main')['object']['sha']
        tree = self.api('git/commits/' + head)['tree']['sha']
        entries = self.api('git/trees/' + tree)
        if entries.get('truncated'):
            raise ValueError('Complete pipeline registry tree required')
        entry = next(item for item in entries['tree'] if item['path'] == 'MANAGEMENT.md')
        text = base64.b64decode(self.api('git/blobs/' + entry['sha'])['content']).decode()
        match = re.search(r'<!-- CRISP-MANAGEMENT-RECORD -->\s*```json\s*(.*?)\s*```', text, re.S)
        if not match:
            raise ValueError('Existing canonical management index required')
        return head, tree, entries['tree'], text, match, json.loads(match.group(1))

    def save_record(self, snapshot, record, row):
        head, tree, _, text, match, management = snapshot
        rows = management['pipelines']
        existing = [value for value in rows if value['pipeline_id'] == record['pipeline_id']]
        if len(existing) > 1:
            raise ValueError('Duplicate pipeline identity in canonical index')
        if existing:
            current = self.read_record(self.snapshot(str(record['pipeline_id']), commit=head, read_indexes=False))
            record, row = merge_creation_transition(current, existing[0], record)
        path = 'Pipeline_' + str(record['pipeline_id']) + '/PIPELINE.md'
        content = '# ' + record['pipelineName'] + '\n\n<!-- CRISP-PIPELINE-RECORD -->\n```json\n' + encoded_index(record).decode() + '```\n'
        row = {**deepcopy(record), **deepcopy(row), 'path': path.rsplit('/', 1)[0],
            'creation': deepcopy(record['creation']),
            'record': dict(path=path, bytes=len(content.encode()), sha256=hashlib.sha256(content.encode()).hexdigest())}
        first_binding = bool(record.get('storage')) and (not existing or not existing[0].get('storage'))
        if existing:
            rows[rows.index(existing[0])] = row
        else:
            rows.append(row)
        text = text[:match.start(1)] + json.dumps(management, indent=2) + text[match.end(1):]
        changes = [dict(path=path, mode='100644', type='blob', content=content),
            dict(path='MANAGEMENT.md', mode='100644', type='blob', content=text)]
        if first_binding:
            changes.append(dict(path=path.rsplit('/', 1)[0] + '/backup_index.json',
                mode='100644', type='blob', content='{}\n'))
        new_tree = self.api('git/trees', dict(base_tree=tree, tree=changes))['sha']
        revision = self.api('git/commits', dict(message='Initialize ' + str(record['pipeline_id']),
            tree=new_tree, parents=[head]))['sha']
        self.api('git/refs/heads/main', dict(sha=revision, force=False), method='PATCH')
        observed = self.read_record(self.snapshot(str(record['pipeline_id']), commit=revision, read_indexes=False))
        if observed != record:
            raise RuntimeError('Pipeline registration readback differs')
        return revision

    def reserve(self, settings, request_id):
        snapshot = self.management()
        rows = snapshot[-1]['pipelines']
        fingerprint = hashlib.sha256(encoded_index(dict(name=settings.name, settings=settings.to_dict()))).hexdigest()
        matches = [row for row in rows if row.get('creationRequest') == request_id]
        if matches:
            if len(matches) != 1 or matches[0].get('settingsSha256') != fingerprint:
                raise ValueError('Creation request already belongs to different settings')
            row = matches[0]
            record = self.read_record(self.snapshot(str(row['pipeline_id']), read_indexes=False))
            if record.get('settings') != settings.to_dict() or record.get('creation', {}).get('requestId') != request_id:
                raise ValueError('Reserved record settings or request identity changed')
            return record, deepcopy(row)
        identities = [int(row['pipeline_id']) for row in rows]
        identities += [int(match.group(1)) for entry in snapshot[2]
            if (match := re.fullmatch(r'Pipeline_([1-9][0-9]*)', entry['path']))]
        number = max(identities, default=0) + 1
        row = dict(pipeline_id=number, creationRequest=request_id, settingsSha256=fingerprint)
        record = dict(schema='quantum-crisp-pipeline/v1', pipeline_id=number,
            pipelineName=settings.name, display_name=settings.name,
            modules=dict(DC=None, DP=None, DM=None), settings=settings.to_dict(),
            status=dict(spectrum=settings.spectrum, capture_complete=False,
                scientific_matrix_complete=False, prepared=False, fairness=False, execution_planned=False),
            source_refs=[], boundary='Registered configuration only; no experiment or preparation has executed',
            creation=dict(requestId=request_id, settingsSha256=fingerprint, state='reserved'))
        self.save_record(snapshot, record, row)
        return record, row


def merge_creation_transition(current, row, candidate):
    incoming, previous = candidate['creation'], current.get('creation', {})
    if (current['pipeline_id'] != candidate['pipeline_id'] or current.get('settings') != candidate.get('settings')
            or any(previous.get(key) != incoming.get(key) for key in ('requestId', 'settingsSha256'))):
        raise ValueError('Creation identity or settings changed; preserve the current record')
    binding = candidate.get('storage')
    if current.get('storage') is not None and binding is not None and binding != current['storage']:
        raise ValueError('Pipeline Drive binding changed; preserve the current record')
    result = deepcopy(current)
    ranks = {'reserved': 0, 'drive-bound': 1, 'registered': 2}
    if previous.get('state') not in ranks or incoming.get('state') not in ranks:
        raise ValueError('Known pipeline initialization state required')
    if ranks[incoming['state']] >= ranks[previous['state']]:
        result['creation']['state'] = incoming['state']
    if result.get('storage') is None and binding is not None:
        result['storage'] = deepcopy(binding)
    if candidate.get('temporaryStaging') is not None:
        if current.get('temporaryStaging', candidate['temporaryStaging']) != candidate['temporaryStaging']:
            raise ValueError('Temporary staging binding changed')
        result['temporaryStaging'] = deepcopy(candidate['temporaryStaging'])
    updated_row = deepcopy(row)
    if result.get('storage'):
        updated_row['storage'] = deepcopy(result['storage'])
    return result, updated_row


class PipelineCreator:
    def __init__(self, *, drive_service, pipeline_store=None, workflow_store=None, temporary_staging=None):
        self.drive = drive_service
        self.pipelines = pipeline_store if pipeline_store is not None else PipelineCreationStore()
        self.workflows = workflow_store if workflow_store is not None else WorkflowStore()
        self.temporary_staging = temporary_staging

    def create(self, settings, request_id):
        if not isinstance(settings, PipelineSettings):
            raise TypeError('PipelineSettings is required')
        if not isinstance(request_id, str) or str(UUID(request_id)) != request_id:
            raise ValueError('A stable canonical request UUID is required for safe retry')
        record, row = self.pipelines.reserve(settings, request_id)
        number = record['pipeline_id']
        if record.get('creation', {}).get('state') == 'registered':
            return number
        if self.temporary_staging is not None and not record.get('storage'):
            staging = dict(driveId=self.temporary_staging, folder=f'Pipeline_{number}')
            if record.get('temporaryStaging', staging) != staging:
                raise ValueError('Temporary staging binding changed')
            record['temporaryStaging'] = staging
        else:
            binding = provision_pipeline_storage(self.drive, number, record.get('storage'))
            record['storage'] = binding
            record['creation']['state'] = 'drive-bound'
            row['storage'] = binding
        self.pipelines.save_record(self.pipelines.management(), record, row)
        key = 'Pipeline_' + str(number)
        head, index, existing = self.workflows.load(key)
        if key not in index:
            document = initial_workflow(number, settings)
            tracker = TAEWorkflow(key, store=self.workflows, defer_git=True)
            tracker.document = document
            self.workflows.publish(head, index, document, tracker.files())
            _, observed_index, observed = self.workflows.load(key)
            if key not in observed_index or observed != document:
                raise RuntimeError('Workflow publication readback differs; retry the same request')
        else:
            if existing.get('settings') != settings.to_dict():
                raise ValueError('Reserved pipeline workflow settings differ; existing work preserved')
        record['creation']['state'] = 'registered'
        self.pipelines.save_record(self.pipelines.management(), record, row)
        return number
