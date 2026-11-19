"""Storage identity and direct backup lookup for one registered pipeline."""
from copy import deepcopy
from pathlib import PurePosixPath

from daqr.config.pipeline_storage import validate_storage

from .registry import PipelineRegistry, normalize_pipeline_id

# WE ALREADY HAVE A GD DRIVE BINDING, WHAT IS THIS FOR??? WORSE CASE SCENARIO, WE SHOULD INHERIT IT!
class Storage:
    def __init__(self, pipeline_id, *, registry=None):
        self._pipeline_id = normalize_pipeline_id(pipeline_id)
        self._registry = registry if registry is not None else PipelineRegistry()
        self._resources = self._registry.resolve(self.pipeline_id)
        if self._resources['pipeline_id'] != self.pipeline_id or self._resources['pipeline_key'] != self.pipeline_key:
            raise ValueError('Resolved metadata belongs to a different pipeline')
        self._storage_binding = deepcopy(self._resources['storage'])
        if self._storage_binding is not None:
            self._storage_binding = validate_storage(self._storage_binding)
            if self._storage_binding['pipelineId'] != str(self.pipeline_id):
                raise ValueError('Drive storage belongs to a different pipeline')
        self._backup_indexes = {}
        self._migration_manifest = None

    @property
    def pipeline_id(self):
        return self._pipeline_id

    @property
    def pipeline_key(self):
        return 'Pipeline_' + str(self.pipeline_id)

    @property
    def storage_binding(self):
        return deepcopy(self._storage_binding)

    @property
    def drive_id(self):
        return self._storage_binding['driveId'] if self._storage_binding is not None else None

    @property
    def pipeline_reference(self):
        return deepcopy(self._resources['pipeline_reference'])

    def resolve_artifact_reference(self, reference):
        migration = self._resources['record'].get('storageMigration') or {}
        if self._migration_manifest is None:
            manifest_ref = migration.get('manifestRef')
            if manifest_ref is None:
                raise LookupError('No verified migration manifest registered for ' + self.pipeline_key)
            manifest = self._registry.read_json(manifest_ref)
            if (manifest.get('pipelineId') != str(self.pipeline_id)
                    or manifest.get('driveId') != self.drive_id or not isinstance(manifest.get('files'), dict)):
                raise ValueError('Migration manifest belongs to a different pipeline/Drive')
            self._migration_manifest = manifest
        identity = reference['provider_id']
        shared = self._migration_manifest.get('sharedReferences', {}).get(identity)
        if shared is not None:
            if any(shared.get(key) != reference.get(key) for key in ('provider_id', 'content_sha256', 'byte_length')):
                raise ValueError('Shared reference content identity differs')
            return deepcopy(shared)
        receipt = self._migration_manifest['files'][identity]
        if (receipt.get('driveId') != self.drive_id or receipt.get('state') != 'moved'
                or receipt.get('sha256') != reference.get('content_sha256')
                or receipt.get('bytes') != reference.get('byte_length')):
            raise ValueError('Relocation cannot change saved content or pipeline identity')
        resolved = deepcopy(reference)
        resolved.update(drive_root_id=self.drive_id, path=receipt['path'])
        if receipt.get('storageVersion') is not None:
            resolved['storage_version'] = receipt['storageVersion']
        if 'parents' in resolved:
            resolved['parents'] = deepcopy(receipt['parents'])
        return resolved

    def backup_path(self, filename, directory=''):
        if self.drive_id is None:
            raise LookupError('No Drive binding is registered for ' + self.pipeline_key)
        if (not isinstance(filename, str) or not filename or filename in ('.', '..')
                or '/' in filename or '\\' in filename or '\0' in filename):
            raise ValueError('An exact saved filename is required')
        if (not isinstance(directory, str) or directory.startswith('/')
                or any(part in ('.', '..') for part in directory.split('/'))
                or '\\' in directory):
            raise ValueError('A relative backup directory is required')
        reference = self.pipeline_reference
        reference['path'] = str(PurePosixPath(self.pipeline_key) / directory / 'backup_index.json')
        if reference['path'] not in self._backup_indexes:
            self._backup_indexes[reference['path']] = self._registry.read_json(reference)
        index = self._backup_indexes[reference['path']]
        value = index[filename]
        expected = 'gdrive://' + self.drive_id + '/' + str(PurePosixPath(directory) / filename)
        if value != expected:
            raise ValueError('Backup entry does not match the bound pipeline Drive/path')
        return value
