"""Explicit, non-destructive registration of active pipeline infrastructure."""
import io
import base64
import json
import tempfile
import re

from googleapiclient.http import MediaIoBaseUpload

from .gd_backup_manager import GoogleDriveBackupManager
from .pipeline_backup_index import GitHubBackupIndexStore, synchronize_backup_index
from .pipeline_storage import provision_pipeline_storage, validate_storage
from .pipeline_backup_index import blob_sha, encoded_index


BASE_BACKUP_INDEX_PATHS = (
    'backup_index.json',
    'quantum_data_lake/backup_index.json',
    'quantum_data_lake/framework_state/backup_index.json',
    'quantum_data_lake/model_state/backup_index.json',
    'quantum_logs/backup_index.json',
)


def plan_pipeline_git_structure(management, tree, *, source_commit):
    if not re.fullmatch(r'[a-f0-9]{40}', source_commit):
        raise ValueError('Pinned original catalog and tree commit required')
    if tree.get('truncated') or not isinstance(tree.get('tree'), list):
        raise ValueError('Complete recursive Git tree required')
    existing = {}
    for entry in tree['tree']:
        path = entry['path']
        if path in existing:
            raise ValueError('Unique Git tree paths required')
        existing[path] = entry['type']
    changes, preserved = [], []
    for row in active_pipeline_rows(management):
        if row['pipeline_id'] == 157:
            continue
        prefix = 'Pipeline_' + str(row['pipeline_id'])
        if existing.get(prefix) != 'tree' or existing.get(prefix + '/PIPELINE.md') != 'blob':
            raise ValueError('Existing canonical pipeline folder and record required')
        documents = {path: {} for path in BASE_BACKUP_INDEX_PATHS}
        documents['workflow_status/status.json'] = dict(
            pipeline=prefix, allocators={}, importState='pending',
            originalRecord=dict(row['record'], repository='pzg8794/quantum-pipelines', commit=source_commit))
        for relative, document in documents.items():
            path = prefix + '/' + relative
            if path in existing:
                if existing[path] != 'blob':
                    raise ValueError('Structure file collides with a non-file: ' + path)
                preserved.append(path)
                continue
            parents = path.split('/')[:-1]
            if any('/'.join(parents[:position]) in existing
                   and existing['/'.join(parents[:position])] != 'tree'
                   for position in range(1, len(parents) + 1)):
                raise ValueError('Structure directory collides with a non-directory: ' + path)
            changes.append(dict(path=path, mode='100644', type='blob', content=encoded_index(document).decode()))
    return dict(source_commit=source_commit, changes=changes, preserved=preserved,
                dataMigration='not-performed', scientificHierarchy='not-imported')


def verify_empty_template_indexes(snapshot):
    if snapshot.get('foreign_data'):
        raise ValueError('Unbound non-template data requires explicit reconciliation')
    for path, digest in snapshot['indexes'].items():
        content = snapshot.get('contents', {}).get(path)
        if path not in BASE_BACKUP_INDEX_PATHS or not isinstance(content, bytes) or blob_sha(content) != digest:
            raise ValueError('Unbound backup template identity is not verified')
        try:
            value = json.loads(content)
        except (ValueError, UnicodeError) as error:
            raise ValueError('Unbound malformed backup mirror requires explicit reconciliation') from error
        if not isinstance(value, dict) or value:
            raise ValueError('Unbound populated backup mirrors require explicit reconciliation')


def register_missing_workflow_versions(management, store=None, *, source_commit):
    if not re.fullmatch(r'[a-f0-9]{40}', source_commit):
        raise ValueError('Pinned original catalog commit required')
    from .tae_workflow import WorkflowStore, workflow_table_entry
    store = store or WorkflowStore()
    def snapshot():
        head = store.api('git/ref/heads/main')['object']['sha']
        root = store.api('git/commits/' + head)['tree']['sha']
        tree = store.api('git/trees/' + root)
        if tree.get('truncated'):
            raise ValueError('Complete workflow root required')
        blobs = {entry['path']: entry['sha'] for entry in tree['tree'] if entry['type'] == 'blob'}
        index = json.loads(base64.b64decode(store.api('git/blobs/' + blobs['index.json'])['content']))
        return head, root, index
    head, _, index = snapshot()
    snapshot_parent = head
    candidates = {}
    for row in active_pipeline_rows(management):
        key = 'Pipeline_' + str(row['pipeline_id'])
        if key in index:
            continue
        document = dict(pipeline=key, allocators={}, importState='legacy-evidence-preserved-not-imported',
            originalRecord=dict(row['record'], repository='pzg8794/quantum-pipelines', commit=source_commit),
            originalStatus={name: value for name, value in row.get('status', {}).items()
                if name in ('capture_complete', 'scientific_matrix_complete', 'fairness', 'prepared', 'lifecycle')})
        tree = store.api('git/trees', dict(tree=[dict(path='workflow.json', mode='100644', type='blob', content=encoded_index(document).decode()),
            dict(path='status.json', mode='100644', type='blob', content=encoded_index(dict(state='none', current=0, expected=0)).decode())]))
        commit = store.api('git/commits', dict(message='Register ' + key + ' workflow template; preserve original evidence',
            tree=tree['sha'], parents=[snapshot_parent]))
        snapshot_parent = commit['sha']
        candidates[key] = dict(version=commit['sha'], importState='legacy-evidence-preserved-not-imported',
            table=workflow_table_entry(document))
    if not candidates:
        return dict(state='unchanged', registered=[])
    head, root, previous = snapshot()
    updated = dict(previous)
    for key, value in candidates.items():
        updated.setdefault(key, value)
    tree = store.api('git/trees', dict(base_tree=root, tree=[dict(path='index.json', mode='100644', type='blob', content=encoded_index(updated).decode())]))
    commit = store.api('git/commits', dict(message='Index active pipeline workflows without changing the running workflow', tree=tree['sha'], parents=[head, snapshot_parent]))
    store.api('git/refs/heads/main', dict(sha=commit['sha'], force=False), method='PATCH')
    readback = store.api('contents/index.json?ref=' + commit['sha'])
    observed = json.loads(base64.b64decode(readback['content']))
    if observed != updated or any(observed.get(key) != value for key, value in previous.items()):
        raise RuntimeError('Workflow index readback differs')
    return dict(state='registered', registered=sorted(set(updated) - set(previous)), commit=commit['sha'])


def active_pipeline_rows(management):
    rows = management['pipelines']
    identities = [row['pipeline_id'] for row in rows]
    if any(type(value) is not int or value <= 0 for value in identities) or len(set(identities)) != len(identities):
        raise ValueError('Unique canonical pipeline identities required')
    retired = {str(key) for row in rows for key in row.get('status', {}).get('retired_pipeline_references', {})}
    return [row for row in rows if row['pipeline_id'] not in (1, 30)
            and str(row['pipeline_id']) not in retired
            and not row.get('status', {}).get('retirement')
            and row.get('status', {}).get('tableFacts', {}).get('dataArtifacts') != 0]


class PipelineInfrastructureAlignment:
    def __init__(self, service, *, store=None, native_service_account=None):
        self.service = service
        self.store = store or GitHubBackupIndexStore()
        self.native_service_account = native_service_account

    def align(self, row):
        identity = str(row['pipeline_id'])
        snapshot = self.store.snapshot(identity)
        record = self.store.read_record(snapshot)
        if str(record['pipeline_id']) != identity:
            raise ValueError('Pipeline identity differs from the selected active row')
        if record.get('storage') is not None:
            storage = validate_storage(record['storage'])
            self.store.verify_binding(storage, snapshot)
            return dict(pipeline=identity, state='existing-binding-preserved', storage=storage)
        verify_empty_template_indexes(snapshot)
        if not self.native_service_account:
            raise ValueError('Reuse the existing native service account for pipeline Drive access')
        storage = provision_pipeline_storage(self.service, identity)
        permissions = self.service.permissions().list(fileId=storage['driveId'], supportsAllDrives=True,
            fields='permissions(id,emailAddress,role)').execute().get('permissions', [])
        if not any(value.get('emailAddress') == self.native_service_account and value.get('role') in ('writer', 'fileOrganizer', 'organizer')
                   for value in permissions):
            self.service.permissions().create(fileId=storage['driveId'], supportsAllDrives=True,
                sendNotificationEmail=False, body=dict(type='user', role='writer', emailAddress=self.native_service_account), fields='id').execute()
        with tempfile.TemporaryDirectory(prefix='pipeline-alignment-') as directory:
            manager = GoogleDriveBackupManager('infrastructure', directory, pipeline_storage=storage,
                staging_dir=directory, drive_service=self.service)
            roots = {}
            for name in ('quantum_data_lake', 'quantum_logs', 'workflow_status'):
                roots[name] = manager._ensure_drive_folder(name, storage['driveId'])
                if not roots[name]:
                    raise RuntimeError('Pipeline folder registration pending: ' + name)
            for name in ('framework_state', 'model_state'):
                if not manager._ensure_drive_folder(name, roots['quantum_data_lake']):
                    raise RuntimeError('Pipeline state folder registration pending: ' + name)
            present = self.service.files().list(q="name='status.json' and '" + roots['workflow_status'] + "' in parents and trashed=false",
                supportsAllDrives=True, includeItemsFromAllDrives=True, fields='files(id)').execute().get('files', [])
            if len(present) > 1:
                raise ValueError('Ambiguous pipeline status template')
            if not present:
                payload = dict(pipeline='Pipeline_' + identity, allocators={}, importState='legacy-evidence-preserved-not-imported',
                    originalRecord=dict(repository=self.store.repository, commit=snapshot['head'], path='Pipeline_' + identity + '/PIPELINE.md'))
                media = MediaIoBaseUpload(io.BytesIO(json.dumps(payload, sort_keys=True).encode()), mimetype='application/json', resumable=False)
                self.service.files().create(body=dict(name='status.json', parents=[roots['workflow_status']]),
                    media_body=media, supportsAllDrives=True, fields='id').execute()
            snapshot = self.store.bind_storage(storage, snapshot)
            mirrored = synchronize_backup_index(self.service, storage, overwrite=True, store=self.store, snapshot=snapshot)
        return dict(pipeline=identity, state='structure-registered', storage=storage, mirror=mirrored,
            dataMigration='not-performed', originalReferencesPreserved=True)
