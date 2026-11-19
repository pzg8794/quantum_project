"""Pipeline 155: existing native nine-run queue, then saved-output postprocessing."""
from copy import deepcopy
from datetime import datetime
import hashlib
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import re
from types import SimpleNamespace

from .completion_notebook import ALLOCATORS, THREATS, validate_binding
from .eight_run_notebook import EightRunPipelineNotebook
from .pipeline import Pipeline
from .registry import validate_reference
from .adoption import PipelineAdoptionPublisher
from daqr.config.pipeline_backup_index import GitHubBackupIndexStore
from daqr.config.tae_workflow import TAEWorkflow


PROFILE = json.loads(Path(__file__).with_name('pipeline155_sources.json').read_bytes())


def nine_run_scopes(queue):
    expected = {allocator + ':' + capacity + ':' + scale for allocator in ALLOCATORS
        for capacity in ('T', 'Tb') for scale in ('1', '1.5', '2')}
    if (queue.get('pipelineId') not in (155, '155') or queue.get('testOnly') is not False
            or set(queue.get('sets', {})) != expected):
        raise ValueError('The original full Pipeline 155 queue is required')
    for group in queue['sets'].values():
        if set(group['attacks']) != set(THREATS):
            raise ValueError('All five original threats required')
        for row in group['attacks'].values():
            if row['context']['run'] != 9:
                raise ValueError('Original nine-run context required')
    return deepcopy(queue['sets'])


def native_complete(groups):
    return all(all(row['state'] == 'done' for row in group['attacks'].values())
        and {'evaluation', 'fairness'} <= set(group.get('finalizationRefs', {})) for group in groups.values())


def verify_native_progress(prefix, native, set_id, frames):
    validate_binding(prefix, set_id, 8)
    json.dumps(native, allow_nan=False)
    if (str(native.get('pipelineId')) != '155' or native.get('setId') != set_id
            or native.get('targetRuns') != 9 or len(native.get('outcomes', [])) != 225
            or set(native.get('runnerReferences', {})) != set(THREATS)):
        raise ValueError('Exact finalized nine-run source required')
    models = prefix['recovered_config']['models']
    seen = set()
    for outcome in native['outcomes']:
        source = outcome['source_record']
        threat, position, model = source['env_type'], str(source['experiment_id']), source['legacy_model']
        identity = threat, position, model
        if (identity in seen or threat not in THREATS or model not in models
                or not 1 <= int(position) <= 9 or source['allocator'] != set_id.split(':')[0]
                or source['reward'] != outcome['reward']):
            raise ValueError('Foreign or duplicate native progress')
        seen.add(identity)
        if int(position) <= 8:
            prior = prefix['env_experiments'][threat][position]['results'][model]
            if prior['final_reward'] != source['reward'] or prior['frames_count'] != source['frame_count']:
                raise ValueError('Native progress differs from its verified predecessor')
        elif source['frame_count'] != (frames if frames is not None else
                prefix['recovered_config']['base_frames'] + 8 * prefix['recovered_config']['frame_step']):
            raise ValueError('Native progress differs from the original ninth-position frame policy')
    return True


class NineRunPipelineNotebook(EightRunPipelineNotebook):
    pipeline_number = 155
    target_runs = 9
    predecessor_pipeline_number = 154
    original_directory_prefix = 'nine-original-'
    queue_refs = (PROFILE['queueRef'],)

    def __init__(self, pipeline, *args, **kwargs):
        self.native_metadata_cache = {}
        if kwargs.get('tracker') is None:
            kwargs['tracker'] = TAEWorkflow(pipeline.pipeline_key)
        previous = pipeline.read_workflow().get('completionQueueRefs')
        if previous:
            if (len(previous) != 1 or previous[0]['repository'] != PROFILE['queueRef']['repository']
                    or previous[0]['path'] != PROFILE['queueRef']['path']):
                raise ValueError('Completion belongs to another queue')
            self.queue_refs = tuple(previous)
        super().__init__(pipeline, *args, **kwargs)
        metadata = self.original_metadata()
        frames = metadata['spec']['frames_per_new_run']
        self.frame_overrides = {'9': frames} if frames is not None else None
        self.frame_policy = dict(run=9, inheritedPrefixRuns=8, framesPerNewRun=frames,
            label=metadata['workflow']['label'], specRef=metadata['specRef'])
        if (self.tracker.document.get('readiness', {}).get('preparedComplete')
                and self.tracker.document.get('executionFramePolicy') != self.frame_policy):
            raise ValueError('Do not reinterpret a prepared execution with another frame policy')
        for key, value in dict(executionFramePolicy=self.frame_policy,
                displayName='Pipeline 155 · 9 runs · ' + self.frame_policy['label']).items():
            if self.tracker.document.get(key) != value:
                self.tracker.document[key] = deepcopy(value)
                self.tracker.pending = True

    def load_groups(self):
        return nine_run_scopes(self.queues[0])

    def _read_queue(self, reference):
        reference = validate_reference(reference)
        if reference['repository'] != PROFILE['queueRef']['repository']:
            raise ValueError('Only the original native queue repository is accepted')
        key = tuple(reference[name] for name in ('repository', 'commit', 'path'))
        if key not in self.native_metadata_cache:
            stores = self.pipeline._registry._stores
            if reference['repository'] not in stores:
                store = GitHubBackupIndexStore()
                store.repository = reference['repository']
                stores[store.repository] = store
            raw = PipelineAdoptionPublisher._read(stores[reference['repository']],
                reference['commit'], reference['path']).encode()
            if sum(map(len, self.native_metadata_cache.values())) + len(raw) > 32 * 1024**2:
                raise ValueError('Bounded immutable native metadata cache exceeded')
            self.native_metadata_cache[key] = raw
        raw = self.native_metadata_cache[key]
        if reference.get('sha256') is not None and hashlib.sha256(raw).hexdigest() != reference['sha256']:
            raise ValueError('Pinned native metadata content changed')
        blocks = re.findall(r'```json\s*\n(.*?)\n```', raw.decode(), re.S)
        return json.loads(blocks[0] if len(blocks) == 1 else raw)

    def refresh_queue(self):
        reference = dict(PROFILE['queueRef'])
        reference.pop('sha256')
        store = self.pipeline._registry._stores[reference['repository']]
        reference['commit'] = store.api('git/ref/heads/main')['object']['sha']
        self.reader(reference)
        raw = self.native_metadata_cache[tuple(reference[name] for name in ('repository', 'commit', 'path'))]
        reference['sha256'] = hashlib.sha256(raw).hexdigest()
        self.queues = (json.loads(raw),)
        self.groups = nine_run_scopes(self.queues[0])
        self.queue_refs = (reference,)

    def original_metadata(self):
        if hasattr(self, '_original_metadata_cache'):
            return deepcopy(self._original_metadata_cache)
        path = Path(PROFILE['originalMetadata']).expanduser()
        if path.stat().st_size > 8 * 1024**2:
            raise ValueError('Bounded original continuation metadata required')
        raw = path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest() != PROFILE['originalMetadataSha256']:
            raise ValueError('Original continuation metadata changed; preserve and reconcile it')
        metadata = json.loads(raw)
        if self.reader(metadata['specRef']) != metadata['spec']:
            raise ValueError('Original SPEC differs from its pinned Git source')
        if (metadata['spec']['workflowRef'] != metadata['workflowRef']
                or self.reader(metadata['workflowRef']) != metadata['workflow']):
            raise ValueError('Original workflow differs from its pinned Git source')
        workflow = metadata['workflow']
        if (workflow['pipelineId'] != 155 or workflow['targetRuns'] != 9
                or workflow['executionId'] != self.queues[0]['executionId']):
            raise ValueError('Original Pipeline 155 execution required')
        frames = metadata['spec']['frames_per_new_run']
        if frames is not None and not (type(frames) is int and frames == 1):
            raise ValueError('The original native worker frame contract changed')
        self._original_metadata_cache = deepcopy(metadata)
        return metadata

    def validate(self, binding, set_id):
        if binding.get('executionFramePolicy') != self.frame_policy:
            raise ValueError('Saved completion must retain its exact published frame policy')
        return super().validate(binding, set_id)

    def recover_source(self, set_id, reference):
        binding = super().recover_source(set_id, reference)
        binding['executionFramePolicy'] = deepcopy(self.frame_policy)
        return binding

    def native_packet(self, *, preflight=False):
        metadata = self.original_metadata()
        workflow = metadata['workflow']
        relocations = dict(self.tracker.document.get('artifactMoves', {}))
        predecessor = Pipeline(154, registry=self.pipeline._registry)
        for pipeline in (predecessor, self.pipeline):
            migration = pipeline.pipeline_record.get('storageMigration', {}).get('manifestRef')
            if migration:
                manifest = pipeline._registry.read_json(migration)
                if manifest['driveId'] != pipeline.drive_id or manifest['pipelineId'] != str(pipeline.pipeline_id):
                    raise ValueError('Relocation manifest belongs to another pipeline')
                for identity, receipt in manifest['files'].items():
                    if identity in relocations and relocations[identity]['driveId'] != receipt['driveId']:
                        raise ValueError('Conflicting source ownership')
                    relocations[identity] = receipt
        binding_source = Path(__file__).with_name('continuation_storage.py')
        pinned = {}
        for name in ('spec', 'workflow'):
            reference = metadata[name + 'Ref']
            raw = self.native_metadata_cache[tuple(reference[key] for key in ('repository', 'commit', 'path'))]
            pinned[name] = dict(reference=reference, content=base64.b64encode(raw).decode())
        return dict(pipelineId=155, targetRuns=9, storage=self.pipeline.storage_binding,
            pipelineReference=self.pipeline.pipeline_reference, worker=PROFILE['worker'],
            notebookSupport=PROFILE['notebookSupport'], settingsCache=PROFILE['settingsCache'],
            bindingSource=dict(path=str(binding_source), sha256=hashlib.sha256(binding_source.read_bytes()).hexdigest()),
            specRef=metadata['specRef'], requestId=workflow['runnerRequestId'], relocations=relocations,
            pinnedMetadata=pinned,
            date=datetime.now().strftime('day_%Y%m%d'), monitorDirectory=metadata['spec']['monitorDirectory'])

    def native_command(self, *, preflight=False):
        packet = self.native_packet(preflight=preflight)
        path = Path(self.manager.dir) / 'native-binding.json'
        raw = json.dumps(packet, sort_keys=True, indent=2).encode()
        path.write_bytes(raw)
        path.chmod(0o600)
        command = [sys.executable, '-B', str(Path(__file__).with_name('native155_worker.py')),
            '--binding', str(path), '--sha256', hashlib.sha256(raw).hexdigest()]
        if preflight:
            command.append('--preflight')
        return command, packet

    def native_preflight(self):
        command, _ = self.native_command(preflight=True)
        result = subprocess.run(command, env={**os.environ, 'PYTHONHASHSEED': '0',
            'PYTHONDONTWRITEBYTECODE': '1'}, text=True, capture_output=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError('Pinned native preflight failed: ' + result.stderr[-8000:])
        print(result.stdout, end='')

    def restore_saved_progress(self):
        predecessor = Pipeline(154, registry=self.pipeline._registry)
        document = predecessor.read_workflow()
        if (set(document.get('savedBindings', {})) != set(self.groups)
                or document.get('readiness', {}).get('preparedComplete') is not True):
            raise ValueError('The verified full eight-run predecessor is required')
        sources = {}

        def read_verified(reference, *, native_checkpoint=False):
            key = reference['provider_id'], reference['content_sha256'], reference['byte_length']
            if not 0 < key[2] <= (128 if native_checkpoint else 8) * 1024**2:
                raise ValueError('Bounded saved progress source required')
            if key not in self.byte_cache:
                raw = self.manager.drive.files().get_media(fileId=key[0], supportsAllDrives=True).execute()
                if len(raw) != key[2] or hashlib.sha256(raw).hexdigest() != key[1]:
                    raise ValueError('Saved progress source content changed')
                if len(raw) <= 2 * 1024**2:
                    self.byte_cache[key] = raw
            else:
                raw = self.byte_cache[key]
            return None if native_checkpoint else json.loads(raw)

        for set_id, reference in document['savedBindings'].items():
            prefix = read_verified(reference)
            validate_binding(prefix, set_id, 8)
            group = self.groups[set_id]
            native_reference = group.get('finalizationRefs', {}).get('evaluation')
            finalized = native_reference and all(row['state'] == 'done' for row in group['attacks'].values())
            adopted = None
            if finalized:
                verify_native_progress(prefix, read_verified(native_reference), set_id,
                    self.frame_policy['framesPerNewRun'])
            elif (any(row['state'] == 'done' for row in group['attacks'].values())
                    and self.tracker.document.get('adoptedNinthCompletions', {}).get('setId') == set_id):
                adoption = self.tracker.document.get('adoptedNinthCompletions', {})
                original = self.original_metadata()
                if (adoption.get('setId') != set_id or adoption.get('executionId') != original['workflow']['executionId']
                        or adoption.get('metadataSha256') != PROFILE['originalMetadataSha256']
                        or self.frame_policy['framesPerNewRun'] is not None or adoption.get('modelsVerified') != 25):
                    raise ValueError('Completed native attacks require their exact adoption proof or finalized outcomes')
                profile = next(row for row in original['profiles'] if row['setId'] == set_id)
                adopted = adoption['references']
                if set(adopted) != set(THREATS):
                    raise ValueError('Exact five-threat adoption required')
                for threat, checkpoint in adopted.items():
                    row = group['attacks'][threat]
                    checked = adoption['modelValidation'][threat]
                    expected = profile['attacks'][threat]['context']
                    if (row['state'] != 'done' or row['origin'] != 'reused' or checkpoint not in row['driveRefs']
                            or row['context']['seed'] != checked['seed'] or checked['seed'] != expected['experimentSeed']
                            or checked['frames'] != expected['frames'] or checked['modelSeeds'] != expected['modelSeeds']):
                        raise ValueError('Adopted checkpoint differs from original native context')
                    read_verified(checkpoint, native_checkpoint=True)
            sources[set_id] = dict(prefix=reference, native=native_reference if finalized else None, adopted=adopted)
        plan = dict(allocators=list(ALLOCATORS), cohorts=['S1T', 'S1.5T', 'S2T', 'S1Tb', 'S1.5Tb', 'S2Tb'],
            threats=list(THREATS), models=list(self.tracker.document['objectDefinitions']['models']), runs=9)
        if self.tracker.document.get('plan', plan) != plan:
            raise ValueError('Saved progress belongs to a different pipeline plan')
        self.tracker.document['plan'] = plan
        for set_id, source in sources.items():
            for threat in THREATS:
                config = self.config(set_id, threat)
                for position in range(1, 10 if source['native'] or source['adopted'] else 9):
                    self.tracker.transition(config, position, 'done')
        for key, value in dict(nativePrefixReference=predecessor.workflow_reference,
                verifiedProgressSources=sources, completionClaimRefs=list(self.queue_refs)).items():
            if self.tracker.document.get(key) != value:
                self.tracker.document[key] = deepcopy(value)
                self.tracker.pending = True
        self.flush()
        self.tracker.write_live_status(synced=True)
        return dict(prefixOutcomes=4800, ninthPositionOutcomes=25 * sum(
            bool(source['native'] or source['adopted']) for source in sources.values()), scientificWorkersStarted=0)

    def full_frame_recovery(self):
        recovered = deepcopy(self.tracker.document.get('fullFrameCheckpointReconciliation', {}))
        if recovered and (recovered.get('pipelineId') != 155
                or recovered.get('originalMetadataSha256') != PROFILE['originalMetadataSha256']
                or recovered.get('recordedNinthFrames') != self.frame_policy['framesPerNewRun']):
            raise ValueError('Full-frame reconciliation belongs to another recorded execution')
        return recovered

    def config(self, set_id, threat):
        allocator, capacity, scale = set_id.split(':')
        return SimpleNamespace(allocator=allocator, scale=float(scale), base_capacity=capacity == 'Tb',
            runs=9, models=list(self.tracker.document['objectDefinitions']['models']),
            test_scenarios=list(THREATS), pipeline_storage=self.pipeline.storage_binding,
            overwrite=False, backup_mgr=self.manager, attack_type=threat)

    def display_native_status(self, packet):
        queue = packet['queue']
        nine_run_scopes(queue)
        active = packet.get('extra', {}).get('currentSet')
        if active is not None and active not in queue['sets']:
            raise ValueError('Native runtime reports another subset')
        for set_id, group in queue['sets'].items():
            for threat, row in group['attacks'].items():
                config = self.config(set_id, threat)
                if row['state'] == 'done':
                    self.tracker.transition(config, 9, 'done')
                elif set_id == active and (row['state'] == 'running'
                        or packet.get('extra', {}).get('currentObjectId') is not None
                        and row.get('runnerObjectId') == packet['extra']['currentObjectId']):
                    cohort = 'S' + format(config.scale, 'g') + ('Tb' if config.base_capacity else 'T')
                    experiment = self.tracker.document['allocators'][config.allocator]['cohorts'][cohort]['threats'][threat]['experiments']['9']
                    experiment['state'] = 'running'
                    states = packet.get('modelStates', {}).get(row.get('runnerObjectId'), {})
                    if set(states) - set(config.models) or any(state not in ('running', 'done') for state in states.values()):
                        raise ValueError('Foreign native model status')
                    for model, state in states.items():
                        experiment['models'][model] = dict(state=state)
                    self.tracker.pending = True
        if active is not None:
            self.tracker.set_runtime(self.config(active, THREATS[0]),
                phase=packet.get('extra', {}).get('phase', 'native-runner/model'),
                state='running' if packet['state'] == 'running' else 'stopped')
        self.tracker.write_live_status()
        published = getattr(self, '_native_published_sets', set())
        newly_complete = {name for name, group in queue['sets'].items()
            if all(row['state'] == 'done' for row in group['attacks'].values())} - published
        if newly_complete:
            self.flush()
            self._native_published_sets = published | newly_complete

    def resume_native(self):
        self.native_packet()
        self.refresh_queue()
        initial_done = sum(row['state'] == 'done' for group in self.groups.values() for row in group['attacks'].values())
        self.native_execution_summary = dict(executedThisSession=False, initialDoneThreats=initial_done,
            sourceLabel=self.frame_policy['label'], framesPerNewRun=self.frame_policy['framesPerNewRun'])
        if native_complete(self.groups):
            return
        predecessor = Pipeline(154, registry=self.pipeline._registry)
        parent = predecessor.read_workflow()
        if (not parent.get('readiness', {}).get('preparedComplete')
                or set(parent.get('savedBindings', {})) != set(self.groups)):
            raise ValueError('Original full eight-run predecessor required')
        if self.tracker.document.get('nativePrefixReference') != predecessor.workflow_reference:
            for set_id in self.groups:
                for threat in THREATS:
                    config = self.config(set_id, threat)
                    for position in range(1, 9):
                        self.tracker.transition(config, position, 'done')
            self.tracker.document['nativePrefixReference'] = predecessor.workflow_reference
            self.flush()
        for set_id, group in self.groups.items():
            if all(row['state'] == 'done' for row in group['attacks'].values()) and group.get('finalizationRefs', {}).get('evaluation'):
                binding = self.recover(set_id)
                self.display_completion(set_id, binding)
                self.flush()
        command, packet = self.native_command()
        owner = self.queues[0].get('claimOwner')
        if owner and subprocess.run(['ps', '-p', str(owner['pid']), '-o', 'lstart='],
                capture_output=True, text=True).stdout.strip() == owner['started']:
            raise RuntimeError('Original native owner is alive; do not dispatch a duplicate')
        feed = Path(self.manager.dir) / 'native-status.json'
        log = Path(packet['monitorDirectory']) / 'production.log'
        offset = log.stat().st_size if log.exists() else 0
        environment = {**os.environ, 'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
        with log.open('ab', buffering=0) as stream:
            process = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        self.native_execution_summary['executedThisSession'] = True
        last = None
        while process.poll() is None:
            if feed.exists():
                raw = feed.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                if digest != last:
                    self.display_native_status(json.loads(raw))
                    last = digest
            with log.open('rb') as stream:
                stream.seek(offset)
                output = stream.read(128 * 1024)
                offset = stream.tell()
                if output:
                    print(output.decode(errors='replace'), end='', flush=True)
            time.sleep(1)
        if feed.exists():
            self.display_native_status(json.loads(feed.read_bytes()))
        if process.returncode != 0:
            raise RuntimeError('Original native continuation failed; keep staging and inspect ' + str(log))
        self.refresh_queue()
        if not native_complete(self.groups):
            raise RuntimeError('Native queue is not complete; do not claim whole-pipeline completion')
        self.native_execution_summary.update(finalDoneThreats=120, newlyCompletedThreats=120-initial_done)

    def prepare(self, preparation_root):
        report = super().prepare(preparation_root)
        report['nativeExecution'] = deepcopy(self.native_execution_summary)
        report['trainingCallsScope'] = 'Saved-output postprocessing only; native continuation reported separately'
        self.tracker.document['nativeExecutionSummary'] = deepcopy(self.native_execution_summary)
        return report
