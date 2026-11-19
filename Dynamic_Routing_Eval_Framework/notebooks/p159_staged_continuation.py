"""Notebook-side continuation for the registered Pipeline 159 baseline cohort."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile

from googleapiclient.http import MediaFileUpload

from cohort_run_publication import SharedCohortStore
from p155_remote_archive import ExperimentArchive
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.config.gd_backup_manager import GoogleDriveBackupManager
from daqr.config.tae_workflow import WorkflowStore
from daqr.core.qubit_allocator import QubitAllocator
from daqr.evaluation.allocator_runner import AllocatorRunner
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator


class SharedStagingArchive(ExperimentArchive):
    def _folder(self, parent, name):
        files = self.manager.drive.files()
        drive = self.config.pipeline_storage['driveId']
        query = f"'{parent}' in parents and name='{name}' and trashed=false"
        result = files.list(q=query, corpora='drive', driveId=drive, supportsAllDrives=True,
            includeItemsFromAllDrives=True, fields='nextPageToken,files(id,mimeType)').execute(num_retries=3)
        found = result['files']
        if result.get('nextPageToken') or len(found) > 1:
            raise ValueError('Ambiguous staging folder')
        mime = 'application/vnd.google-apps.folder'
        if found:
            if found[0]['mimeType'] != mime:
                raise ValueError('Expected a staging folder')
            return found[0]['id']
        return files.create(body=dict(name=name, parents=[parent], mimeType=mime),
                            supportsAllDrives=True, fields='id').execute()['id']

    def evaluator_folder(self, execution):
        parent = self.config.pipeline_storage['driveId']
        for name in ('Pipeline_159', execution, 'framework_state'):
            parent = self._folder(parent, name)
        return parent

    def _publish_drive(self, key, path, digest):
        cohort = self.run.identity['cohort'].replace('.', '-')
        execution = self.run.identity['execution'] + '-' + cohort + '-' + key.replace('/', '-')
        parent = self.evaluator_folder(execution)
        root = self.config.pipeline_storage['driveId']
        files = self.manager.drive.files()
        response = files.list(q=f"'{parent}' in parents and name='{path.name}' and trashed=false",
            corpora='drive', driveId=root, supportsAllDrives=True, includeItemsFromAllDrives=True,
            fields='nextPageToken,files(id)').execute(num_retries=3)
        found = response['files']
        if response.get('nextPageToken') or len(found) > 1:
            raise ValueError('Ambiguous evaluator checkpoint')
        identity = found[0]['id'] if found else files.create(body=dict(name=path.name, parents=[parent]),
            media_body=MediaFileUpload(str(path), resumable=True), supportsAllDrives=True,
            fields='id').execute()['id']
        reference = dict(fileId=identity, driveId=root, name=path.name, size=path.stat().st_size,
                         sha256=digest, parentId=parent)
        self._verify_drive(reference)
        return reference

    def _handoff(self, key, checkpoint, models, evaluator, *, log=None):
        try:
            self.log_stream.flush()
        except OSError as error:
            print(f'Log backup pending for {key}: {error!r}', flush=True)
            return super()._handoff(key, checkpoint, models, evaluator)
        return super()._handoff(key, checkpoint, models, evaluator, log=self.log_path)


class NotebookLog:
    def __init__(self, notebook, file):
        self.notebook, self.file = notebook, file

    def write(self, content):
        self.notebook.write(content)
        self.file.write(content)
        self.flush()
        return len(content)

    def flush(self):
        self.notebook.flush()
        self.file.flush()


def run_continuation():
    assert Path('/.dockerenv').exists()
    assert int(Path('/sys/fs/cgroup/memory.max').read_text()) >= 12 * 1024**3
    quota, period = map(int, Path('/sys/fs/cgroup/cpu.max').read_text().split())
    assert quota == 8 * period
    os.environ.update(DAQR_MODEL_MAX_WORKERS='4', DAQR_RESUME_ALLOW_DRIVE_DOWNLOADS='0')
    launch = json.loads(Path('/run/tae/workflow-launch.json').read_bytes())
    assert launch['pipeline'] == 'Pipeline_159'
    execution = '3a1ba82a-1450-4e17-816d-917568e19736'
    store = SharedCohortStore()
    pinned = store.open_published('pipeline-159', execution, 'S1.5T')
    assert set(pinned.experiments) == {f'Default/none/{position}' for position in range(1, 8)}
    models = launch['settings']['models']
    assert set(models) == {'Oracle', 'GNeuralUCB', 'EXPNeuralUCB', 'CPursuitNeuralUCB', 'iCPursuitNeuralUCB'}
    for position in range(1, 8):
        state = pickle.loads(pinned.read(f'Default/none/{position}', 'state'))
        assert state['id'] == position and state['is_complete'] and set(state['results']) == set(models)
    root = Path(tempfile.mkdtemp(prefix='pipeline-159-staging-'))
    binding = dict(pipelineId='159', driveId='0AE6N-7UYJfURUk9PVA')
    drive = GoogleDriveBackupManager.pipeline_creation_drive_service()
    assert drive.drives().get(driveId=binding['driveId'], fields='name').execute()['name'] == 'TAE_Temporary_Staging'
    config = ExperimentConfiguration(runs=10, allocator=QubitAllocator(), scenarios={'none': 'none'}, attack_type='none',
        models=models, scale=1.5, base_capacity=False, attack_intensity=0.25, suffix='S1.5T',
        resume=False, use_last_backup=False, overwrite=False, pipeline_storage=binding,
        staging_dir=root, drive_service=drive)
    config.resume_allow_drive_downloads = False
    config.remote_experiment_archive = True
    run = store.open_run('pipeline-159', execution, 'S1.5T')
    assert run.head == pinned.head
    archive = SharedStagingArchive(config, run, root)
    source = archive.evaluator_folder(execution)
    result = drive.files().list(q=f"'{source}' in parents and trashed=false", corpora='drive',
        driveId=binding['driveId'], supportsAllDrives=True, includeItemsFromAllDrives=True,
        fields='nextPageToken,files(id,name,size,sha256Checksum)').execute()
    assert not result.get('nextPageToken')
    reference, = [item for item in result['files'] if item['sha256Checksum'] ==
                 '2b01589aa647902373172f0f28228c1cc951e60391fa7588d86f7862723bdfbe']
    saved = drive.files().get_media(fileId=reference['id'], supportsAllDrives=True).execute(num_retries=3)
    assert len(saved) == int(reference['size']) and hashlib.sha256(saved).hexdigest() == reference['sha256Checksum']
    checkpoint = pickle.load(io.BytesIO(saved))
    positions = checkpoint['env_experiments']['none']
    assert set(positions) == set(range(1, 8)) and all(set(item['results']) == set(models) for item in positions.values())
    evaluator = MultiRunEvaluator(configs=config, base_frames=4000, frame_step=2000, base_seed=12345, attack_type='none')
    evaluator.env_experiments = {'none': positions}
    evaluator.runner_qubit_caps = checkpoint['runner_qubit_caps']
    evaluator._experiment_archive = archive
    archive.log_path = Path('/tmp/pipeline-notebooks/Docker_Pipeline_10_Runs.live.log')
    with archive.log_path.open('w', encoding='utf-8') as log:
        archive.log_stream = log
        with contextlib.redirect_stdout(NotebookLog(sys.stdout, log)):
            print('DOCKER PIPELINE: Default S1.5T positions=10 frames=4000+2000')
            print('Verified completed baseline positions: [1, 2, 3, 4, 5, 6, 7]')
            print('Starting only experiment 8 with four model workers')
            evaluator.run_experiment(exp_no=7)
            print('Experiment 8 published to Git and Shared Drive staging.')


def continue_after_eight():
    execution = '3a1ba82a-1450-4e17-816d-917568e19736'
    store = SharedCohortStore()
    pinned = store.open_published('pipeline-159', execution, 'S1.5T')
    key = 'Default/none/8'
    finished = pinned.experiments[key]
    completed_runner = pickle.loads(pinned.read(key, 'state'))
    assert completed_runner['id'] == 8 and completed_runner['is_complete']
    assert completed_runner['frames_count'] == 18000 and pinned.read(key, 'log')
    for reference in finished.get('models', {}).values():
        store.read(pinned.head, reference['path'], reference['size'], reference['sha256'])
    _, _, workflow = WorkflowStore().load('Pipeline_159')
    settings = workflow['settings']
    models = settings['models']
    assert set(completed_runner['results']) == set(models)
    assert settings['runs'] == 10 and settings['base_frames'] == 4000 and settings['frame_step'] == 2000
    binding = dict(pipelineId='159', driveId='0AE6N-7UYJfURUk9PVA')
    drive = GoogleDriveBackupManager.pipeline_creation_drive_service()
    root = Path(tempfile.mkdtemp(prefix='pipeline-159-continuation-'))
    evaluator_path = finished['evaluator']
    observed = drive.files().get(fileId=evaluator_path['fileId'], supportsAllDrives=True,
        fields='id,name,driveId,parents,size,sha256Checksum,trashed').execute()
    assert observed == dict(id=evaluator_path['fileId'], name=evaluator_path['name'],
        driveId=binding['driveId'], parents=[evaluator_path['parentId']], size=str(evaluator_path['size']),
        sha256Checksum=evaluator_path['sha256'], trashed=False)
    print('Experiment 8: runner and log verified in pinned Git; evaluator verified on shared staging.', flush=True)
    dashboard_log = Path('/tmp/pipeline-notebooks/Docker_Pipeline_10_Runs.live.log')
    missing = []
    scenarios = {name: name for name in settings['threats']}
    os.environ.update(DAQR_MODEL_MAX_WORKERS='4', DAQR_RESUME_ALLOW_DRIVE_DOWNLOADS='0')
    native_stdout = sys.stdout
    with dashboard_log.open('a', encoding='utf-8') as live:
        for allocator_name in settings['allocators']:
            for base_cap in (False, True):
                for scale in settings['scales']:
                    cohort = f"S{scale:g}{'Tb' if base_cap else 'T'}"
                    if (allocator_name, cohort) == ('Default', 'S1T'):
                        print('Skipping verified completed Default S1T (50 positions).', file=NotebookLog(native_stdout, live))
                        continue
                    run = store.open_run('pipeline-159', execution, cohort)
                    allocator = QubitAllocator() if allocator_name == 'Default' else AllocatorRunner(
                        allocator_name, ['default'], {}, [scale], [10], models, scenarios).create_allocator('default')
                    config = ExperimentConfiguration(runs=10, allocator=allocator, scenarios=scenarios,
                        models=models, scale=scale, base_capacity=base_cap, attack_intensity=settings['attack_intensity'],
                        suffix=cohort, resume=False, use_last_backup=False, overwrite=False, pipeline_storage=binding,
                        staging_dir=root, drive_service=drive)
                    config.resume_allow_drive_downloads = False
                    config.remote_experiment_archive = True
                    evaluator = MultiRunEvaluator(configs=config, base_frames=4000, frame_step=2000,
                                                  base_seed=settings['base_seed'])
                    archive = SharedStagingArchive(config, run, root)
                    evaluator._experiment_archive = archive
                    print(f'DOCKER PIPELINE: {allocator_name} {cohort} positions=10 frames=4000+2000',
                          file=NotebookLog(native_stdout, live))
                    saved_cohort = (workflow.get('allocators', {}).get(allocator_name, {})
                        .get('cohorts', {}).get(cohort, {}))
                    for threat in scenarios:
                        config.attack_type = threat
                        evaluator.env_experiments.setdefault(threat, {})
                        for position in range(1, 11):
                            key = f'{allocator_name}/{threat}/{position}'
                            prior = run.experiments.get(key)
                            if prior is not None:
                                state = pickle.loads(run.read(key, 'state'))
                                assert state['id'] == position and state['is_complete'] and set(state['results']) == set(models)
                                evaluator.env_experiments[threat][position] = dict(
                                    results=state['results'], winner=state['winner'], exp_id=position)
                                print(f'SKIPPING EXPERIMENT {position}: ALREADY COMPLETED AND STORED',
                                      file=NotebookLog(native_stdout, live))
                                continue
                            status = saved_cohort.get('threats', {}).get(threat, {}).get('experiments', {}).get(str(position), {})
                            if status.get('state') == 'done':
                                missing.append(key)
                                print(f'{key}: skipped completed experiment with missing checkpoint',
                                      file=NotebookLog(native_stdout, live))
                                continue
                            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root, prefix='experiment-log-') as experiment_log:
                                archive.log_path, archive.log_stream = Path(experiment_log.name), experiment_log
                                with contextlib.redirect_stdout(NotebookLog(NotebookLog(native_stdout, live), experiment_log)):
                                    evaluator.run_experiment(exp_no=position-1)
                                    print(f'{key}: checkpoint, log, and evaluator verified remotely.')
                    if all(set(evaluator.env_experiments[name]) == set(range(1, 11)) for name in scenarios):
                        evaluator.calculate_scenarios_performance()
                    else:
                        print(f'{allocator_name}/{cohort}: incomplete evidence; evaluation not marked complete.',
                              file=NotebookLog(native_stdout, live))
    if missing:
        print('Completed positions skipped with missing Git artifacts:', missing)
