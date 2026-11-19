"""Pipeline 6's saved-completion continuation, never an evaluator resume."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import importlib
import tempfile
import time
from types import SimpleNamespace

from daqr.config.pipeline_backup_index import GitHubBackupIndexStore
from daqr.config.tae_workflow import TAEWorkflow
from .recovery import recover_completion


ORIGINAL_QUEUE = dict(repository='pzg8794/pipeline_runner',
    commit='f5515e247df4203627776b5eecef6cbbc7b2e79b',
    path='queues/p6-drive-queue-df461a5f-2935-4a05-857a-653f3fb08cc9.json',
    sha256='2ab710ad68b4fd21ac7b40d0ccad27162f35b64d568b37b167da6496dc49847d')
TS2_QUEUE = dict(repository='pzg8794/pipeline_runner',
    commit='cc6c69541655ce930028f75f0d70385d74ad725b',
    path='queues/p6-original-ts2-common-six-39d19e065b32.json',
    sha256='32e523c994b1746c7f6ecdf46d9dd0fa1fa9da9ae7c1e74d82c5af280ed8955b')
THREATS = ('none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive')
ALLOCATORS = ('Default', 'Random', 'Dynamic', 'ThompsonSampling')
COHORTS = ('S1T', 'S1.5T', 'S2T', 'S1Tb', 'S1.5Tb', 'S2Tb')


def completed_scopes(original, closure):
    if str(original.get('pipelineId')) != '6' or str(closure.get('pipelineId')) != '6':
        raise ValueError('Only the original Pipeline 6 queues are accepted')
    expected = {allocator + ':' + capacity + ':' + scale for allocator in ALLOCATORS
        for capacity in ('T', 'Tb') for scale in ('1', '1.5', '2')}
    if set(original.get('sets', {})) != expected or set(closure.get('sets', {})) != {'ThompsonSampling:T:2'}:
        raise ValueError('The complete original 24-subset scope is required')
    groups = deepcopy(original['sets'])
    groups['ThompsonSampling:T:2'] = deepcopy(closure['sets']['ThompsonSampling:T:2'])
    for name, group in groups.items():
        if set(group.get('attacks', {})) != set(THREATS) or not group.get('finalizationRefs', {}).get('evaluation'):
            raise ValueError('Incomplete saved source scope: ' + name)
        for threat, attack in group['attacks'].items():
            if attack.get('state') != 'done' or attack.get('context', {}).get('run') != 6:
                raise ValueError('Unfinished work requires its original native runner/model continuation: ' + name + '/' + threat)
    return groups


def validate_binding(binding, set_id, target_runs=6, *, frame_overrides=None):
    if frame_overrides is not None and (not isinstance(frame_overrides, dict)
            or set(frame_overrides) != {str(target_runs)}
            or type(frame_overrides[str(target_runs)]) is not int or frame_overrides[str(target_runs)] <= 0):
        raise ValueError('Only an explicit recorded final-position frame policy is accepted')
    allocator, capacity, scale = set_id.split(':')
    config = binding['recovered_config']
    if (config['allocator'] != allocator or config['base_capacity'] != (capacity == 'Tb')
            or float(config['scale']) != float(scale) or config['runs'] != target_runs
            or set(config['test_scenarios']) != set(THREATS)):
        raise ValueError('Original shared subset settings differ: ' + set_id)
    models = config['models']
    if len(models) != 5 or len(set(models)) != 5:
        raise ValueError('Five original models required')
    for threat in THREATS:
        experiments = binding['env_experiments'][threat]
        if set(experiments) != {str(position) for position in range(1, target_runs + 1)}:
            raise ValueError('Incomplete saved experiment positions')
        for position, experiment in experiments.items():
            if set(experiment['results']) != set(models):
                raise ValueError('Incomplete saved model roster')
            for result in experiment['results'].values():
                if (result.get('error') or 'final_reward' not in result
                        or not isinstance(result['final_reward'], (int, float))
                        or result.get('frames_count') != (frame_overrides or {}).get(position,
                            config['base_frames'] + (int(position) - 1) * config['frame_step'])):
                    raise ValueError('Incomplete saved model output')
    json.dumps(binding, allow_nan=False)
    return binding


class SavedPipelineNotebook:
    pipeline_number = 6
    target_runs = 6
    queue_refs = (ORIGINAL_QUEUE, TS2_QUEUE)

    def __init__(self, pipeline, manager, projector, *, read_queue=None, tracker=None):
        if (pipeline.pipeline_id != self.pipeline_number or pipeline.target_runs != self.target_runs
                or manager.pipeline_storage != pipeline.storage_binding):
            raise ValueError('The registered pipeline, original run target and dedicated Drive are required')
        self.pipeline, self.manager, self.projector = pipeline, manager, projector
        self.reader = read_queue or self._read_queue
        self.queues = tuple(self.reader(reference) for reference in self.queue_refs)
        self.groups = self.load_groups()
        self.tracker = tracker or TAEWorkflow(pipeline.pipeline_key, defer_git=True)
        self.tracker.ensure_source()
        self.bindings = {}
        self.receipts = {}
        self.additional_moves = list(self.tracker.document.get('artifactMoves', {}).values())
        self.move_service = None

    def load_groups(self):
        return completed_scopes(*self.queues)

    @property
    def coverage(self):
        return dict(expectedMembers=24, observedMembers=24, expectedOutcomes=600 * self.target_runs,
            observedOutcomes=600 * self.target_runs, complete=True)

    def validate(self, binding, set_id):
        return validate_binding(binding, set_id, self.target_runs,
            frame_overrides=getattr(self, 'frame_overrides', None))

    def flush(self):
        for attempt in range(3):
            try:
                return self.tracker.flush()
            except RuntimeError:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    def completed_report(self):
        document = self.tracker.document
        ready = document.get('readiness', {})
        reference = document.get('preparedDataset')
        if (ready.get('fairnessComplete') is not True or ready.get('preparedComplete') is not True
                or not reference or set(document.get('savedBindings', {})) != set(self.groups)
                or document.get('completionQueueRefs') != list(self.queue_refs)):
            return None
        raw, resolved = self.read(reference, maximum=128 * 1024**2)
        dataset = json.loads(raw)
        coverage = self.coverage
        if (dataset.get('schema') != 'prepared-pipeline-dataset/v1' or dataset.get('coverage') != coverage
                or dataset.get('pipeline', {}).get('definitionId') != 'Pipeline_' + str(self.pipeline_number)
                or dataset.get('pipeline', {}).get('runCount') != self.target_runs
                or set(dataset.get('members', {})) != set(self.groups)
                or len(dataset.get('records', {})) != 600 * self.target_runs):
            raise ValueError('Recorded prepared completion no longer matches this pipeline')
        self.tracker.write_live_status(synced=True)
        return dict(coverage=coverage, preparedDataset=resolved, evaluatorsResumed=0,
            trainingCalls=0, skippedThreats=120, alreadyComplete=True)

    def _read_queue(self, reference):
        registry = self.pipeline._registry
        if reference['repository'] not in registry._stores:
            store = GitHubBackupIndexStore()
            store.repository = reference['repository']
            registry._stores[store.repository] = store
        return registry.read_json(reference)

    def read(self, reference, *, maximum=512 * 1024**2):
        resolved = (deepcopy(reference) if reference.get('drive_root_id') == self.pipeline.drive_id
            else self.pipeline.resolve_artifact_reference(reference))
        if not 0 < resolved['byte_length'] <= maximum:
            raise ValueError('Bounded saved artifact required')
        raw = self.manager.drive.files().get_media(fileId=resolved['provider_id'], supportsAllDrives=True).execute()
        if len(raw) != resolved['byte_length'] or hashlib.sha256(raw).hexdigest() != resolved['content_sha256']:
            raise ValueError('Saved artifact content changed')
        return raw, resolved

    def fairness_inputs(self, set_id, binding):
        cached = self.tracker.document.get('savedFairness', {}).get(set_id)
        if cached:
            result = {name: self.read(reference, maximum=8 * 1024**2) for name, reference in cached.items()}
            self.validate_outcomes(json.loads(result['outcomes'][0]), binding)
            return result
        reference = self.groups[set_id]['finalizationRefs'].get('fairness')
        result = {}
        names = dict(outcomes='fairness_outcomes.json', records='fairness_records.json',
            summary='fairness_summary.json', manifest='fairness_manifest.json')
        if reference:
            raw, resolved = self.read(reference, maximum=4 * 1024**2)
            manifest = json.loads(raw)
            if manifest.get('outcome_count') == 25 * self.target_runs:
                result['manifest'] = raw, resolved
                migrated = self.pipeline._migration_manifest['files'][reference['provider_id']]
                parent = migrated['originalParents'][0]
                for kind, filename in names.items():
                    if kind in result:
                        continue
                    known = dict(self.pipeline._migration_manifest['files'], **self.tracker.document.get('artifactMoves', {}))
                    retained = [item for item in known.values()
                        if item.get('originalParents') == [parent] and Path(item['path']).name == filename]
                    if len(retained) == 1:
                        item = retained[0]
                        current = dict(status='verified', component='framework_state', provider_id=item['fileId'],
                            storage_version=item['storageVersion'], content_sha256=item['sha256'],
                            byte_length=item['bytes'], original_filename=filename, parents=item['parents'],
                            drive_root_id=item['driveId'], path=item['path'])
                        result[kind] = self.read(current, maximum=8 * 1024**2)
                query = "trashed=false and '" + parent + "' in parents and (" + ' or '.join(
                    "name='" + value + "'" for value in names.values()) + ')'
                found = self.manager.drive.files().list(q=query, supportsAllDrives=True,
                    includeItemsFromAllDrives=True, pageSize=1000,
                    fields='nextPageToken,files(id,name,driveId,parents,size,sha256Checksum,version)').execute()
                if found.get('nextPageToken'):
                    raise ValueError('Ambiguous original fairness directory; preserve without guessing')
                for kind, name in names.items():
                    if kind in result:
                        continue
                    candidates = [item for item in found['files'] if item['name'] == name]
                    if len(candidates) > 1:
                        raise ValueError('Multiple original fairness files: ' + set_id + '/' + name)
                    if candidates:
                        item = candidates[0]
                        candidate = dict(status='verified', component='framework_state', provider_id=item['id'],
                            storage_version=item['version'], content_sha256=item['sha256Checksum'],
                            byte_length=int(item['size']), original_filename=name, parents=item['parents'],
                            drive_root_id=item['driveId'], path=str(Path(reference['path']).parent / name))
                        content = self.manager.drive.files().get_media(fileId=item['id'], supportsAllDrives=True).execute()
                        if len(content) != candidate['byte_length'] or hashlib.sha256(content).hexdigest() != candidate['content_sha256']:
                            raise ValueError('Original fairness content changed')
                        result[kind] = content, candidate
        if 'outcomes' in result:
            try:
                self.validate_outcomes(json.loads(result['outcomes'][0]), binding)
            except ValueError:
                self.tracker.document.setdefault('unboundFairnessCandidates', {})[set_id] = {
                    name: ref for name, (_, ref) in result.items()}
                self.tracker.pending = True
                result = {}
        if set(result) == set(names):
            return self._relocate_fairness(set_id, result)
        from daqr.evaluation.fairness_legacy_sidecar import LegacyFairnessSidecarBridge
        config = SimpleNamespace(**dict(binding['recovered_config'], **binding.get('savedScientificSettings', {})))
        facade = SimpleNamespace(configs=config, env_experiments=binding['env_experiments'],
            allocator_id=config.allocator, component='framework_state',
            file_name=binding['sourceRef']['original_filename'], save_to_dir='pipeline-drive')
        with tempfile.TemporaryDirectory(prefix='fairness-missing-', dir=self.manager.dir) as temporary:
            sidecar = LegacyFairnessSidecarBridge().attach_to_legacy_evaluator(config, facade,
                run_name='Pipeline' + str(self.pipeline_number) + '-' + set_id.replace(':', '-'), datalake_root=temporary,
                source='original-saved-results-no-training')
            paths = vars(sidecar.workflow_result.artifacts)
            for kind in names:
                if kind not in result:
                    body = json.loads(Path(paths[kind + '_json']).read_bytes())
                    result[kind] = self.upload_json(names[kind], body, group=set_id)
        self.validate_outcomes(json.loads(result['outcomes'][0]), binding)
        return self._relocate_fairness(set_id, result)

    def _relocate_fairness(self, set_id, inputs):
        from .migration import PipelineArtifactMover
        result = {}
        for name, (raw, reference) in inputs.items():
            if reference['drive_root_id'] == self.pipeline.drive_id:
                result[name] = raw, reference
                continue
            if self.move_service is None:
                from daqr.config.gd_backup_manager import GoogleDriveBackupManager
                self.move_service = GoogleDriveBackupManager.pipeline_creation_drive_service()
            mover = PipelineArtifactMover(self.move_service, self.pipeline.storage_binding)
            planned = mover.preflight([dict(fileId=reference['provider_id'],
                sha256=reference['content_sha256'],
                path='quantum_data_lake/framework_state/recovered-' + set_id.replace(':', '-') + '/' + reference['original_filename'])])[0]
            receipt = mover.move(planned)
            self.additional_moves.append(receipt)
            self.tracker.document.setdefault('artifactMoves', {})[receipt['fileId']] = receipt
            self.tracker.pending = True
            self.tracker.write_live_status()
            result[name] = raw, dict(reference, drive_root_id=receipt['driveId'], path=receipt['path'],
                parents=receipt['parents'], storage_version=receipt['storageVersion'])
        self.tracker.document.setdefault('savedFairness', {})[set_id] = {name: reference
            for name, (_, reference) in result.items()}
        self.tracker.pending = True
        return result

    @staticmethod
    def validate_outcomes(outcomes, binding):
        expected = {(threat, str(position), model): result for threat, positions in binding['env_experiments'].items()
            for position, experiment in positions.items() for model, result in experiment['results'].items()}
        seen = set()
        for outcome in outcomes:
            source = outcome['source_record']
            key = source['env_type'], str(source['experiment_id']), source.get('legacy_model', source.get('group'))
            if key in seen or key not in expected:
                raise ValueError('Fairness duplicates or substitutes original model outcomes')
            result = expected[key]
            if (source['reward'] != result['final_reward'] or outcome['reward'] != result['final_reward']
                    or source['frame_count'] != result['frames_count']
                    or source['allocator'] != binding['recovered_config']['allocator']):
                raise ValueError('Fairness differs from original saved results')
            seen.add(key)
        if seen != set(expected):
            raise ValueError('Fairness omits original saved outcomes')

    def recover(self, set_id):
        if set_id in self.bindings:
            return self.bindings[set_id]
        cached = self.tracker.document.get('savedBindings', {}).get(set_id)
        if cached:
            raw, _ = self.read(cached, maximum=8 * 1024**2)
            binding = self.validate(json.loads(raw), set_id)
            self.bindings[set_id] = binding
            return binding
        reference = self.groups[set_id]['finalizationRefs']['evaluation']
        binding = self.recover_source(set_id, reference)
        self.validate(binding, set_id)
        self.bindings[set_id] = binding
        _, reference = self.upload_json('saved_source_binding.json', binding, group=set_id)
        self.tracker.document.setdefault('savedBindings', {})[set_id] = reference
        self.tracker.pending = True
        return binding

    def recover_source(self, set_id, reference):
        if set_id == 'ThompsonSampling:T:2':
            binding = self._recover_ts2(reference)
        else:
            if reference['original_filename'].endswith('.json'):
                raw, _ = self.read(reference)
                saved = json.loads(raw)
                if saved.get('setId') != set_id or saved.get('targetRuns') != 6:
                    raise ValueError('Saved completion receipt belongs to another subset')
                reference = saved['sourceRef']
            resolved = self.pipeline.resolve_artifact_reference(reference)
            recovered = recover_completion(self.manager.drive, resolved, self.projector)
            binding = recovered['binding']
            binding['savedScientificSettings'] = recovered['savedScientificSettings']
        return binding

    def _recover_ts2(self, reference):
        raw, resolved = self.read(reference)
        native = json.loads(raw)
        if str(native.get('pipelineId')) != '6' or native.get('setId') != 'ThompsonSampling:T:2' or native.get('targetRuns') != 6:
            raise ValueError('Original-settings six-run native completion required')
        outcomes = native['outcomes']
        if len(outcomes) != 150:
            raise ValueError('All six original positions and five threats/models required')
        original = outcomes[0]['provenance']['extras']['originalEvaluator']
        original = self.pipeline.resolve_artifact_reference(original)
        recovered = recover_completion(self.manager.drive, original, self.projector, target_runs=5)
        binding = recovered['binding']
        base = deepcopy(binding['env_experiments'])
        models = binding['recovered_config']['models']
        seen = set()
        for outcome in outcomes:
            source = outcome['source_record']
            key = source['env_type'], str(source['experiment_id']), source['legacy_model']
            if key in seen or key[0] not in THREATS or key[2] not in models or not 1 <= int(key[1]) <= 6:
                raise ValueError('Duplicate or foreign native outcome')
            seen.add(key)
            if int(key[1]) <= 5:
                prior = base[key[0]][key[1]]['results'][key[2]]
                if prior['final_reward'] != source['reward'] or prior['frames_count'] != source['frame_count']:
                    raise ValueError('Native completion changed an original completed result')
        for threat, attack in self.groups['ThompsonSampling:T:2']['attacks'].items():
            refs = [value for value in attack['driveRefs'] if value['original_filename'].startswith('QuantumExperimentRunner_')]
            if len(refs) != 1:
                raise ValueError('One exact native runner state required')
            runner_raw, _ = self.read(refs[0])
            runner = pickle.loads(runner_raw)
            del runner_raw
            if not isinstance(runner, dict) or not runner.get('is_complete') or set(runner['results']) != set(models):
                raise ValueError('Incomplete native runner state')
            for model, result in runner['results'].items():
                recorded = [value for value in outcomes if value['source_record']['env_type'] == threat
                    and str(value['source_record']['experiment_id']) == '6' and value['source_record']['legacy_model'] == model]
                if len(recorded) != 1 or recorded[0]['reward'] != result['final_reward']:
                    raise ValueError('Native saved runner differs from completion outcome')
            primitive = self.projector.__globals__['primitive']
            base[threat]['6'] = primitive(dict(results={name: {key: value for key, value in result.items() if key != 'model_results'}
                for name, result in runner['results'].items()}, exp_id='6'))
            del runner
        binding.update(source_sha256=resolved['content_sha256'], sourceRef=resolved, env_experiments=base,
            recovered_config=dict(binding['recovered_config'], runs=6),
            savedScientificSettings=recovered['savedScientificSettings'],
            continuation=dict(originalPrefix=original, nativeCompletion=resolved,
                resumeLevel='experiment-runner/model', evaluatorsResumed=0, trainingCalls=0))
        return binding

    def display_completion(self, set_id, binding):
        self.validate(binding, set_id)
        config = SimpleNamespace(**binding['recovered_config'], pipeline_storage=self.pipeline.storage_binding,
            backup_mgr=self.manager, overwrite=False)
        self.tracker.document.setdefault('plan', dict(allocators=list(ALLOCATORS), cohorts=list(COHORTS),
            threats=list(THREATS), models=list(config.models), runs=self.target_runs))
        self.tracker.set_runtime(config, phase='saved-completion-and-postprocessing', state='running')
        for threat in THREATS:
            config.attack_type = threat
            for position in range(1, self.target_runs + 1):
                self.tracker.transition(config, position, 'done')
            print(set_id, threat, 'done — saved work skipped', flush=True)
        return config

    def upload_json(self, name, value, *, group):
        raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
        digest = hashlib.sha256(raw).hexdigest()
        key = group + '/' + name + '/' + digest
        if key in self.receipts:
            return raw, self.receipts[key]
        retained = self.tracker.document.get('notebookArtifacts', {}).get(key)
        if retained:
            existing, resolved = self.read(retained, maximum=64 * 1024**2)
            if existing != raw:
                raise ValueError('Existing notebook artifact changed')
            self.receipts[key] = resolved
            return raw, resolved
        directory = Path(self.manager.dir) / 'pipeline-postprocessing'
        directory.mkdir(exist_ok=True)
        path = directory / name
        path.write_bytes(raw)
        day = 'pipeline' + str(self.pipeline_number) + '-' + group.replace(':', '-') + '-' + digest[:16]
        try:
            if not self.manager._upload_file_to_drive('framework_state', day, str(path), name):
                raise RuntimeError('Pipeline Drive upload failed')
            upload = self.manager.workflow_upload_receipts[name]
            metadata = self.manager.drive.files().get(fileId=upload['fileId'], supportsAllDrives=True,
                fields='id,name,driveId,parents,size,sha256Checksum,version').execute()
            if metadata['sha256Checksum'] != digest or int(metadata['size']) != len(raw) or metadata['driveId'] != self.pipeline.drive_id:
                raise ValueError('Pipeline artifact upload readback differs')
            reference = dict(status='verified', component='framework_state', provider_id=metadata['id'],
                storage_version=metadata['version'], content_sha256=digest, byte_length=len(raw),
                original_filename=name, parents=metadata['parents'], drive_root_id=metadata['driveId'],
                path='quantum_data_lake/framework_state/' + day + '/' + name)
            self.receipts[key] = reference
            self.tracker.document.setdefault('notebookArtifacts', {})[key] = reference
            self.tracker.pending = True
            return raw, reference
        finally:
            path.unlink(missing_ok=True)
            if not any(directory.iterdir()):
                directory.rmdir()

    def prepare(self, preparation_root):
        root = Path(preparation_root).resolve()
        source = root / 'pipeline_preparation.py'
        if hashlib.sha256(source.read_bytes()).hexdigest() != 'f7cfbcea5bac74201e3327ab1c90cd440d8d98966d7f80a17dc6ce2c7062e40f':
            raise ValueError('Accepted canonical preparation source changed; review before using')
        import daqr.evaluation
        if str(root) not in daqr.evaluation.__path__:
            daqr.evaluation.__path__.append(str(root))
        preparation = importlib.import_module('daqr.evaluation.pipeline_preparation')
        if Path(preparation.__file__).resolve() != source:
            raise ValueError('Wrong canonical preparation module')
        members, expected = [], []
        for set_id, binding in self.bindings.items():
            current = SimpleNamespace(**binding['recovered_config'], pipeline_storage=self.pipeline.storage_binding)
            self.tracker.set_runtime(current, phase='fairness-and-preparation', state='running')
            fairness = self.fairness_inputs(set_id, binding)
            binding_input = self.upload_json('saved_source_binding.json', binding, group=set_id)
            campaign_input = self.upload_json('saved_completion_sources.json',
                dict(queueRefs=list(self.queue_refs), setId=set_id,
                    savedQueueState=self.groups[set_id], evaluatorsResumed=0, trainingCalls=0), group=set_id)
            completion = self.upload_json('completion.json', dict(status='COMPLETE_SAVED_OUTPUTS',
                source_evaluator_sha256=binding['sourceRef']['content_sha256'],
                source_campaign_receipt_sha256=campaign_input[1]['content_sha256'],
                threats=5, positions=self.target_runs, models=5, evaluatorsResumed=0, trainingCalls=0), group=set_id)
            artifacts = dict(fairness, sourceBinding=binding_input, completion=completion)
            context = dict(allocator=binding['recovered_config']['allocator'],
                scale=binding['recovered_config']['scale'], base_capacity=binding['recovered_config']['base_capacity'])
            members.append(dict(memberId=set_id, context=context, evaluatorRef=binding['sourceRef'],
                campaignRef=campaign_input[1], artifacts={key: preparation.PipelineJSONInput(raw, reference)
                    for key, (raw, reference) in artifacts.items()}))
            expected.append(dict(memberId=set_id, context=context, expectedOutcomeIdentities=[
                dict(scenario=threat, experiment=str(position), model=model)
                for threat in THREATS for position in range(1, self.target_runs + 1) for model in binding['recovered_config']['models']]))
            print(set_id, 'fairness verified; preparation member ready', flush=True)
            self.tracker.document.setdefault('postprocessing', {})[set_id] = dict(fairness='done', preparation='member-verified')
            self.tracker.pending = True
            self.flush()
            self.tracker.write_live_status()
        if set(self.bindings) != set(self.groups):
            raise ValueError('All 24 original subsets must be recovered before whole-pipeline preparation')
        definition = dict(definitionId='Pipeline_' + str(self.pipeline_number), executionId=self.queues[0]['executionId'], runCount=self.target_runs,
            expectedMembers=expected, sourceRefs=[member['evaluatorRef'] for member in members])
        dataset = preparation.build_pipeline_prepared_dataset(definition, members).to_dict()
        if dataset['coverage'] != self.coverage or not dataset['publicationReadiness']['ready']:
            raise ValueError('Whole-pipeline preparation coverage/persistence is incomplete')
        raw, reference = self.upload_json('PreparedPipelineDataset.json', dataset, group='whole-pipeline')
        downloaded, _ = self.read(reference, maximum=128 * 1024**2)
        if downloaded != raw:
            raise ValueError('Prepared dataset readback differs')
        self.tracker.document['preparedDataset'] = reference
        self.tracker.document['stageStatus'] = dict(evaluators={
            'allocators': dict(completed=4, expected=4),
            'experiments': dict(completed=120, expected=120),
            'models': dict(completed=600, expected=600)})
        self.tracker.document['readiness'] = dict(fairnessComplete=True, preparedComplete=True)
        self.tracker.pending = True
        return dict(coverage=dataset['coverage'], preparedDataset=reference,
            evaluatorsResumed=0, trainingCalls=0, skippedThreats=120)

    def finish(self, config):
        if not self.tracker.document.get('readiness', {}).get('preparedComplete'):
            raise RuntimeError('Fairness and preparation must finish before final status')
        self.tracker.document['importState'] = 'verified-saved-completion-imported'
        self.tracker.document['completionQueueRefs'] = list(self.queue_refs)
        if self.additional_moves:
            from .migration import PipelineMigrationPublisher
            from .pipeline import Pipeline
            self.pipeline = Pipeline(self.pipeline_number)
            PipelineMigrationPublisher().publish(self.pipeline, self.additional_moves)
            self.pipeline = Pipeline(self.pipeline_number)
            self.tracker.document['storageMigration'] = self.pipeline.read_workflow()['storageMigration']
            self.tracker.head = None
            self.tracker.ensure_source()
        self.tracker.set_runtime(config, phase='complete', state='done')
        self.tracker.pending = True
        self.flush()
        self.tracker.write_live_status(synced=True)
        self.backup_index_result = self.manager.synchronize_backup_index(overwrite=True)
