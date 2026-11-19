"""Explicit identity for an existing pipeline Drive and private staging directory."""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import stat
from uuid import NAMESPACE_URL, uuid5


def provision_pipeline_storage(service, pipeline_id, existing_storage=None):
    if type(pipeline_id) not in (str, int) or re.fullmatch(r'[1-9][0-9]*', str(pipeline_id)) is None:
        raise ValueError('Exact positive pipeline identity required')
    pipeline_id = str(pipeline_id)
    if existing_storage is not None:
        storage = validate_storage(existing_storage)
        if storage['pipelineId'] != pipeline_id:
            raise ValueError('Existing Drive binding belongs to another pipeline')
        return storage
    name = 'quantum_pipeline_' + pipeline_id
    request_id = str(uuid5(NAMESPACE_URL, 'https://github.com/pzg8794/quantum-pipelines/Pipeline_' + pipeline_id + '/storage'))
    created = service.drives().create(body={'name': name}, requestId=request_id, fields='id,name').execute()
    if type(created) is not dict or created.get('name') != name:
        raise ValueError('Created existing-account SharedDrive identity differs')
    return validate_storage(dict(pipelineId=pipeline_id, driveId=created.get('id')))


def validate_storage(storage):
    if (type(storage) is not dict or set(storage) != {'pipelineId', 'driveId'}
            or not isinstance(storage['pipelineId'], str)
            or re.fullmatch(r'[1-9][0-9]*', storage['pipelineId']) is None
            or not isinstance(storage['driveId'], str)
            or re.fullmatch(r'[A-Za-z0-9_-]{1,256}', storage['driveId']) is None):
        raise ValueError('Exact pipeline storage identity and Drive ID required')
    return deepcopy(storage)


def read_private_json(path, maximum):
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        metadata = os.fstat(stream.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1 or metadata.st_mode & 0o077
                or metadata.st_size > maximum):
            raise ValueError('Private bounded pipeline cache metadata required')
        return json.loads(stream.read(maximum + 1))


def validate_staging_directory(staging_dir):
    if staging_dir is None:
        raise ValueError('Explicit existing private staging_dir required for pipeline storage')
    path = Path(staging_dir).expanduser()
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ValueError('Existing absolute pipeline staging directory required')
    path = path.resolve(strict=True)
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise ValueError('Private operator-owned pipeline staging directory required')
    if (path.is_relative_to(Path.home() / 'Library/CloudStorage')
            or path.is_relative_to('/Volumes') or path.is_relative_to('/content/drive')):
        raise ValueError('Pipeline staging must not be an unverified mounted Drive workspace')
    if any((parent / '.git').exists() for parent in (path, *path.parents)):
        raise ValueError('Pipeline runtime staging must be outside source repositories')
    return path


def bind_staging(storage, staging_dir):
    storage = validate_storage(storage)
    path = validate_staging_directory(staging_dir)
    marker = path / '.pipeline-storage.json'
    expected = dict(schema='pipeline-storage-binding/v1', storage=storage)
    if marker.exists() or marker.is_symlink():
        if read_private_json(marker, 4096) != expected:
            raise ValueError('Staging directory belongs to a different pipeline/Drive binding')
    else:
        if any(path.iterdir()):
            raise ValueError('Unbound legacy staging contents cannot be adopted implicitly')
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(expected, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
    return storage, path


def validate_local_path(path, staging_dir):
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.is_symlink() or not candidate.resolve().is_relative_to(staging_dir):
        raise ValueError('Cached state belongs outside the bound pipeline staging directory')
    return str(candidate)


def load_registry(staging_dir):
    path = staging_dir / 'local_backup_registry.json'
    if not path.exists() and not path.is_symlink():
        return {}
    registry = read_private_json(path, 32 * 1024**2)
    if type(registry) is not dict:
        raise ValueError('Pipeline cache registry dictionary required')
    for entries in registry.values():
        if type(entries) is not dict:
            raise ValueError('Original filename-to-local-path registry required')
        for filename, value in entries.items():
            if (not isinstance(filename, str) or filename in ('.', '..')
                    or Path(filename).name != filename or not isinstance(value, str)
                    or Path(value).name != filename):
                raise ValueError('Original local cache filename/path entry required')
            validate_local_path(value, staging_dir)
    return registry
