"""Fresh-process storage adapter around the existing, pinned native worker."""
import argparse
import base64
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import importlib.util
import importlib
import json
import os
from pathlib import Path
import sys
import io
from contextlib import redirect_stderr
from types import SimpleNamespace


def load(path, name, digest=None):
    path = Path(path)
    if path.is_symlink() or digest is not None and sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Pinned execution adapter source changed')
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def model_log_label(runner, model):
    return f'{runner.configs.allocator}][{runner.environment.attack}][{model}'


class WorkerLogOutput:
    def __init__(self, runner):
        self.runner = runner

    def forward(self, original, path, model, offsets):
        captured = io.StringIO()
        with redirect_stderr(captured):
            changed = original(path, model, offsets)
        for line in captured.getvalue().splitlines():
            prefix = '[' + model + '] '
            body = line.removeprefix(prefix)
            if 'Starting ' in body and 'in sequence...' in body:
                body = body.replace('in sequence...', 'in parallel...')
            message = body.strip()
            noise = ('PyTorch version:', 'NumPy version:', 'Using device:',
                'Matplotlib is building the font cache;', '→ Skipping local cache',
                '→ Attempting to fetch registry', '→ Filesystem scan found',
                '🔍 SCANNING LOCAL FILES', 'Parameters: load_to_drive=',
                '📂 Checking DRIVE mode:', '📂 Checking LOCAL mode:',
                '✅ Path exists, starting walk', '🚶 Walking directory tree:',
                '📊 Processed ', '📦 BUILDING FINAL REGISTRY', 'Components found:',
                '✅ SCAN COMPLETE', 'Modes scanned:', 'Total files in registry:',
                '⚠️ Drive NOT available -> cannot fetch registry', '✓ Drive registry loaded')
            if message.startswith(noise) or any(marker in message for marker in
                    ('GET LOCAL REGISTRY ===', 'BUILD LOCAL REGISTRY ===',
                     'GET DRIVE REGISTRY ===', 'BUILD REGISTRY END ===',
                     'REGISTRY BUILD COMPLETE ===', 'FETCH FROM DRIVE START ===')):
                continue
            print(f'[{self.runner.configs.allocator}] [{self.runner.environment.attack}] '
                f'[{model}] {body}', file=sys.stderr, flush=True)
        return changed


@contextmanager
def experiment_log_output(adapter):
    original_isolated, original_forward = adapter.run_isolated, adapter.forward_log

    def displayed(runner, *args, **kwargs):
        output = WorkerLogOutput(runner)
        adapter.forward_log = lambda path, model, offsets: output.forward(
            original_forward, path, model, offsets)
        try:
            result = original_isolated(runner, *args, **kwargs)
        finally:
            adapter.forward_log = original_forward
        display_experiment_result(runner, result)
        return result

    adapter.run_isolated = displayed
    try:
        yield
    finally:
        adapter.run_isolated, adapter.forward_log = original_isolated, original_forward


def display_model_result(runner, model):
    result = runner.results[model]
    attempts = result.get('failed_attempts') or {}
    capacity = int(runner.capacity * runner.configs.scale)
    efficiency = result.get('efficiency')
    efficiency_text = 'N/A' if efficiency is None else f'{efficiency:05.1f}%'
    print(f"\tEXP {runner.id} {model.upper():<20}: Reward={result['final_reward']:07.2f}, "
        f"Efficiency={efficiency_text} "
        f"[Retries={attempts.get('total', 0)}, Failed={attempts.get('failed', 0)}, "
        f"< Threshold={attempts.get('under_threshold', 0)}, SCapacity={capacity}, "
        f"Threshold={attempts.get('threshold', 0)}]", flush=True)


def display_experiment_result(runner, result):
    winner = result.get('winner')
    if not winner:
        return
    print("\n\t📊 EXPERIMENT RESULTS SUMMARY", flush=True)
    print("\t" + "=" * 120, flush=True)
    for model in result['results']:
        if model != 'Oracle':
            display_model_result(runner, model)
    print("\t" + "=" * 120, flush=True)
    gap = result['results'][winner].get('gap', 100)
    gap_text = 'N/A' if gap is None else f'{gap:05.1f}%'
    capacity = int(runner.capacity * runner.configs.scale)
    print(f"\t-->🏆 EXP{runner.id} Winner:{winner:<20}(Gap:{gap_text}) "
        f"[Env:{runner.environment}, Attack:{runner.environment.attack} "
        f"X Rate:{runner.environment.attack_rate}, Frames:{runner.environment.frame_length}, "
        f"SCapacity={capacity}, Alloc={runner.configs.allocator}]", flush=True)


def drive_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    path = os.environ.get('DAQR_PIPELINE_CREATION_CREDENTIALS')
    if path is None:
        path = Path(os.environ.get('CLOUDSDK_CONFIG', Path.home() / '.config/gcloud')) / 'application_default_credentials.json'
    document = json.loads(Path(path).expanduser().read_bytes())
    if document.get('type') != 'authorized_user':
        raise ValueError('Reuse the existing authorized user Drive client')
    credentials = Credentials.from_authorized_user_info(document, scopes=['https://www.googleapis.com/auth/drive'])
    if not credentials.valid:
        credentials.refresh(Request())
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)


def resolver(receipts):
    def resolve(reference):
        receipt = receipts.get(reference['provider_id'])
        if receipt is None:
            return deepcopy(reference)
        if (receipt['state'] != 'moved' or receipt['sha256'] != reference['content_sha256']
                or receipt['bytes'] != reference['byte_length']
                or receipt.get('fileId') != reference['provider_id']
                or Path(receipt['path']).name != reference['original_filename']):
            raise ValueError('Pinned relocation receipt differs from original source')
        return dict(reference, drive_root_id=receipt['driveId'], path=receipt['path'],
            storage_version=str(receipt['storageVersion']), relocationReceipt=deepcopy(receipt))
    return resolve


class NativeStatusFeed:
    def __init__(self, path):
        self.path = Path(path)
        self.packet = None
        self.models = {}
        self.locations = {}
        self.last = None
        self.last_error = None

    def update(self, queue, state, extra):
        groups = {}
        for name, group in queue['sets'].items():
            rows = {}
            for threat, row in group['attacks'].items():
                identity = row.get('runnerObjectId')
                rows[threat] = dict(state=row['state'], context=dict(run=row['context']['run']),
                    runnerObjectId=identity)
                if identity:
                    self.locations[identity] = (name, threat)
            groups[name] = dict(attacks=rows, finalizationRefs=dict.fromkeys(group.get('finalizationRefs', {}), True))
        self.packet = dict(pipelineId=155, state=state, extra=deepcopy(extra), queue=dict(
            pipelineId=queue['pipelineId'], testOnly=queue['testOnly'], executionId=queue['executionId'], sets=groups))
        self.publish()

    def model(self, identity, model, state):
        if self.packet is None or identity not in self.locations:
            return
        cohort, threat = self.locations[identity]
        self.models.setdefault(identity, {})[model] = state
        self.packet['extra'] = dict(currentSet=cohort, currentAttack=threat,
            currentObjectId=identity, phase='model-' + state)
        self.publish()

    def publish(self):
        pending = self.path.with_suffix('.' + str(os.getpid()) + '.pending')
        try:
            raw = json.dumps(dict(self.packet, modelStates=self.models), sort_keys=True).encode()
            if raw == self.last:
                return
            pending.write_bytes(raw)
            pending.chmod(0o600)
            pending.replace(self.path)
            self.last = raw
            self.last_error = None
        except (OSError, TypeError, ValueError) as error:
            message = str(error)
            if message != self.last_error:
                print('Live status publication pending; native execution continues:', message, file=sys.stderr)
                self.last_error = message


@contextmanager
def authorized_transport(manager_type, service, root):
    initialize = manager_type.__init__
    persist = manager_type.persist_artifact

    def init(manager, date_str, config_dir, verbose=False, local_only=False):
        initialize(manager, date_str, config_dir, verbose=verbose, local_only=True)
        if not local_only:
            manager.drive = service
            manager.local_only = False
            manager.remote_available = True

    def write(manager, *args, **kwargs):
        if manager.drive_folder_id != root:
            raise ValueError('Pipeline 155 cannot write to a historical source Drive')
        return persist(manager, *args, **kwargs)

    manager_type.__init__, manager_type.persist_artifact = init, write
    try:
        yield
    finally:
        manager_type.__init__, manager_type.persist_artifact = initialize, persist


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    os.environ.update(NO_COLOR='1', CLICOLOR='0', TERM='dumb')
    for name in ('GH_FORCE_TTY', 'CLICOLOR_FORCE', 'FORCE_COLOR'):
        os.environ.pop(name, None)
    raw = args.binding.read_bytes()
    if args.binding.is_symlink() or sha256(raw).hexdigest() != args.sha256:
        raise ValueError('Owned exact execution binding required')
    packet = json.loads(raw)
    if packet['pipelineId'] != 155 or packet['targetRuns'] != 9:
        raise ValueError('Pipeline 155 nine-run continuation only')
    worker = load(packet['worker']['path'], '_p155_original_native_worker', packet['worker']['sha256'])
    policy, adapter = worker.bootstrap()
    from tools.automation import run_drive_queue as cli
    from daqr.config.gd_backup_manager import GoogleDriveBackupManager
    support = load(packet['bindingSource']['path'], '_p155_transport', packet['bindingSource']['sha256'])
    pipeline = SimpleNamespace(pipeline_id=155, target_runs=9, settings={'runs': 9},
        storage_binding=packet['storage'], drive_id=packet['storage']['driveId'],
        pipeline_reference=packet['pipelineReference'])
    service = drive_service()
    make_manager = lambda root: support.ContinuationStorageBinding.native_manager(
        GoogleDriveBackupManager, service, args.binding.parent, root, packet['date'])
    writer = make_manager(pipeline.drive_id)
    binding = support.ContinuationStorageBinding(pipeline, writer, make_manager,
        resolve_reference=resolver(packet['relocations']))
    os.environ['DAQR_PIPELINE155_BINDING_WORKER'] = '1'
    source = worker.load(policy.ORIGINAL / 'run_future.py', '_p155_original_reader',
        policy.INPUT_HASHES[policy.ORIGINAL / 'run_future.py'])
    controls = {}
    for name in ('spec', 'workflow'):
        cached = packet['pinnedMetadata'][name]
        raw = base64.b64decode(cached['content'], validate=True)
        if len(raw) > 8 * 1024**2 or sha256(raw).hexdigest() != cached['reference']['sha256']:
            raise ValueError('Cached immutable control bytes differ')
        controls[name] = cli.parse_document(raw)
    spec, workflow = controls['spec'], controls['workflow']
    if (packet['pinnedMetadata']['spec']['reference'] != packet['specRef']
            or packet['pinnedMetadata']['workflow']['reference'] != spec['workflowRef']):
        raise ValueError('Cached control linkage differs')
    worker.validate_spec(spec, workflow, packet['requestId'], policy)
    binding.workflow(workflow)
    if args.preflight:
        print(json.dumps(dict(preflight='PASS', pipelineId=155, targetRuns=9,
            storage=packet['storage'], evaluatorResume=False, scientificWorkersLaunched=0,
            sourceFramesPerNewRun=spec['frames_per_new_run'], sourceLabel=workflow['label'],
            readyForSavedFramePolicy=True,
            readyForFullFrameRun=spec['frames_per_new_run'] is None)))
        return
    notebook = load(packet['notebookSupport']['path'], '_p155_existing_notebook_support',
        packet['notebookSupport']['sha256'])
    notebook.control_cache_module(policy, adapter)
    original_scope = adapter.metadata_scope

    def primed_scope(reference, request_id):
        cache = original_scope(reference, request_id)
        identity = dict(pid=os.getpid(), requestId=request_id, specRef=reference)
        notebook.prime_settings_cache(cache, packet['settingsCache'], identity, adapter)
        return cache

    adapter.metadata_scope = primed_scope
    original_driver, original_managers = cli.DriveQueueDriver, cli.build_drive_managers
    cli.DriveQueueDriver = binding.driver_type(original_driver, GoogleDriveBackupManager)
    cli.build_drive_managers = lambda workflow, factory: dict.fromkeys(support.ROLES, writer)
    feed = NativeStatusFeed(args.binding.parent / 'native-status.json')
    mirror_type = cli.DriverMirror

    class LiveMirror(mirror_type):
        def update(self, queue, state, **extra):
            result = super().update(queue, state, **extra)
            feed.update(queue.document, state, extra)
            return result

    cli.DriverMirror = LiveMirror
    from tools.automation.resume_drive_set import IndexedRunnerStatePort
    start_model = IndexedRunnerStatePort._start_model
    complete_model = IndexedRunnerStatePort._complete_model

    def started(port, model):
        result = start_model(port, model)
        feed.model(port._object_id, model, 'running')
        return result

    def completed(port, object_id, model, runner, checkpoint):
        feed.model(object_id, model, 'done')
        result = complete_model(port, object_id, model, runner, checkpoint)
        return result

    IndexedRunnerStatePort._start_model = started
    IndexedRunnerStatePort._complete_model = completed
    original_run = IndexedRunnerStatePort.run

    def displayed_run(port, *args, **kwargs):
        selected_adapter = port.parallel_adapter or importlib.import_module('process_adapter')
        with experiment_log_output(selected_adapter):
            return original_run(port, *args, **kwargs)

    IndexedRunnerStatePort.run = displayed_run
    try:
        with authorized_transport(GoogleDriveBackupManager, service, pipeline.drive_id):
            worker.native_worker(packet['specRef'], request_id=packet['requestId'],
                access=SimpleNamespace(read_bytes=source.pinned_bytes),
                reexec_argv=[sys.executable, '-B', str(Path(__file__).resolve()),
                    '--binding', str(args.binding), '--sha256', args.sha256])
    finally:
        IndexedRunnerStatePort.run = original_run
        IndexedRunnerStatePort._start_model, IndexedRunnerStatePort._complete_model = start_model, complete_model
        cli.DriverMirror, cli.DriveQueueDriver, cli.build_drive_managers = mirror_type, original_driver, original_managers


if __name__ == '__main__':
    main()
