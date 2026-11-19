"""Pipeline 152's original seven-run completion sources; no evaluator resume."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .completion_notebook import SavedPipelineNotebook, THREATS, ALLOCATORS
from .migration import PipelineArtifactMover
from .pipeline import Pipeline
from .recovery import recover_completion


PROFILE = json.loads(Path(__file__).with_name('pipeline152_sources.json').read_bytes())
QUEUE_REFS = tuple(dict(repository=PROFILE['repository'], commit=PROFILE['commit'],
    path='queues/' + name + '.json', sha256=digest) for name, digest in PROFILE['queues'].items())


def seven_run_scopes(queues, review):
    groups = {}
    expected = {allocator + ':' + capacity + ':' + scale for allocator in ALLOCATORS
        for capacity in ('T', 'Tb') for scale in ('1', '1.5', '2')}
    for queue in queues:
        if str(queue.get('pipelineId')) != '152' or queue.get('testOnly') is True:
            raise ValueError('Only Pipeline 152 production completion queues are accepted')
        for name, group in queue['sets'].items():
            if name not in expected or set(group['attacks']) != set(THREATS):
                raise ValueError('Foreign subset or threat scope')
            if not all(attack.get('state') == 'done' and attack.get('context', {}).get('run') == 7
                    for attack in group['attacks'].values()):
                raise ValueError('Do not replay unfinished or stale queue entries as completed work')
            if name in groups and groups[name]['finalizationRefs'] != group['finalizationRefs']:
                raise ValueError('Conflicting original-settings completion sources')
            groups[name] = deepcopy(group)
    prefix = review['verifiedSevenPrefixes']
    if prefix.get('schema') != 'native-seven-prefix-review/v1':
        raise ValueError('Original seven-run prefix review required')
    for admitted in prefix['admitted']:
        name = admitted['setId']
        if (name not in expected or name in groups or admitted.get('prefixVerified') is not True
                or admitted.get('targetContexts') != 5 or admitted.get('targetModels') != 25):
            raise ValueError('Ambiguous or incomplete original seven-run admission')
        groups[name] = dict(finalizationRefs=dict(evaluation=deepcopy(admitted['evaluationRef'])),
            sourceCompletionProof=dict(review=PROFILE['prefixReview'], admitted=deepcopy(admitted)),
            attacks={threat: dict(state='done', origin='verified-existing-seven-prefix',
                context=dict(run=7), driveRefs=[deepcopy(admitted['evaluationRef'])]) for threat in THREATS})
    if set(groups) != expected:
        raise ValueError('All 24 subsets need their own original seven-run evidence; never guess missing settings')
    return groups


class SevenRunPipelineNotebook(SavedPipelineNotebook):
    pipeline_number = 152
    target_runs = 7
    predecessor_pipeline_number = 6
    original_directory_prefix = 'seven-original-'
    queue_refs = (*QUEUE_REFS, PROFILE['prefixReview'])

    def __init__(self, *args, **kwargs):
        self.byte_cache = {}
        self.predecessor = None
        self.predecessor_document = None
        self.predecessor_drive_id = None
        super().__init__(*args, **kwargs)
        if self.pipeline._migration_manifest is None:
            reference = self.pipeline.pipeline_record.get('storageMigration', {}).get('manifestRef')
            self.pipeline._migration_manifest = (self.pipeline._registry.read_json(reference) if reference else
                dict(pipelineId=str(self.pipeline_number), driveId=self.pipeline.drive_id, files={}))
        self.pipeline._migration_manifest['files'].update(self.tracker.document.get('artifactMoves', {}))

    def load_groups(self):
        return seven_run_scopes(self.queues[:-1], self.queues[-1])

    def validate(self, binding, set_id):
        super().validate(binding, set_id)
        config = binding['recovered_config']
        settings = self.pipeline.settings
        if any(name in settings and config[field] != settings[name]
                for name, field in (('startFrames', 'base_frames'), ('stepFrames', 'frame_step'))):
            raise ValueError('Saved frame settings differ from the registered pipeline')
        if config['models'] != self.tracker.document['objectDefinitions']['models']:
            raise ValueError('Original model roster differs from the registered pipeline')
        return binding

    def locate_original(self, reference):
        manifest = self.pipeline._migration_manifest
        identity = reference['provider_id']
        if identity in manifest['files']:
            return self.pipeline.resolve_artifact_reference(reference)
        if reference.get('drive_root_id') == self.pipeline.drive_id:
            return deepcopy(reference)
        if self.move_service is None:
            from daqr.config.gd_backup_manager import GoogleDriveBackupManager
            self.move_service = GoogleDriveBackupManager.pipeline_creation_drive_service()
        if not hasattr(self, 'artifact_mover'):
            self.artifact_mover = PipelineArtifactMover(self.move_service, self.pipeline.storage_binding)
        mover = self.artifact_mover
        metadata = mover.read(identity)
        if self.predecessor_drive_id is None:
            self.predecessor_drive_id = self.pipeline._registry.resolve(self.predecessor_pipeline_number)['storage']['driveId']
        if metadata.get('driveId') == self.predecessor_drive_id:
            raise ValueError('Never relocate predecessor-owned state into a continuation pipeline')
        if int(metadata['size']) != reference['byte_length'] or metadata['name'] != reference['original_filename']:
            raise ValueError('Original saved artifact identity differs')
        path = 'quantum_data_lake/' + reference['component'] + '/' + self.original_directory_prefix + identity + '/' + metadata['name']
        receipt = mover.move(mover.preflight([dict(fileId=identity, path=path, sha256=reference['content_sha256'])])[0])
        self.additional_moves.append(receipt)
        self.tracker.document.setdefault('artifactMoves', {})[identity] = receipt
        manifest['files'][identity] = receipt
        self.tracker.pending = True
        self.tracker.write_live_status()
        return self.pipeline.resolve_artifact_reference(reference)

    def read(self, reference, *, maximum=512 * 1024**2):
        if not 0 < reference['byte_length'] <= maximum:
            raise ValueError('Bounded saved artifact required')
        resolved = self.locate_original(reference)
        key = resolved['provider_id'], resolved['content_sha256'], resolved['byte_length']
        if key in self.byte_cache:
            return self.byte_cache[key], resolved
        raw = self.manager.drive.files().get_media(fileId=resolved['provider_id'], supportsAllDrives=True).execute()
        if len(raw) != resolved['byte_length'] or hashlib.sha256(raw).hexdigest() != resolved['content_sha256']:
            raise ValueError('Saved artifact content changed')
        if len(raw) <= 2 * 1024**2:
            self.byte_cache[key] = raw
        return raw, resolved

    def initialize_completion_claims(self):
        models = self.tracker.document['objectDefinitions']['models']
        if len(models) != 5 or len(set(models)) != 5:
            raise ValueError('Original five-model roster required')
        self.tracker.document.setdefault('plan', dict(allocators=list(ALLOCATORS),
            cohorts=['S1T', 'S1.5T', 'S2T', 'S1Tb', 'S1.5Tb', 'S2Tb'], threats=list(THREATS),
            models=list(models), runs=self.target_runs))
        for set_id, group in self.groups.items():
            allocator, capacity, scale = set_id.split(':')
            config = SimpleNamespace(allocator=allocator, scale=float(scale), base_capacity=capacity == 'Tb',
                runs=self.target_runs, models=models, test_scenarios=THREATS, pipeline_storage=self.pipeline.storage_binding,
                overwrite=False, backup_mgr=self.manager)
            for threat in THREATS:
                if group['attacks'][threat]['state'] != 'done':
                    raise ValueError('Only original completed claims can be imported')
                config.attack_type = threat
                for position in range(1, self.target_runs + 1):
                    self.tracker.transition(config, position, 'done')
        self.tracker.document['completionClaimRefs'] = list(self.queue_refs)
        self.tracker.document['importState'] = 'completion-claims-linked-results-verification-pending'
        self.tracker.set_runtime(config, phase='verify-saved-original-sources', state='running')
        self.flush()
        self.tracker.write_live_status()

    def recover_source(self, set_id, reference):
        resolved = self.locate_original(reference)
        if resolved['original_filename'].endswith('.pkl'):
            recovered = recover_completion(self.manager.drive, resolved, self.projector, target_runs=self.target_runs)
            binding = recovered['binding']
            binding['savedScientificSettings'] = recovered['savedScientificSettings']
            return binding
        raw, resolved = self.read(resolved)
        native = json.loads(raw)
        if (str(native.get('pipelineId')) != str(self.pipeline_number) or native.get('setId') != set_id
                or native.get('targetRuns') != self.target_runs or len(native.get('outcomes', [])) != 25 * self.target_runs):
            raise ValueError('Original same-target completion source required')
        if self.predecessor is None:
            self.predecessor = Pipeline(self.predecessor_pipeline_number, registry=self.pipeline._registry)
            self.predecessor_document = self.predecessor.read_workflow()
        prefix_reference = self.predecessor_document['savedBindings'][set_id]
        prefix_raw = self.manager.drive.files().get_media(fileId=prefix_reference['provider_id'], supportsAllDrives=True).execute()
        if (len(prefix_raw) != prefix_reference['byte_length']
                or hashlib.sha256(prefix_raw).hexdigest() != prefix_reference['content_sha256']):
            raise ValueError('Original same-subset predecessor binding changed')
        binding = json.loads(prefix_raw)
        from .completion_notebook import validate_binding
        validate_binding(binding, set_id, self.target_runs - 1)
        envs = deepcopy(binding['env_experiments'])
        models = binding['recovered_config']['models']
        seen = set()
        for outcome in native['outcomes']:
            source = outcome['source_record']
            threat, position, model = source['env_type'], str(source['experiment_id']), source['legacy_model']
            identity = threat, position, model
            if identity in seen or threat not in THREATS or model not in models or not 1 <= int(position) <= self.target_runs:
                raise ValueError('Unexpected or duplicate native outcome')
            if source['allocator'] != binding['recovered_config']['allocator'] or outcome['reward'] != source['reward']:
                raise ValueError('Native result belongs to another allocator/source')
            seen.add(identity)
            if int(position) < self.target_runs:
                prior = envs[threat][position]['results'][model]
                if prior['final_reward'] != source['reward'] or prior['frames_count'] != source['frame_count']:
                    raise ValueError('Native source differs from its original completed prefix: ' + set_id)
            else:
                envs[threat].setdefault(str(self.target_runs), dict(results={}))['results'][model] = dict(
                    final_reward=source['reward'], frames_count=source['frame_count'], saved_source_record=deepcopy(source))
        if set(native.get('runnerReferences', {})) != set(THREATS):
            raise ValueError('Each completed threat must reference its native runner state')
        runners = {threat: self.locate_original(ref) for threat, ref in native['runnerReferences'].items()}
        binding.update(source_sha256=resolved['content_sha256'], sourceRef=resolved,
            recovered_config=dict(binding['recovered_config'], runs=self.target_runs), env_experiments=envs,
            continuation=dict(originalPrefix=prefix_reference, nativeCompletion=resolved, runnerReferences=runners,
                originalSettingsRefs={name: group.get('context', {}).get('settingsRef')
                    for name, group in self.groups[set_id]['attacks'].items()},
                resumeLevel='experiment-runner/model', evaluatorsResumed=0, trainingCalls=0))
        return binding
