"""Pipeline 155 temporary checkpoint staging with verified remote handoff."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from functools import partial
import os
from pathlib import Path
import pickle
import shutil
import tempfile
import time


class CheckpointPublisher:
    def __init__(self, root, *, limit=2, reserve_bytes=2 * 1024**3):
        if limit < 1 or reserve_bytes < 0:
            raise ValueError('Positive queue limit and nonnegative disk reserve required')
        self.root = Path(root)
        self.outbox = self.root / '.checkpoint-outbox'
        self.outbox.mkdir(mode=0o700, exist_ok=True)
        if self.outbox.is_symlink() or any(self.outbox.iterdir()):
            raise RuntimeError('Backup pending: previous checkpoint batches retained in outbox')
        self.limit, self.reserve_bytes = limit, reserve_bytes
        self.headroom = 0
        self.jobs = []
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='p155-backup')

    def _reap(self):
        self.jobs[:] = [job for job in self.jobs if not job.done() or job.exception() is not None]

    def admit(self):
        while True:
            self._reap()
            enough_space = shutil.disk_usage(self.root).free >= self.reserve_bytes + self.headroom
            if len(self.jobs) < self.limit and enough_space:
                return
            pending = next((job for job in self.jobs if not job.done()), None)
            if pending is None:
                raise RuntimeError('Backup pending: queue or staging disk limit reached')
            try:
                pending.result()
            except Exception:
                pass

    def submit(self, key, paths, operation):
        batch = Path(tempfile.mkdtemp(prefix=key.replace('/', '-') + '-', dir=self.outbox))
        moved = {}
        try:
            for path in paths:
                destination = batch / path.parent.parent.name / path.name
                destination.parent.mkdir(exist_ok=True)
                os.replace(path, destination)
                moved[path] = destination
            self.headroom = max(self.headroom, sum(path.stat().st_size for path in moved.values()))
            self.jobs.append(self.executor.submit(self._publish, batch, moved, operation))
        except Exception:
            (self.root / '.backup-pending').touch(exist_ok=True)
            raise

    def _publish(self, batch, moved, operation):
        try:
            operation(moved)
            for directory in {path.parent for path in moved.values()}:
                directory.rmdir()
            batch.rmdir()
        except Exception:
            (self.root / '.backup-pending').touch(exist_ok=True)
            raise

    def close(self):
        self.executor.shutdown(wait=True)
        self._reap()
        return not self.jobs and not (self.root / '.backup-pending').exists()


class ExperimentArchive:
    def __init__(self, config, run, cache, legacy_search=None, *, sleep=time.sleep,
                 publisher=None, drive_factory=None):
        self.config, self.run, self.cache = config, run, cache
        self.manager = config.backup_mgr
        self.root = Path(config.dir).resolve(strict=True)
        self.legacy_search, self.sleep = legacy_search, sleep
        self.publisher, self.drive_factory = publisher, drive_factory
        self.remote_manager = None

    def key(self, position):
        return f'{self.config.allocator}/{self.config.attack_type}/{position}'

    def select(self, position):
        key = self.key(position)
        self.manager.github_checkpoint_search = (
            self.run.checkpoint_search(key, self.cache) if key in self.run.experiments
            else self.legacy_search)

    def has_runner_checkpoint(self, position):
        loader = self.manager.github_checkpoint_search
        registry = getattr(loader, 'git_backup_registry', {})
        prefix = f'QuantumExperimentRunner_{position}_'
        attack = {'none': 'Baseline (None)_No', 'stochastic': 'Stochastic_Random',
                  'markov': 'Adversarial_Markov', 'adaptive': 'Adversarial_Adaptive',
                  'onlineadaptive': 'Adversarial_OnlineAdaptive'}.get(self.config.attack_type)
        return attack is not None and any(
            name.startswith(prefix) and f'-{self.config.allocator}_{attack}-' in name
            for name in registry.get('framework_state', {}))

    def _files(self, component):
        directory = self.root / component / self.config.day_str
        if directory.resolve() != directory:
            raise RuntimeError('Checkpoint staging must not traverse symbolic links')
        return {path: self._stamp(path) for path in directory.glob('*.pkl')
                if not path.is_symlink() and path.is_file()}

    @staticmethod
    def _stamp(path):
        info = path.stat()
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns

    @staticmethod
    def _digest(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()

    def begin(self, position):
        if self.publisher is not None:
            self.publisher.admit()
        if self.key(position) in self.run.experiments:
            raise RuntimeError('Published experiment must be restored before execution')
        self.select(position)
        self.before = {component: self._files(component) for component in ('framework_state', 'model_state')}

    def _publish_drive(self, key, path, digest):
        from googleapiclient.http import MediaFileUpload
        manager = self.manager
        if self.drive_factory is not None:
            if self.remote_manager is None:
                self.remote_manager = copy(self.manager)
                self.remote_manager.drive = self.drive_factory()
            manager = self.remote_manager
        drive_id = self.config.pipeline_storage['driveId']
        if not manager.remote_available or manager.drive_folder_id != drive_id:
            raise RuntimeError('The bound evaluator Drive is unavailable')
        parent = drive_id
        for name in ('quantum_data_lake', 'framework_state', self.config.day_str,
                     self.run.identity['cohort'] + '-' + key.replace('/', '-')):
            parent = manager._ensure_drive_folder(name, parent)
            if not parent:
                raise RuntimeError('Drive evaluator destination unavailable')
        files = manager.drive.files()
        query = f"'{parent}' in parents and name = '{path.name}' and trashed = false"
        matches = files.list(q=query, corpora='drive', driveId=drive_id,
            supportsAllDrives=True, includeItemsFromAllDrives=True, fields='nextPageToken,files(id)').execute()
        if matches.get('nextPageToken') or len(matches.get('files', [])) > 1:
            raise RuntimeError('Ambiguous Drive evaluator checkpoint')
        existing = matches.get('files', [])
        if existing:
            file_id = existing[0]['id']
        else:
            file_id = files.create(body={'name': path.name, 'parents': [parent]},
                media_body=MediaFileUpload(str(path), resumable=True),
                supportsAllDrives=True, fields='id').execute()['id']
        reference = dict(fileId=file_id, driveId=drive_id, name=path.name,
                         size=path.stat().st_size, sha256=digest, parentId=parent)
        self._verify_drive(reference, manager)
        return reference

    def _verify_drive(self, reference, manager=None):
        remote = (manager or self.manager).drive.files().get(fileId=reference['fileId'], supportsAllDrives=True,
            fields='id,name,size,sha256Checksum,driveId,parents,trashed').execute()
        if (remote.get('driveId') != self.config.pipeline_storage['driveId']
                or remote.get('driveId') != reference['driveId']
                or remote.get('id') != reference['fileId'] or remote.get('name') != reference['name']
                or remote.get('parents') != [reference['parentId']] or remote.get('trashed') is not False
                or int(remote.get('size', -1)) != reference['size']
                or remote.get('sha256Checksum') != reference['sha256']):
            raise RuntimeError('Drive evaluator checksum or identity differs')

    def _retry(self, operation):
        for attempt in range(1, 5):
            try:
                return operation()
            except Exception as error:
                if attempt == 4:
                    raise RuntimeError('Remote checkpoint handoff failed after three retries; staging retained') from error
                print(f'Checkpoint handoff attempt {attempt}/4 failed; retrying with staging intact.')
                self.sleep(2 ** attempt)

    def verify_saved(self, position):
        key = self.key(position)
        def verify():
            if self.publisher is None:
                self.run.publish()
            pinned = self.run.store.open_published(**self.run.identity)
            record = pinned.experiments[key]
            self._verify_drive(record['evaluator'])
            references = [record['state'], *record['models'].values()]
            for reference in references:
                if not reference['path'].startswith(f'experiments/{key}/'):
                    raise RuntimeError('Pinned checkpoint belongs to a different experiment')
                self.run.store.read(pinned.head, reference['path'], reference['size'], reference['sha256'])
            return pinned
        return self._retry(verify)

    def finish(self, position, results, evaluator_checkpoint):
        expected = set(self.config.models)
        outcomes = results.get('results', {})
        if set(outcomes) != expected or any(outcome.get('error') or 'final_reward' not in outcome
                                             for outcome in outcomes.values()):
            raise RuntimeError('Incomplete experiment; temporary checkpoints retained')
        changed = {component: {path: stamp for path, stamp in self._files(component).items()
                               if self.before[component].get(path) != stamp}
                   for component in self.before}
        evaluator = Path(evaluator_checkpoint) if evaluator_checkpoint else None
        if evaluator is not None and not evaluator.is_symlink():
            evaluator = evaluator.resolve()
        runners = [path for path in changed['framework_state']
                   if path.name.startswith(f'QuantumExperimentRunner_{position}_')]
        models = {path.name: path for path in changed['model_state']}
        if (evaluator not in changed['framework_state'] or not evaluator.name.startswith('MultiRunEvaluator_')
                or len(runners) != 1):
            raise RuntimeError('Missing exact experiment checkpoint writes; temporary files retained')
        checkpoint = runners[0]
        if not expected.issubset({name.split('(', 1)[0] for name in models}):
            self.verify_runner_results(checkpoint, position, outcomes, results.get('winner'))
        paths = [checkpoint, *models.values(), evaluator]
        key = self.key(position)
        if self.publisher is None:
            self._handoff(key, checkpoint, models, evaluator)
        else:
            self.publisher.submit(key, paths, partial(self._handoff_staged, key, checkpoint, models, evaluator))
        for path in paths:
            component = path.parent.parent.name
            for registry in (self.config.backup_registry, self.manager.backup_registry, self.manager.new_entries):
                entries = registry.get(component, {})
                if entries.get(path.name) == str(path):
                    entries.pop(path.name)

    def _handoff_staged(self, key, checkpoint, models, evaluator, moved):
        self._handoff(key, moved[checkpoint], {name: moved[path] for name, path in models.items()},
                      moved[evaluator])

    @staticmethod
    def verify_runner_results(checkpoint, position, outcomes, winner):
        with checkpoint.open('rb') as stream:
            saved = pickle.load(stream)
            if stream.read(1):
                raise ValueError('Unexpected trailing runner checkpoint bytes')
        stored = saved.get('results', {})
        frames = saved.get('frames_count')
        if (saved.get('is_complete') is not True or saved.get('id') != position
                or saved.get('winner') != winner or set(stored) != set(outcomes)
                or type(frames) is not int or frames <= 0):
            raise RuntimeError('Incomplete saved runner; temporary files retained')
        for model, result in outcomes.items():
            record = stored[model]
            history = record.get('model_results', {}).get('reward_list', ())
            if (record.get('error') or record.get('frames_count') != frames or len(history) != frames
                    or 'final_reward' not in record or any(record.get(key) != result.get(key)
                        for key in ('final_reward', 'frames_count', 'seed'))):
                raise RuntimeError(f'Incomplete saved runner history for {model}; temporary files retained')

    def _handoff(self, key, checkpoint, models, evaluator, *, log=None):
        paths = [checkpoint, *models.values(), evaluator]
        stamps = {path: self._stamp(path) for path in paths}
        digests = {path: self._digest(path) for path in paths}
        def publish():
            drive = self._publish_drive(key, evaluator, digests[evaluator])
            self.run.save_finished(key, checkpoint, models=models, evaluator=drive)
            self.run.publish()
            pinned = self.run.store.open_published(**self.run.identity)
            record = pinned.experiments[key]
            if record.get('evaluator') != drive:
                raise RuntimeError('Pinned evaluator reference differs')
            for path, reference in [(checkpoint, record['state']),
                                    *((path, record['models'][name]) for name, path in models.items())]:
                if reference['sha256'] != digests[path] or reference['size'] != stamps[path][2]:
                    raise RuntimeError('Pinned Git checkpoint reference differs')
                self.run.store.read(pinned.head, reference['path'], reference['size'], reference['sha256'])
        self._retry(publish)
        if log is not None:
            try:
                def publish_log():
                    self.run.save_finished(key, checkpoint, log=log)
                    self.run.publish()
                self._retry(publish_log)
            except Exception as error:
                print(f'Log backup pending for {key}: {error.__cause__ or error!r}', flush=True)
        if any(path.is_symlink() or self._stamp(path) != stamps[path]
               or self._digest(path) != digests[path] for path in paths):
            raise RuntimeError('Temporary checkpoints changed during publication; no files deleted')
        for path in paths:
            path.unlink()
