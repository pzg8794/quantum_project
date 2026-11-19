"""Read-only resolution of the existing pipeline and workflow Git records."""
import base64
from copy import deepcopy
import json
import hashlib
import re
from urllib.parse import quote

from daqr.config.pipeline_backup_index import GitHubBackupIndexStore, blob_sha
from daqr.config.pipeline_storage import validate_storage


def normalize_pipeline_id(pipeline_id):
    if type(pipeline_id) not in (int, str):
        raise ValueError('A positive pipeline ID is required')
    match = re.fullmatch(r'(?:Pipeline_)?([1-9][0-9]*)', str(pipeline_id))
    if match is None:
        raise ValueError('A positive pipeline ID is required')
    return int(match.group(1))


def validate_component_name(name):
    if (not isinstance(name, str) or name in ('.', '..')
            or re.fullmatch(r'[A-Za-z0-9_.:-]+', name) is None):
        raise ValueError('A component name is required')
    return name


def validate_reference(reference):
    if not isinstance(reference, dict):
        raise ValueError('An immutable Git reference is required')
    result = deepcopy(reference)
    repository = result.get('repository', result.get('repo'))
    path = result.get('path')
    commit = result.get('commit')
    if (not isinstance(repository, str)
            or re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) is None
            or not isinstance(commit, str) or re.fullmatch(r'[a-f0-9]{40}', commit) is None
            or not isinstance(path, str) or not path or path.startswith('/')
            or any(part in ('', '.', '..') for part in path.split('/'))
            or any(character in path for character in ('\\', '\0', '?', '#', '\n', '\r'))):
        raise ValueError('An immutable Git reference with a safe relative path is required')
    result['repository'] = repository
    result.pop('repo', None)
    return result


class PipelineRegistry:
    """Cache metadata from the existing repositories; perform no writes."""

    pipeline_repository = 'pzg8794/quantum-pipelines'
    workflow_repository = 'pzg8794/TAE_Workflow'

    def __init__(self, *, pipeline_store=None, workflow_store=None):
        self._stores = {}
        for repository, store in ((self.pipeline_repository, pipeline_store),
                                  (self.workflow_repository, workflow_store)):
            if store is None:
                store = GitHubBackupIndexStore()
                store.repository = repository
            if store.repository != repository:
                raise ValueError('Metadata store belongs to a different repository')
            self._stores[repository] = store
        self._heads = {}
        self._contents = {}
        self._resources = {}
        self._workflow_index = None

    def _index(self):
        if self._workflow_index is None:
            reference = dict(repository=self.workflow_repository,
                commit=self._head(self.workflow_repository), path='index.json')
            index = self.read_json(reference)
            for key in index:
                if not isinstance(key, str) or re.fullmatch(r'Pipeline_[1-9][0-9]*', key) is None:
                    raise ValueError('The workflow index must contain exact pipeline keys')
            self._workflow_index = index
        return self._workflow_index

    def pipeline_ids(self):
        return sorted(normalize_pipeline_id(key) for key in self._index())

    def _head(self, repository):
        if repository not in self._heads:
            head = self._stores[repository].api('git/ref/heads/main')['object']['sha']
            if not isinstance(head, str) or re.fullmatch(r'[a-f0-9]{40}', head) is None:
                raise ValueError('A pinned metadata repository commit is required')
            self._heads[repository] = head
        return self._heads[repository]

    def _read(self, reference):
        reference = validate_reference(reference)
        repository, commit, path = (reference[name] for name in ('repository', 'commit', 'path'))
        if repository not in self._stores:
            raise ValueError('No existing metadata store is configured for this reference')
        key = repository, commit, path
        if key not in self._contents:
            response = self._stores[repository].api('contents/' + quote(path, safe='/') + '?ref=' + commit)
            if response.get('encoding') != 'base64' or not isinstance(response.get('content'), str):
                raise ValueError('A Git file response is required')
            content = base64.b64decode(response['content'])
            if blob_sha(content) != response.get('sha'):
                raise ValueError('Git metadata content identity differs')
            self._contents[key] = content
        content = self._contents[key]
        if reference.get('sha256') is not None and hashlib.sha256(content).hexdigest() != reference['sha256']:
            raise ValueError('Recorded metadata SHA256 differs')
        return content

    def read_json(self, reference):
        value = json.loads(self._read(reference))
        if not isinstance(value, dict):
            raise ValueError('A metadata dictionary is required')
        return value

    def resolve(self, pipeline_id):
        pipeline_id = normalize_pipeline_id(pipeline_id)
        if pipeline_id not in self._resources:
            key = 'Pipeline_' + str(pipeline_id)
            reference = dict(repository=self.pipeline_repository,
                commit=self._head(self.pipeline_repository), path=key + '/PIPELINE.md')
            content = self._read(reference).decode()
            match = re.search(r'<!-- CRISP-PIPELINE-RECORD -->\s*```json\s*(.*?)\s*```', content, re.S)
            if match is None:
                raise ValueError('The registered structured pipeline record is required')
            record = json.loads(match.group(1))
            if (not isinstance(record, dict) or record.get('schema') != 'quantum-crisp-pipeline/v1'
                    or normalize_pipeline_id(record.get('pipeline_id')) != pipeline_id):
                raise ValueError('Registered pipeline identity differs')
            storage = record.get('storage')
            if storage is not None:
                storage = validate_storage(storage)
                if storage['pipelineId'] != str(pipeline_id):
                    raise ValueError('Drive storage belongs to a different pipeline')
            index_reference = dict(repository=self.workflow_repository,
                commit=self._head(self.workflow_repository), path='index.json')
            entry = self._index().get(key)
            if entry is not None:
                if not isinstance(entry, dict):
                    raise ValueError('The indexed workflow must be a dictionary')
                workflow_reference = validate_reference(entry.get('workflowRef') or dict(
                    repository=self.workflow_repository, commit=entry.get('version'), path='workflow.json'))
                if (workflow_reference['repository'] != self.workflow_repository
                        or workflow_reference['commit'] != entry.get('version')
                        or workflow_reference['path'] != 'workflow.json'
                        or (entry.get('table') or {}).get('pipelineNumber', pipeline_id) != pipeline_id):
                    raise ValueError('Indexed workflow identity or version differs')
            else:
                workflow_reference = None
            status_reference = (entry or {}).get('statusRef')
            if status_reference is not None:
                status_reference = validate_reference(status_reference)
                if (status_reference['repository'] != self.workflow_repository
                        or status_reference['commit'] != entry.get('version')
                        or status_reference['path'] != 'pipeline_status.json'):
                    raise ValueError('Indexed workflow status identity or version differs')
            status = (entry or {}).get('pipelineStatus')
            if status is not None and (not isinstance(status, dict) or status.get('pipeline', key) != key):
                raise ValueError('Indexed status belongs to a different pipeline')
            progress = ((entry or {}).get('table') or {}).get('progressSource') or {}
            if (progress.get('pipelineNumber') is not None
                    and normalize_pipeline_id(progress['pipelineNumber']) != pipeline_id):
                raise ValueError('Runner execution belongs to a different pipeline')
            runner_reference = (entry or {}).get('runnerRef') or record.get('runnerRef') or progress.get('sourceRef')
            if runner_reference is not None:
                runner_reference = validate_reference(runner_reference)
                if runner_reference['repository'] != 'pzg8794/pipeline_runner':
                    raise ValueError('Runner reference belongs to a different repository')
                owners = [runner_reference[field] for field in ('pipelineId', 'pipeline_id', 'pipelineNumber')
                    if field in runner_reference]
                owners.extend(re.findall(r'Pipeline[_-]?([1-9][0-9]*)', runner_reference['path']))
                if any(normalize_pipeline_id(owner) != pipeline_id for owner in owners):
                    raise ValueError('Runner reference belongs to a different pipeline')
                if not owners and (runner_reference['path'] != 'RUNS.md'
                        or ((entry or {}).get('table') or {}).get('pipelineNumber') != pipeline_id
                        or not isinstance(progress.get('jobId'), str) or not progress['jobId']):
                    raise ValueError('An explicitly pipeline-bound runner reference is required')
            self._resources[pipeline_id] = dict(pipeline_id=pipeline_id, pipeline_key=key,
                pipeline_reference=reference, record=record, storage=storage,
                workflow_entry=entry, workflow_reference=workflow_reference,
                workflow_index_reference=index_reference, workflow_status_reference=status_reference,
                runner_reference=runner_reference,
                runner_execution_id=progress.get('jobId'))
        return deepcopy(self._resources[pipeline_id])
