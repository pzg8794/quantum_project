"""Publish runner-owned cohort status to the existing TAE_Workflow index."""

import base64
from collections import OrderedDict
import io
import json
import pickle
import re
from threading import RLock, Timer
import time
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor


def reconcile_cohort_report(document, existing, snapshots=None):
    plan = document.get('plan') or {}
    report = json.loads(json.dumps(existing))
    allocators = document.get('allocators') or {}
    snapshots = snapshots or {}
    artifact_allocators = {key.split('/')[0] for records in snapshots.values() for key in records
                           if len(key.split('/')) == 3}
    threats, models, runs = plan.get('threats'), plan.get('models'), plan.get('runs')
    complete_plan = bool(threats and models and type(runs) is int and runs > 0)
    for allocator in set(plan.get('allocators') or ()) | set(allocators) | artifact_allocators:
        observed = allocators.get(allocator, {}).get('cohorts', {})
        cohorts = report.setdefault(allocator, {}).setdefault('cohorts', {})
        for cohort in set(plan.get('cohorts') or ()) | set(observed) | set(snapshots):
            if cohorts.get(cohort) in {'done', 'running', 'stopped'}:
                continue
            saved = observed.get(cohort, {}).get('threats', {})
            records = [record for threat in saved.values() for record in threat.get('experiments', {}).values()]
            published = snapshots.get(cohort, {})
            published_for_allocator = any(key.startswith(allocator + '/') and record.get('state')
                                          for key, record in published.items())
            def verified(threat, position):
                if published.get(f'{allocator}/{threat}/{position}', {}).get('state'):
                    return True
                record = saved.get(threat, {}).get('experiments', {}).get(str(position), {})
                return record.get('state') == 'done' and all(
                    record.get('models', {}).get(model, {}).get('state') == 'done' for model in models)
            if complete_plan and all(verified(threat, position) for threat in threats for position in range(1, runs + 1)):
                cohorts[cohort] = 'done'
            elif published_for_allocator or any(record.get('state') in {'done', 'running', 'resume', 'stopped'} for record in records):
                cohorts[cohort] = 'resume'
            else:
                cohorts[cohort] = 'none' if complete_plan else 'unobserved'
    return report


class _OpaqueCheckpointObject:
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        pass


class _CheckpointMetadataReader(pickle._Unpickler):
    def find_class(self, module, name):
        if (module, name) == ('collections', 'OrderedDict'):
            return OrderedDict
        return _OpaqueCheckpointObject

    def get_extension(self, code):
        raise pickle.UnpicklingError('Checkpoint extensions are not supported')


def completed_runner_models(data, position, expected):
    stream = io.BytesIO(data)
    saved = _CheckpointMetadataReader(stream).load()
    if (stream.read(1) or not isinstance(saved, dict) or saved.get('is_complete') is not True
            or saved.get('id') != position or type(saved.get('frames_count')) is not int
            or saved['frames_count'] <= 0 or not isinstance(saved.get('results'), dict)):
        raise ValueError('Expected a complete runner checkpoint for the indexed position')
    return {name for name in expected if isinstance(record := saved['results'].get(name), dict)
            and not record.get('error') and record.get('frames_count') == saved['frames_count']
            and 'final_reward' in record}


def cohort_progress(document, report, snapshots, runner_models=None):
    plan = document.get('plan') or {}
    if not all(plan.get(key) for key in ('allocators', 'cohorts', 'threats', 'models', 'runs')):
        return None
    allocators, cohorts, threats, models, runs = (plan[key] for key in ('allocators', 'cohorts', 'threats', 'models', 'runs'))
    if type(runs) is not int or runs < 1:
        raise ValueError('Invalid planned run count')
    done_allocators = done_cohorts = done_experiments = done_models = 0
    for allocator in allocators:
        scope = document.get('allocators', {}).get(allocator, {}).get('cohorts', {})
        states = report.get(allocator, {}).get('cohorts', {})
        for cohort in cohorts:
            done_cohorts += states.get(cohort) == 'done'
            observed = scope.get(cohort, {}).get('threats', {})
            published = snapshots.get(cohort, {})
            for threat in threats:
                positions = observed.get(threat, {}).get('experiments', {})
                for position in range(1, runs + 1):
                    saved = positions.get(str(position), {})
                    checkpoint = published.get(f'{allocator}/{threat}/{position}', {})
                    done_experiments += saved.get('state') == 'done' or bool(checkpoint.get('state'))
                    model_files = {name.split('(', 1)[0] for name in checkpoint.get('models', {})}
                    model_files.update((runner_models or {}).get((cohort, allocator, threat, position), ()))
                    done_models += sum(saved.get('models', {}).get(model, {}).get('state') == 'done'
                                       or model in model_files for model in models)
        done_allocators += all(states.get(cohort) == 'done' for cohort in cohorts)
    cohort_count = len(allocators) * len(cohorts)
    experiment_count = cohort_count * len(threats) * runs
    return {key: dict(completed=completed, expected=expected) for key, completed, expected in (
        ('allocators', done_allocators, len(allocators)), ('cohorts', done_cohorts, cohort_count),
        ('experiments', done_experiments, experiment_count), ('models', done_models, experiment_count * len(models)))}


def reconcile_index(store, cohort_store, *, pipeline=None, apply=False):
    head = store.api('git/ref/heads/main')['object']['sha']
    saved = store.api('contents/index.json?ref=' + head)
    index = json.loads(base64.b64decode(saved['content']))
    cohort_index = cohort_store.api('contents/index.json?ref=main')
    cohort_pipelines = json.loads(base64.b64decode(cohort_index['content']))['pipelines']

    def reconcile(item):
        identity, entry = item
        pin = entry['version']
        if not re.fullmatch(r'[a-f0-9]{40}', pin):
            raise ValueError('Invalid workflow pin')
        payload = store.api('contents/workflow.json?ref=' + pin)
        document = json.loads(base64.b64decode(payload['content']))
        if document.get('pipeline') != identity:
            raise ValueError('Workflow identity differs: ' + identity)
        key = 'pipeline-' + identity.split('_')[1]
        cohort_entry = cohort_pipelines.get(key, {})
        snapshots = {}
        runner_models = {}
        reader = None
        for cohort, reference in cohort_entry.get('cohorts', {}).items():
            commit, tag = reference['commit'], reference.get('tag')
            if not tag:
                continue
            if not re.fullmatch(r'[a-f0-9]{40}', commit) or cohort_store.api('git/ref/tags/' + tag)['object']['sha'] != commit:
                raise ValueError('Cohort tag does not match its pinned commit')
            payload = cohort_store.api('contents/run.json?ref=' + commit)
            snapshot = json.loads(base64.b64decode(payload['content']))
            if (snapshot['pipeline'], snapshot['execution'], snapshot['cohort']) != (key, cohort_entry['execution'], cohort):
                raise ValueError('Cohort snapshot identity differs')
            snapshots[cohort] = snapshot['experiments']
            plan = document.get('plan') or {}
            models = set(plan.get('models') or ())
            for experiment, record in snapshot['experiments'].items():
                allocator, threat, position_text = experiment.split('/')
                position = int(position_text)
                reference = record.get('state')
                if (not reference or not models or allocator not in (plan.get('allocators') or ())
                        or cohort not in (plan.get('cohorts') or ()) or threat not in (plan.get('threats') or ())
                        or not 1 <= position <= plan['runs']):
                    continue
                saved = (document.get('allocators', {}).get(allocator, {}).get('cohorts', {})
                         .get(cohort, {}).get('threats', {}).get(threat, {}).get('experiments', {})
                         .get(position_text, {}))
                known = {name for name in models if saved.get('models', {}).get(name, {}).get('state') == 'done'}
                known.update(name.split('(', 1)[0] for name in record.get('models', {}))
                if models <= known:
                    continue
                if not 0 < reference['size'] <= 50 * 1024**2:
                    raise ValueError('Indexed runner checkpoint has an invalid size')
                if reader is None:
                    from p155_github_checkpoint_store import GitHubCheckpointStore
                    reader = GitHubCheckpointStore(cohort_store.repository)
                data = reader.read(commit, reference['path'], reference['size'], reference['sha256'])
                runner_models[cohort, allocator, threat, position] = completed_runner_models(data, position, models)
        previous = entry.get('allocators', {})
        report = reconcile_cohort_report(document, previous, snapshots)
        counts = sum(len(value['cohorts']) for value in report.values())
        progress = cohort_progress(document, report, snapshots, runner_models)
        changed = report != previous or (progress is not None and entry.get('progress') != progress)
        if report != previous:
            entry['allocators'] = report
        if progress is not None:
            entry['progress'] = progress
        return identity, counts, changed

    with ThreadPoolExecutor(max_workers=4) as workers:
        selected = index.items() if pipeline is None else [(pipeline, index[pipeline])]
        results = list(workers.map(reconcile, selected))
    if apply and any(changed for _, _, changed in results):
        store.api('contents/index.json', {
            'message': 'Reconcile allocator and cohort reports from pinned workflows',
            'sha': saved['sha'], 'branch': 'main',
            'content': base64.b64encode(json.dumps(index, sort_keys=True).encode()).decode(),
        }, method='PUT')
    return results


def publish_cohort_event(store, event):
    pipeline = event['pipeline']
    if not re.fullmatch(r'Pipeline_[1-9][0-9]*', pipeline):
        raise ValueError('A registered pipeline ID is required')
    runner = event['runner']
    if not re.fullmatch(r'[a-f0-9]{32}', runner) or event['heartbeatKey'] != f'{pipeline}/{runner}':
        raise ValueError('Heartbeat key must match the pipeline and runner')
    for attempt in range(4):
        head = store.api('git/ref/heads/main')['object']['sha']
        saved = store.api('contents/index.json?ref=' + head)
        index = json.loads(base64.b64decode(saved['content']))
        entry = index[pipeline]
        runtime = entry.get('runnerStatus') or {}
        owner = runtime.get('heartbeatKey')
        if owner != event['heartbeatKey'] and runtime.get('state') == 'running':
            raise RuntimeError('Another execution owns the running workflow entry')
        if owner == event['heartbeatKey'] and runtime.get('sequence', -1) >= event['sequence']:
            return
        for allocator, cohort, state in event['cohorts']:
            report = entry.setdefault('allocators', {}).setdefault(allocator, {}).setdefault('cohorts', {})
            if report.get(cohort) != 'done' or state == 'done':
                report[cohort] = state
        entry['runnerStatus'] = {key: value for key, value in event.items() if key != 'cohorts'}
        payload = json.dumps(index, sort_keys=True, allow_nan=False).encode()
        try:
            store.api('contents/index.json', {
                'message': 'Report ' + pipeline + ' runner status',
                'sha': saved['sha'],
                'branch': 'main',
                'content': base64.b64encode(payload).decode(),
            }, method='PUT')
            return
        except RuntimeError:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


class BackgroundWorkflowStatus:
    def __init__(self, store, pipeline, execution, *, heartbeat_interval=60):
        self.store = store
        self.pipeline = pipeline
        self.execution = execution
        self.runner = uuid4().hex
        self.sequence = 0
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='tae-workflow-status')
        self.active = None
        self.completed = None
        self.incomplete = False
        self.heartbeat_interval = heartbeat_interval
        self.lock = RLock()
        self.timer = None
        self.latest = None
        self.pending = None
        self.closed = False
        self.changes = {}

    @classmethod
    def for_pipeline(cls, store, number):
        return cls(store, f'Pipeline_{number}', uuid4().hex)

    def __enter__(self):
        return self

    def start(self, allocator, cohort):
        if self.active == (allocator, cohort):
            return
        if self.active is not None and self.completed is None:
            self.incomplete = True
            self.report(*self.active, state='stopped')
        self.report(allocator, cohort, completed=self.completed)
        self.completed = None
        self.active = (allocator, cohort)

    def finish_cohort(self, *, complete):
        if complete:
            self.completed = self.active
        else:
            self.incomplete = True
            self.report(*self.active, state='stopped')

    def __exit__(self, error_type, error, traceback):
        self.finish_run(success=error is None)

    def finish_run(self, *, success):
        if self.active:
            final = 'done' if success and not self.incomplete and self.completed else 'stopped'
            self.report(*self.active, state=final, completed=self.completed)
        self.close()

    def start_scope(self, config):
        self.start(str(config.allocator), f"S{float(config.scale):g}{'Tb' if config.base_capacity else 'T'}")

    def confirm_saved_cohort(self, document, *, threats, runs, models):
        allocator, cohort = self.active
        saved = document.get('allocators', {}).get(allocator, {}).get('cohorts', {}).get(cohort, {})
        for threat in threats:
            positions = saved.get('threats', {}).get(threat, {}).get('experiments', {})
            for position in range(1, runs + 1):
                experiment = positions.get(str(position), {})
                if experiment.get('state') != 'done' or any(
                        experiment.get('models', {}).get(model, {}).get('state') != 'done' for model in models):
                    return False
        self.finish_cohort(complete=True)
        return True

    def report(self, allocator, cohort, *, state='running', completed=None):
        if state not in {'running', 'done', 'stopped'}:
            raise ValueError('Invalid runner status')
        if state == 'done' and completed != (allocator, cohort):
            raise ValueError('Run completion requires the final completed cohort')
        if completed is not None and state == 'running' and completed == (allocator, cohort):
            raise ValueError('The active cohort cannot also be the completed cohort')
        changes = [] if completed is None else [(*completed, 'done')]
        if state != 'done':
            changes.append((allocator, cohort, state))
        with self.lock:
            self.latest = dict(allocator=allocator, cohort=cohort, state=state)
            if state != 'running' and self.timer:
                self.timer.cancel()
                self.timer = None
            future = self._submit(changes)
            if state == 'running' and self.timer is None:
                self._schedule_heartbeat()
            return future

    def _submit(self, changes):
        for allocator, cohort, state in changes:
            self.changes[allocator, cohort] = state
        self.sequence = max(self.sequence + 1, time.time_ns())
        event = dict(pipeline=self.pipeline, execution=self.execution, sequence=self.sequence,
                     runner=self.runner, heartbeatKey=f'{self.pipeline}/{self.runner}',
                     updated=time.time(), heartbeatTimeout=self.heartbeat_interval * 3,
                     cohorts=[(*scope, state) for scope, state in self.changes.items()], **self.latest)
        self.pending = self.worker.submit(publish_cohort_event, self.store, event)
        self.pending.add_done_callback(self._report_result)
        return self.pending

    def _schedule_heartbeat(self):
        self.timer = Timer(self.heartbeat_interval, self._heartbeat)
        self.timer.daemon = True
        self.timer.start()

    def _heartbeat(self):
        with self.lock:
            if self.closed or self.latest['state'] != 'running':
                return
            if self.pending is None or self.pending.done():
                self._submit([])
            self._schedule_heartbeat()

    @staticmethod
    def _report_result(future):
        if not future.cancelled() and future.exception() is not None:
            print('TAE_Workflow status publication pending:', future.exception(), flush=True)

    def close(self):
        with self.lock:
            self.closed = True
            if self.timer:
                self.timer.cancel()
                self.timer = None
            self.worker.shutdown(wait=False)
