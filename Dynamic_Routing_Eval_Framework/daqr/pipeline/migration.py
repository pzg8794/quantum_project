"""Exact-ID server-side moves; never download, deserialize, copy or delete data."""
from copy import deepcopy
from pathlib import PurePosixPath
import re

from daqr.config.pipeline_storage import validate_storage
from .adoption import PipelineAdoptionPublisher
import hashlib
import json


FIELDS = 'id,name,mimeType,driveId,parents,size,md5Checksum,sha256Checksum,version,capabilities'
FOLDER = 'application/vnd.google-apps.folder'


class PipelineArtifactMover:
    def __init__(self, service, storage, metadata=None):
        self.service = service
        self.storage = validate_storage(storage)
        self.metadata = deepcopy(metadata or {})
        self.folders = {'': self.storage['driveId']}
        self.children = {}

    def read(self, identity, refresh=False):
        if not refresh and identity in self.metadata:
            return self.metadata[identity]
        value = self.service.files().get(fileId=identity, supportsAllDrives=True, fields=FIELDS).execute()
        if value.get('id') != identity:
            raise ValueError('Drive returned another file identity')
        self.metadata[identity] = value
        return value

    @staticmethod
    def safe_path(value):
        if (not isinstance(value, str) or not value or value.startswith('/')
                or any(part in ('', '.', '..') for part in value.split('/'))
                or any(character in value for character in ('\\', '\0', '\n', '\r'))):
            raise ValueError('Exact safe relative artifact path required')
        return value

    def original_path(self, metadata):
        names, visited = [metadata['name']], {metadata['id']}
        parents = metadata.get('parents', [])
        while parents and parents[0] != metadata.get('driveId'):
            if len(parents) != 1 or parents[0] in visited:
                raise ValueError('Ambiguous source parent hierarchy')
            identity = parents[0]
            visited.add(identity)
            parent = self.metadata.get(identity) or self.read(identity)
            names.append(parent['name'])
            parents = parent.get('parents', [])
        if len(parents) != 1:
            raise ValueError('Source path does not terminate at its Drive root')
        return self.safe_path('/'.join(reversed(names)))

    def preflight(self, artifacts):
        planned, identities, paths = [], set(), set()
        for artifact in artifacts:
            identity = artifact.get('fileId')
            digest = artifact.get('sha256')
            if (not isinstance(identity, str) or not identity or identity in identities
                    or not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest)):
                raise ValueError('Unique exact IDs and saved SHA256 values required')
            before = self.read(identity)
            if before.get('mimeType') == FOLDER or before.get('sha256Checksum') != digest:
                raise ValueError('Artifact is not the exact saved binary file: ' + identity)
            if len(before.get('parents', [])) != 1:
                raise ValueError('Exactly one source parent required')
            path = self.safe_path(artifact.get('path') or self.original_path(before))
            if PurePosixPath(path).name != before['name'] or path in paths:
                raise ValueError('Filename/path collision; preserve ' + identity
                    + ': expected ' + path + ', observed ' + before['name'])
            if (before.get('driveId') != self.storage['driveId']
                    and not before.get('capabilities', {}).get('canMoveItemOutOfDrive')):
                raise PermissionError('Source Drive does not permit moving ' + identity)
            identities.add(identity)
            paths.add(path)
            planned.append(dict(pipelineId=self.storage['pipelineId'], fileId=identity,
                path=path, sha256=digest, before=deepcopy(before)))
        return planned

    def contents(self, parent):
        if parent not in self.children:
            entries, token = [], None
            while True:
                result = self.service.files().list(corpora='drive', driveId=self.storage['driveId'],
                    supportsAllDrives=True, includeItemsFromAllDrives=True,
                    q="trashed=false and '" + parent + "' in parents", pageSize=1000,
                    pageToken=token, fields='nextPageToken,files(id,name,mimeType)').execute()
                entries.extend(result.get('files', []))
                token = result.get('nextPageToken')
                if not token:
                    break
            self.children[parent] = entries
        return self.children[parent]

    def folder(self, path):
        if path in self.folders:
            return self.folders[path]
        relative = PurePosixPath(path)
        parent = self.folder('' if str(relative.parent) == '.' else str(relative.parent))
        matches = [entry for entry in self.contents(parent) if entry['name'] == relative.name]
        if len(matches) > 1 or matches and matches[0].get('mimeType') != FOLDER:
            raise ValueError('Destination folder collision')
        if matches:
            value = matches[0]
        else:
            value = self.service.files().create(body=dict(name=relative.name,
                mimeType=FOLDER, parents=[parent]), supportsAllDrives=True,
                fields='id,name,mimeType').execute()
            self.children[parent].append(value)
        self.folders[path] = value['id']
        return value['id']

    def move(self, planned):
        if planned.get('pipelineId') != self.storage['pipelineId']:
            raise ValueError('Move belongs to a different pipeline')
        before = planned['before']
        relative = PurePosixPath(self.safe_path(planned['path']))
        parent = self.folder('' if str(relative.parent) == '.' else str(relative.parent))
        matches = [entry for entry in self.contents(parent) if entry['name'] == relative.name]
        if any(entry['id'] != planned['fileId'] for entry in matches):
            raise ValueError('Destination already contains a different file; no overwrite')
        if before.get('driveId') != self.storage['driveId'] or before['parents'] != [parent]:
            self.service.files().update(fileId=planned['fileId'], addParents=parent,
                removeParents=','.join(before['parents']), supportsAllDrives=True,
                fields='id,parents,driveId').execute()
        after = self.read(planned['fileId'], refresh=True)
        unchanged = all(before.get(field) == after.get(field)
            for field in ('id', 'name', 'size', 'md5Checksum', 'sha256Checksum'))
        if not unchanged or after.get('driveId') != self.storage['driveId'] or after.get('parents') != [parent]:
            raise RuntimeError('Move verification failed; preserve file and inspect its exact ID')
        return dict(pipelineId=self.storage['pipelineId'], fileId=after['id'], path=planned['path'],
            sha256=after['sha256Checksum'], bytes=int(after['size']), state='moved',
            originalDriveId=before.get('driveId'), originalParents=before['parents'],
            driveId=after['driveId'], parents=after['parents'], storageVersion=after.get('version'))


def migration_documents(record, receipts, previous=None, *, inventory=None, shared_references=None):
    storage = validate_storage(record['storage'])
    manifest = deepcopy(previous or dict(schema='pipeline-artifact-move/v1',
        pipelineId=storage['pipelineId'], driveId=storage['driveId'], files={}))
    if manifest['pipelineId'] != storage['pipelineId'] or manifest['driveId'] != storage['driveId']:
        raise ValueError('Existing migration belongs to another pipeline/Drive')
    for receipt in receipts:
        if (receipt.get('pipelineId') != storage['pipelineId'] or receipt.get('driveId') != storage['driveId']
                or receipt.get('state') != 'moved' or not re.fullmatch('[a-f0-9]{64}', receipt.get('sha256', ''))
                or type(receipt.get('bytes')) is not int or receipt['bytes'] < 0
                or len(receipt.get('parents', [])) != 1):
            raise ValueError('Exact verified move receipt required')
        identity = receipt['fileId']
        if identity in manifest['files']:
            existing = manifest['files'][identity]
            if any(existing[field] != receipt[field] for field in ('sha256', 'bytes', 'driveId', 'path')):
                raise ValueError('Migration receipt changed an existing file identity/content')
        else:
            manifest['files'][identity] = deepcopy(receipt)
    manifest.update(state='partial', inventoryComplete=False,
        movedFiles=len(manifest['files']), verifiedBytes=sum(r['bytes'] for r in manifest['files'].values()))
    if inventory is not None:
        expected = {}
        for artifact in inventory:
            identity = artifact.get('fileId')
            if not isinstance(identity, str) or not identity or identity in expected:
                raise ValueError('Unique exact owned artifact inventory required')
            receipt = manifest['files'].get(identity)
            if (receipt is None or artifact.get('sha256') != receipt['sha256']
                    or artifact.get('bytes') != receipt['bytes']):
                raise ValueError('Owned inventory is not completely moved and verified: ' + identity)
            expected[identity] = dict(sha256=receipt['sha256'], bytes=receipt['bytes'])
        if set(expected) != set(manifest['files']):
            raise ValueError('Closure must account for every moved artifact')
        shared = deepcopy(shared_references or {})
        for identity, reference in shared.items():
            if (identity in expected or reference.get('provider_id') != identity
                    or reference.get('status') != 'verified'
                    or not re.fullmatch('[a-f0-9]{64}', reference.get('content_sha256', ''))
                    or not reference.get('drive_root_id') or type(reference.get('byte_length')) is not int):
                raise ValueError('Shared references must remain explicit and separate from owned moves')
        manifest.update(state='complete-with-shared-references' if shared else 'complete',
            inventoryComplete=True, inventoryScope='registered-artifacts-and-pinned-completion-queues',
            ownedInventory=expected, sharedReferences=shared)
    updated = deepcopy(record)
    for artifact in updated.get('artifact_metadata', []):
        original = artifact.get('sourceRef') or {}
        identity = artifact.get('provider_id') or original.get('provider_id')
        if identity not in manifest['files']:
            continue
        receipt = manifest['files'][identity]
        artifact.setdefault('originalSourceRef', deepcopy(original))
        current = dict(original, provider_id=identity, drive_root_id=receipt['driveId'],
            path=receipt['path'], parents=deepcopy(receipt['parents']))
        if receipt.get('storageVersion') is not None:
            current['storage_version'] = receipt['storageVersion']
        artifact.update(sourceRef=current, path=receipt['path'])
    return updated, manifest


class PipelineMigrationPublisher(PipelineAdoptionPublisher):
    def publish(self, pipeline, receipts, *, inventory=None, shared_references=None):
        number, key = pipeline.pipeline_id, pipeline.pipeline_key
        stores = pipeline._registry._stores
        canonical, workflows = stores['pzg8794/quantum-pipelines'], stores['pzg8794/TAE_Workflow']
        reference = pipeline.pipeline_reference
        head = self._head(canonical)
        if reference['commit'] != head:
            raise ValueError('Canonical record advanced; reload before publishing migration')
        text = self._read(canonical, head, reference['path'])
        match, original = self._block(text, 'CRISP-PIPELINE-RECORD')
        previous = None
        previous_ref = original.get('storageMigration', {}).get('manifestRef')
        if previous_ref:
            previous = json.loads(self._read(workflows, previous_ref['commit'], previous_ref['path']))
        record, manifest = migration_documents(original, receipts, previous,
            inventory=inventory, shared_references=shared_references)
        workflow_head = self._head(workflows)
        index = json.loads(self._read(workflows, workflow_head, 'index.json'))
        entry = deepcopy(index[key])
        old_version = entry['version']
        document = json.loads(self._read(workflows, old_version, 'workflow.json'))
        if document.get('pipeline') != key:
            raise ValueError('Workflow belongs to another pipeline')
        manifest_raw = self._encode(manifest)
        infrastructure = document.get('infrastructure')
        if not isinstance(infrastructure, dict) or str(infrastructure.get('pipelineId')) != str(number):
            raise ValueError('Own pipeline infrastructure must accompany the new workflow version')
        summary = dict(schema=manifest['schema'], state=manifest['state'],
            movedFiles=manifest['movedFiles'], verifiedBytes=manifest['verifiedBytes'],
            inventoryComplete=manifest['inventoryComplete'], driveId=manifest['driveId'])
        if manifest['inventoryComplete']:
            summary.update(inventoryScope=manifest['inventoryScope'], sharedReferences=manifest['sharedReferences'])
        document['storageMigration'] = summary
        base = workflows.api('git/commits/' + old_version)['tree']['sha']
        tree = workflows.api('git/trees', dict(base_tree=base, tree=[
            dict(path='workflow.json', mode='100644', type='blob', content=self._encode(document)),
            dict(path='storage_migration.json', mode='100644', type='blob', content=manifest_raw),
            dict(path='infrastructure.json', mode='100644', type='blob', content=self._encode(infrastructure))]))['sha']
        version = self._commit(workflows, workflow_head, tree, 'Record verified ' + key + ' artifact moves')
        entry['version'] = version
        for field, path in (('workflowRef', 'workflow.json'), ('statusRef', 'pipeline_status.json'),
                ('infrastructureRef', 'infrastructure.json')):
            entry[field] = dict(repository=workflows.repository, commit=version, path=path)
        manifest_ref = dict(repository=workflows.repository, commit=version, path='storage_migration.json',
            sha256=hashlib.sha256(manifest_raw.encode()).hexdigest())
        entry['storageMigration'] = dict(summary, manifestRef=manifest_ref)
        index[key] = entry
        tree = workflows.api('git/trees', dict(base_tree=tree, tree=[dict(path='index.json',
            mode='100644', type='blob', content=self._encode(index))]))['sha']
        indexed = self._commit(workflows, version, tree, 'Index ' + key + ' verified move manifest')
        self._advance(workflows, workflow_head, indexed)
        if json.loads(self._read(workflows, indexed, 'index.json')) != index:
            raise RuntimeError('Published migration index readback differs')
        if self._read(workflows, version, 'storage_migration.json') != manifest_raw:
            raise RuntimeError('Published migration manifest readback differs')
        record['storageMigration'] = dict(summary, manifestRef=manifest_ref)
        record['workflowRef'] = deepcopy(entry['workflowRef'])
        updated_text = text[:match.start(1)] + self._encode(record).rstrip() + text[match.end(1):]
        management_text = self._read(canonical, head, 'MANAGEMENT.md')
        management_match, management = self._block(management_text, 'CRISP-MANAGEMENT-RECORD')
        rows = [row for row in management['pipelines'] if row.get('pipeline_id') == number]
        if len(rows) != 1:
            raise ValueError('Unique canonical management entry required')
        rows[0]['record'] = dict(path=reference['path'], bytes=len(updated_text.encode()),
            sha256=hashlib.sha256(updated_text.encode()).hexdigest())
        rows[0]['workflowRef'] = deepcopy(entry['workflowRef'])
        updated_management = management_text[:management_match.start(1)] + self._encode(management).rstrip() + management_text[management_match.end(1):]
        tree = canonical.api('git/trees', dict(base_tree=canonical.api('git/commits/' + head)['tree']['sha'],
            tree=[dict(path=reference['path'], mode='100644', type='blob', content=updated_text),
                  dict(path='MANAGEMENT.md', mode='100644', type='blob', content=updated_management)]))['sha']
        revision = self._commit(canonical, head, tree, 'Link ' + key + ' verified artifact locations')
        self._advance(canonical, head, revision)
        if self._read(canonical, revision, reference['path']) != updated_text:
            raise RuntimeError('Canonical migration readback differs')
        return dict(pipelineId=number, canonicalCommit=revision, workflowRef=entry['workflowRef'],
            manifestRef=manifest_ref, movedFiles=manifest['movedFiles'], inventoryComplete=manifest['inventoryComplete'])
