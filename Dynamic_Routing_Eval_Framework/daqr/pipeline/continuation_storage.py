"""Transport binding for the existing native queue and runner/model state port."""
from contextlib import contextmanager
from copy import deepcopy
from types import MethodType
import os
from pathlib import Path, PurePosixPath
import re


ROLES = ('evaluator', 'runner', 'model')


class ContinuationStorageBinding:
    @staticmethod
    def native_manager(manager_type, service, directory, drive_id, date_str):
        manager = manager_type(date_str, directory, local_only=True)
        manager.drive_folder_id = drive_id
        manager.drive = service
        manager.local_only = False
        manager.remote_available = True
        return manager

    def __init__(self, pipeline, writer, reader_factory, *, resolve_reference=None):
        if (pipeline.pipeline_id != 155 or pipeline.target_runs != 9
                or pipeline.settings.get('runs') != 9 or not pipeline.storage_binding
                or writer.drive_folder_id != pipeline.drive_id or not callable(reader_factory)):
            raise ValueError('Registered Pipeline 155, nine runs and its own Drive writer required')
        self.storage = deepcopy(pipeline.storage_binding)
        self.pipeline_reference = deepcopy(pipeline.pipeline_reference)
        self.writer = writer
        self.reader_factory = reader_factory
        self.resolve_reference = resolve_reference or deepcopy
        self.readers = {pipeline.drive_id: writer}
        self.resolved = {}

    def workflow(self, original):
        if (original.get('pipelineId') != 155 or original.get('targetRuns') != 9
                or not original.get('executionId') or original.get('testOnly') is not False):
            raise ValueError('Original Pipeline 155 production continuation required')
        previous = original.get('storage')
        if previous is not None and previous != self.storage:
            raise ValueError('Do not replace another registered storage binding')
        result = deepcopy(original)
        result['storage'] = deepcopy(self.storage)
        result['driveRoots'] = dict.fromkeys(ROLES, self.storage['driveId'])
        return result

    def reference(self, original):
        key = tuple(original.get(field) for field in ('provider_id', 'content_sha256', 'byte_length',
            'original_filename', 'component', 'drive_root_id', 'storage_version', 'path'))
        if key not in self.resolved:
            resolved = self.resolve_reference(deepcopy(original))
            if any(resolved.get(field) != original.get(field) for field in (
                    'provider_id', 'content_sha256', 'byte_length', 'original_filename', 'component')):
                raise ValueError('A storage relocation must preserve exact original artifact identity')
            self.resolved[key] = deepcopy(resolved)
        return deepcopy(self.resolved[key])

    def reader(self, reference):
        root = reference['drive_root_id']
        if root not in self.readers:
            reader = self.reader_factory(root)
            if reader.drive_folder_id != root:
                raise ValueError('Source reader belongs to another Drive')
            self.readers[root] = reader
        return self.readers[root]

    @contextmanager
    def native_reads(self, manager_type):
        if os.environ.get('DAQR_PIPELINE155_BINDING_WORKER') != '1':
            raise ValueError('Native read routing requires the isolated Pipeline 155 worker')
        original = manager_type.download_artifact
        binding = self

        def download(manager, reference, *args, **kwargs):
            resolved = binding.reference(reference)
            if resolved.get('relocationReceipt') is not None:
                return binding.download_relocated(binding.reader(resolved), resolved, *args, **kwargs)
            return original(binding.reader(resolved), resolved, *args, **kwargs)

        manager_type.download_artifact = download
        try:
            yield
        finally:
            manager_type.download_artifact = original

    @staticmethod
    def download_relocated(manager, reference, cache_dir, *, max_bytes=2 * 1024**3):
        from googleapiclient.http import MediaIoBaseDownload
        receipt = reference['relocationReceipt']
        filename = reference['original_filename']
        relative = PurePosixPath(reference['path'])
        if (reference.get('status') != 'verified'
                or receipt.get('state') != 'moved' or receipt.get('fileId') != reference['provider_id']
                or receipt.get('driveId') != reference['drive_root_id']
                or receipt.get('sha256') != reference['content_sha256']
                or receipt.get('bytes') != reference['byte_length']
                or receipt.get('path') != reference['path']
                or str(receipt.get('storageVersion')) != reference['storage_version']
                or reference['drive_root_id'] != manager.drive_folder_id
                or reference['component'] not in ('framework_state', 'model_state')
                or relative.parts[:2] != ('quantum_data_lake', reference['component'])
                or any(part in ('', '.', '..') for part in reference['path'].split('/'))
                or relative.name != filename or filename.startswith('MultiRunEvaluator')
                or filename in ('', '.', '..') or any(value in filename for value in ('/', '\\', '\0', '\n', '\r'))
                or re.fullmatch('[a-f0-9]{64}', str(reference['content_sha256'])) is None
                or not isinstance(receipt.get('parents'), list) or len(receipt['parents']) != 1
                or not isinstance(receipt['parents'][0], str) or not receipt['parents'][0]
                or type(reference['byte_length']) is not int
                or type(max_bytes) is not int or not 0 < reference['byte_length'] <= max_bytes):
            raise ValueError('Exact registered relocation receipt required')
        cache = Path(cache_dir).resolve(strict=True)
        if not cache.is_dir() or str(cache).startswith('/Volumes/'):
            raise ValueError('Private internal temporary native cache required')
        destination = cache / filename
        partial = cache / ('.' + filename + '.partial')
        if destination.exists() or destination.is_symlink() or partial.exists() or partial.is_symlink():
            raise FileExistsError(destination)

        def metadata():
            value = manager.drive.files().get(fileId=reference['provider_id'], supportsAllDrives=True,
                fields='id,name,size,version,driveId,parents,trashed').execute()
            if (value.get('id') != reference['provider_id'] or value.get('name') != filename
                    or int(value.get('size', -1)) != reference['byte_length']
                    or str(value.get('version')) != reference['storage_version']
                    or value.get('driveId') != reference['drive_root_id'] or value.get('trashed')
                    or value.get('parents') != receipt.get('parents')):
                raise ValueError('Relocated native object metadata differs from Git receipt')
            return value

        before = metadata()
        created = False
        try:
            with partial.open('xb') as stream:
                created = True
                downloader = MediaIoBaseDownload(stream, manager.drive.files().get_media(
                    fileId=reference['provider_id'], supportsAllDrives=True), chunksize=8 * 1024**2)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                    if stream.tell() > reference['byte_length']:
                        raise ValueError('Relocated state exceeds pinned size')
            checksum, _, length = manager._artifact_digests(partial)
            if (length != reference['byte_length']
                    or checksum != reference['content_sha256']
                    or metadata() != before):
                raise ValueError('Relocated native bytes/version changed')
            os.link(partial, destination)
            destination.chmod(0o600)
            return str(destination)
        finally:
            if created:
                partial.unlink(missing_ok=True)

    def driver_type(self, original_type, manager_type):
        binding = self

        class BoundDriver(original_type):
            def run(self, *args, **kwargs):
                with binding.native_reads(manager_type), binding.connected(self):
                    return super().run(*args, **kwargs)

        return BoundDriver

    @contextmanager
    def connected(self, driver):
        port = driver.indexed_runner_port
        if port is None or not callable(getattr(port, '_materialize', None)):
            raise ValueError('The existing indexed runner/model state port is required')
        original_workflow = driver.workflow
        bound_workflow = self.workflow(original_workflow)
        old_managers, old_port_managers = driver.managers, port.managers
        old_port_values = dict(old_port_managers)
        materialize = port._materialize
        instance_method = vars(port).get('_materialize')
        had_instance_method = '_materialize' in vars(port)
        writer = self.writer
        binding = self

        def load_states(instance, artifacts):
            names = [value['original_filename'] for value in artifacts.values()]
            if len(set(names)) != len(names):
                raise ValueError('Duplicate original runner/model state filenames')
            resolved = [(name, binding.reference(reference)) for name, reference in artifacts.items()]
            for _, reference in resolved:
                filename = reference['original_filename']
                if (not filename.endswith('.pkl') or filename.startswith('MultiRunEvaluator')
                        or reference['component'] not in ('framework_state', 'model_state')):
                    raise ValueError('Only original native runner/model states may resume')
            result = {}
            try:
                for name, reference in resolved:
                    role = 'runner' if reference['component'] == 'framework_state' else 'model'
                    instance.managers = {**instance.managers, role: binding.reader(reference)}
                    loaded = materialize({name: reference})
                    if set(loaded).intersection(result):
                        raise ValueError('Ambiguous resumed state filename')
                    result.update(loaded)
            finally:
                instance.managers = old_port_managers
            return result

        try:
            driver.workflow = bound_workflow
            driver.managers = dict.fromkeys(ROLES, writer)
            old_port_managers.clear()
            old_port_managers.update(dict.fromkeys(ROLES, writer))
            port.managers = old_port_managers
            port._materialize = MethodType(load_states, port)
            yield driver
        finally:
            driver.workflow = original_workflow
            old_port_managers.clear()
            old_port_managers.update(old_port_values)
            driver.managers, port.managers = old_managers, old_port_managers
            if had_instance_method:
                port._materialize = instance_method
            else:
                del port._materialize
