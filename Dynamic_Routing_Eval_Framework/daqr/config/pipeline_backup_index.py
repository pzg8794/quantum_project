"""Metadata-only, explicit pipeline-boundary Drive-to-Git backup indexes."""
import base64
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import subprocess

from .pipeline_storage import validate_storage

INDEX_NAME = 'backup_index.json'
REPOSITORY = 'pzg8794/quantum-pipelines'


def blob_sha(content):
    return hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()


def encoded_index(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def drive_backup_indexes(service, drive_id):
    entries, token, pages = {}, None, set()
    while True:
        if token in pages:
            raise ValueError('Drive pagination repeated without progress')
        pages.add(token)
        page = service.files().list(corpora='drive', driveId=drive_id,
            includeItemsFromAllDrives=True, supportsAllDrives=True, q='trashed=false',
            fields='nextPageToken,files(id,name,mimeType,parents,driveId)',
            pageSize=1000, pageToken=token).execute()
        for entry in page.get('files', []):
            name = entry.get('name')
            if (not isinstance(name, str) or name in ('', '.', '..', '.git')
                    or any(character in name for character in ('/', '\0', '\n', '\r'))
                    or entry.get('driveId') != drive_id or entry.get('id') in entries):
                raise ValueError('Unique safe names inside the selected pipeline Drive required')
            if entry.get('mimeType') == 'application/vnd.google-apps.folder' and name == INDEX_NAME:
                raise ValueError('Drive folder collides with the backup index filename')
            if len(entry.get('parents', [])) != 1:
                raise ValueError('Exactly one in-Drive parent required for each backup entry')
            entries[entry['id']] = entry
        token = page.get('nextPageToken')
        if not token:
            break
    folders, visiting, folder_paths = {drive_id: ''}, set(), {''}
    def directory(identity):
        if identity in folders:
            return folders[identity]
        if identity in visiting or identity not in entries:
            raise ValueError('Drive folder graph is cyclic or escapes the selected Drive')
        entry = entries[identity]
        if entry.get('mimeType') != 'application/vnd.google-apps.folder':
            raise ValueError('Backup parent must be a Drive folder')
        visiting.add(identity)
        parent = directory(entry['parents'][0])
        relative = str(PurePosixPath(parent) / entry['name'])
        visiting.remove(identity)
        if relative in folder_paths:
            raise ValueError('Duplicate Drive folder path cannot be represented in Git')
        folders[identity] = relative
        folder_paths.add(relative)
        return relative
    for identity, entry in entries.items():
        if entry.get('mimeType') == 'application/vnd.google-apps.folder':
            directory(identity)
    dictionaries = {relative: {} for relative in folders.values()}
    for entry in entries.values():
        if entry.get('mimeType') == 'application/vnd.google-apps.folder':
            continue
        parent = directory(entry['parents'][0])
        name = entry['name']
        if name in dictionaries[parent]:
            raise ValueError('Duplicate filenames in one Drive folder cannot form a dictionary')
        relative = str(PurePosixPath(parent) / name)
        dictionaries[parent][name] = 'gdrive://' + drive_id + '/' + relative
    return {str(PurePosixPath(relative) / INDEX_NAME): encoded_index(values)
            for relative, values in dictionaries.items()}


class GitHubBackupIndexStore:
    repository = REPOSITORY

    def api(self, endpoint, payload=None, method=None):
        command = ['gh', 'api', 'repos/' + self.repository + '/' + endpoint,
                   '--header', 'Accept: application/vnd.github+json']
        if payload is not None:
            command += ['--method', method or 'POST', '--input', '-']
        environment = dict(os.environ)
        for name in ('GH_FORCE_TTY', 'CLICOLOR_FORCE', 'FORCE_COLOR'):
            environment.pop(name, None)
        environment.update(NO_COLOR='1', CLICOLOR='0', TERM='dumb', GH_PAGER='cat')
        result = subprocess.run(command, input=None if payload is None else json.dumps(payload).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60, env=environment)
        if result.returncode:
            raise RuntimeError('GitHub backup-index request failed; no forced reference update attempted')
        try:
            document = json.loads(result.stdout)
        except (ValueError, TypeError, UnicodeError) as error:
            raise RuntimeError('GitHub backup-index response was not machine-readable JSON; publication is pending') from error
        if not isinstance(document, dict):
            raise RuntimeError('GitHub backup-index response must be a JSON object')
        return document

    def snapshot(self, pipeline_id, *, commit=None, read_indexes=True):
        head = commit or self.api('git/ref/heads/main')['object']['sha']
        root = self.api('git/commits/' + head)['tree']['sha']
        root_tree = self.api('git/trees/' + root)
        if root_tree.get('truncated'):
            raise ValueError('Complete Git root tree required')
        prefix = 'Pipeline_' + pipeline_id
        matches = [entry for entry in root_tree['tree'] if entry['path'] == prefix]
        if len(matches) != 1 or matches[0]['type'] != 'tree':
            raise ValueError('Pipeline must already be registered in the canonical Git index')
        tree = self.api('git/trees/' + matches[0]['sha'] + '?recursive=1')
        if tree.get('truncated'):
            raise ValueError('Complete pipeline Git tree required')
        indexes, contents, foreign_data, record_sha = {}, {}, False, None
        found_data = False
        for entry in tree['tree']:
            if entry['type'] != 'blob':
                if entry['type'] != 'tree':
                    foreign_data = True
                continue
            path = entry['path']
            if path == 'PIPELINE.md':
                record_sha = entry['sha']
            if PurePosixPath(path).name == INDEX_NAME:
                indexes[path] = entry['sha']
                if read_indexes and not found_data:
                    if entry['sha'] == blob_sha(encoded_index({})):
                        contents[path] = encoded_index({})
                    else:
                        blob = self.api('git/blobs/' + entry['sha'])
                        contents[path] = base64.b64decode(blob['content'])
                        try:
                            value = json.loads(contents[path])
                            found_data = not isinstance(value, dict) or bool(value)
                        except (ValueError, UnicodeError):
                            found_data = True
            elif path not in ('PIPELINE.md', 'README.md', 'workflow_status/status.json'):
                foreign_data = True
        management = next((entry['sha'] for entry in root_tree['tree']
                           if entry['path'] == 'MANAGEMENT.md' and entry['type'] == 'blob'), None)
        return dict(head=head, root=root, indexes=indexes, contents=contents,
                    foreign_data=foreign_data, record_sha=record_sha, management_sha=management)

    def read_record(self, snapshot):
        if 'record' in snapshot:
            return snapshot['record']
        if not snapshot['record_sha']:
            raise ValueError('Canonical pipeline record required before backup publication')
        blob = self.api('git/blobs/' + snapshot['record_sha'])
        text = base64.b64decode(blob['content']).decode()
        match = re.search(r'<!-- CRISP-PIPELINE-RECORD -->\s*```json\s*(.*?)\s*```', text, re.S)
        if not match:
            raise ValueError('Canonical structured pipeline record required')
        record = json.loads(match.group(1))
        if record.get('schema') != 'quantum-crisp-pipeline/v1':
            raise ValueError('Canonical pipeline record schema required')
        snapshot['record'], snapshot['record_text'] = record, text
        return record

    def verify_binding(self, storage, snapshot):
        record = self.read_record(snapshot)
        if (record.get('schema') != 'quantum-crisp-pipeline/v1'
                or str(record.get('pipeline_id')) != storage['pipelineId']
                or validate_storage(record.get('storage')) != storage):
            raise ValueError('Git pipeline storage binding differs from the selected Drive')

    def bind_storage(self, storage, snapshot):
        record = self.read_record(snapshot)
        if str(record.get('pipeline_id')) != storage['pipelineId']:
            raise ValueError('Canonical pipeline identity differs')
        if record.get('storage') is not None:
            self.verify_binding(storage, snapshot)
            return snapshot
        if not snapshot['management_sha']:
            raise ValueError('Existing canonical pipeline index required')
        blob = self.api('git/blobs/' + snapshot['management_sha'])
        management_text = base64.b64decode(blob['content']).decode()
        pattern = r'<!-- CRISP-MANAGEMENT-RECORD -->\s*```json\s*(.*?)\s*```'
        match = re.search(pattern, management_text, re.S)
        if not match:
            raise ValueError('Canonical pipeline index record required')
        management = json.loads(match.group(1))
        rows = [row for row in management.get('pipelines', [])
                if str(row.get('pipeline_id')) == storage['pipelineId']]
        if len(rows) != 1:
            raise ValueError('Pipeline identity must already have exactly one index entry')
        record = dict(record, storage=storage)
        text = snapshot['record_text']
        record_match = re.search(r'<!-- CRISP-PIPELINE-RECORD -->\s*```json\s*(.*?)\s*```', text, re.S)
        text = text[:record_match.start(1)] + json.dumps(record, indent=2) + text[record_match.end(1):]
        path = 'Pipeline_' + storage['pipelineId'] + '/PIPELINE.md'
        rows[0]['storage'] = storage
        rows[0]['record'] = dict(path=path, bytes=len(text.encode()), sha256=hashlib.sha256(text.encode()).hexdigest())
        management_text = (management_text[:match.start(1)] + json.dumps(management, indent=2)
                           + management_text[match.end(1):])
        tree = self.api('git/trees', dict(base_tree=snapshot['root'], tree=[
            dict(path=path, mode='100644', type='blob', content=text),
            dict(path='MANAGEMENT.md', mode='100644', type='blob', content=management_text)]))
        commit = self.api('git/commits', dict(message='Bind pipeline ' + storage['pipelineId'] + ' Drive storage',
            tree=tree['sha'], parents=[snapshot['head']]))
        self.api('git/refs/heads/main', dict(sha=commit['sha'], force=False), method='PATCH')
        observed = self.snapshot(storage['pipelineId'], commit=commit['sha'])
        self.verify_binding(storage, observed)
        return observed

    def commit(self, pipeline_id, snapshot, documents):
        prefix = 'Pipeline_' + pipeline_id + '/'
        changes = [dict(path=prefix + path, mode='100644', type='blob', content=content.decode())
                   for path, content in documents.items()
                   if snapshot['indexes'].get(path) != blob_sha(content)]
        changes += [dict(path=prefix + path, mode='100644', type='blob', sha=None)
                    for path in snapshot['indexes'] if path not in documents]
        if not changes:
            return None
        tree = self.api('git/trees', dict(base_tree=snapshot['root'], tree=changes))
        commit = self.api('git/commits', dict(message='Mirror pipeline ' + pipeline_id + ' Drive backup paths',
            tree=tree['sha'], parents=[snapshot['head']]))
        self.api('git/refs/heads/main', dict(sha=commit['sha'], force=False), method='PATCH')
        observed = self.snapshot(pipeline_id, commit=commit['sha'], read_indexes=False)
        expected = {path: blob_sha(content) for path, content in documents.items()}
        if observed['indexes'] != expected:
            raise RuntimeError('Published Git backup-index readback differs')
        return commit['sha']


def synchronize_backup_index(service, storage, *, overwrite=False, store=None, snapshot=None):
    storage = validate_storage(storage)
    if type(overwrite) is not bool:
        raise ValueError('Explicit Boolean overwrite required')
    store = GitHubBackupIndexStore() if store is None else store
    snapshot = store.snapshot(storage['pipelineId'], read_indexes=not overwrite) if snapshot is None else snapshot
    populated = snapshot['foreign_data']
    for content in snapshot['contents'].values():
        try:
            value = json.loads(content)
            populated = populated or not isinstance(value, dict) or bool(value)
        except (ValueError, UnicodeError):
            populated = True
    if populated and not overwrite:
        return dict(status='skipped', reason='existing-backup-data', pipelineId=storage['pipelineId'])
    store.verify_binding(storage, snapshot)
    if service is None:
        raise RuntimeError('Original authorized Drive client required to populate backup indexes')
    documents = drive_backup_indexes(service, storage['driveId'])
    commit = store.commit(storage['pipelineId'], snapshot, documents)
    return dict(status='published' if commit else 'unchanged', pipelineId=storage['pipelineId'],
                folders=len(documents), files=sum(len(json.loads(content)) for content in documents.values()),
                commit=commit)
