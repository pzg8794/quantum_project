"""Prepare existing pipeline metadata without I/O or execution."""
from copy import deepcopy
import base64
import hashlib
import json
import re

from daqr.config.pipeline_storage import validate_storage
from .registry import normalize_pipeline_id, validate_reference


def prepare_adoption(pipeline_record, workflow_document, indexed_entry, target_runs, own_tracker_ref):
    if not all(isinstance(value, dict) for value in (pipeline_record, workflow_document, indexed_entry)):
        raise ValueError('Existing record, workflow and index dictionaries required')
    number = normalize_pipeline_id(pipeline_record.get('pipeline_id'))
    if number not in (6, 152, 154, 155) or type(target_runs) is not int or target_runs != {6: 6, 152: 7, 154: 8, 155: 9}[number]:
        raise ValueError('Only the existing six through nine-run identities may be adopted')
    key = 'Pipeline_' + str(number)
    if workflow_document.get('pipeline') != key:
        raise ValueError('Workflow belongs to another pipeline')
    for identity in (indexed_entry.get('pipelineNumber'), (indexed_entry.get('table') or {}).get('pipelineNumber')):
        if identity is not None and normalize_pipeline_id(identity) != number:
            raise ValueError('Indexed pipeline identity differs')
    if (indexed_entry.get('pipelineStatus') or {}).get('pipeline', key) != key:
        raise ValueError('Indexed status belongs to another pipeline')
    version = indexed_entry.get('version')
    adopted_source = (workflow_document.get('infrastructure') or {}).get('sourceWorkflowRef')
    source = deepcopy(adopted_source or indexed_entry.get('workflowRef') or dict(
        repository='pzg8794/TAE_Workflow', commit=version, path='workflow.json'))
    source = validate_reference(source)
    if source.get('repository') != 'pzg8794/TAE_Workflow' or (not adopted_source and source.get('commit') != version) or source.get('path') != 'workflow.json':
        raise ValueError('Exact pinned indexed workflow required')
    tracker = deepcopy(own_tracker_ref)
    tracker = validate_reference(tracker)
    if tracker.get('repository') != 'pzg8794/ThreatAwareEvaluation' or re.fullmatch(
            r'executions/p' + str(number) + r'-[A-Za-z0-9_.-]+/index\.json', tracker.get('path', '')) is None:
        raise ValueError('Own immutable execution index required')
    storage = pipeline_record.get('storage')
    if storage is not None and validate_storage(storage)['pipelineId'] != str(number):
        raise ValueError('Storage belongs to another pipeline')
    infrastructure = dict(schema='pipeline-object-adoption/v1', pipelineId=number,
        targetRuns=target_runs, classHierarchy=['Pipeline', 'Workflow', 'Storage'],
        sourceWorkflowRef=source, trackerRef=tracker,
        storageState='linked' if storage is not None else 'pending-original-binding',
        executionPolicy=dict(resumeLevels=['experiment-runner', 'model'],
            skipCompleted=True, evaluatorResume=False))
    definitions = dict(cohorts=['S1T', 'S1.5T', 'S2T', 'S1Tb', 'S1.5Tb', 'S2Tb'],
        allocators=['Default', 'Random', 'Dynamic', 'ThompsonSampling'],
        threats=['none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive'],
        models=['Oracle', 'GNeuralUCB', 'EXPNeuralUCB', 'CPursuitNeuralUCB', 'iCPursuitNeuralUCB'],
        observed=False)
    record, workflow = deepcopy(pipeline_record), deepcopy(workflow_document)
    for document, additions in ((record, {'infrastructure': infrastructure}),
            (workflow, {'infrastructure': infrastructure, 'objectDefinitions': definitions})):
        for field, value in additions.items():
            if field in document and document[field] != value:
                previous = document[field]
                storage_link = (field == 'infrastructure' and storage is not None
                    and isinstance(previous, dict)
                    and previous.get('storageState') == 'pending-original-binding'
                    and dict(previous, storageState='linked') == value)
                if not storage_link:
                    raise ValueError('Existing adoption metadata differs: ' + field)
            document[field] = deepcopy(value)
    return dict(workflow=workflow, record=record)


class PipelineAdoptionPublisher:
    """Explicit metadata publication; never provision storage or execute science."""

    @staticmethod
    def _encode(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'

    @staticmethod
    def _read(store, commit, path):
        result = store.api('contents/' + path + '?ref=' + commit)
        if result.get('encoding') == 'none' or not result.get('content') and result.get('size', 0) > 0:
            result = store.api('git/blobs/' + result['sha'])
        content = base64.b64decode(''.join(result['content'].split()), validate=True)
        if len(content) > 8 * 1024 * 1024:
            raise ValueError('Bounded pipeline metadata required')
        if re.fullmatch(r'[a-f0-9]{40}', result.get('sha', '')):
            from daqr.config.pipeline_backup_index import blob_sha
            if blob_sha(content) != result['sha']:
                raise ValueError('Pinned metadata content identity differs')
        return content.decode()

    @staticmethod
    def _block(text, marker):
        match = re.search(r'<!-- ' + re.escape(marker) + r' -->\s*```json\s*(.*?)\s*```', text, re.S)
        if match is None:
            raise ValueError('Original structured metadata block required')
        return match, json.loads(match.group(1))

    @staticmethod
    def _head(store):
        return store.api('git/ref/heads/main')['object']['sha']

    def _commit(self, store, head, tree, message):
        revision = store.api('git/commits', dict(tree=tree, parents=[head], message=message))['sha']
        return revision

    def _advance(self, store, head, revision):
        if self._head(store) != head:
            raise ValueError('Branch advanced; reconcile before retrying adoption')
        store.api('git/refs/heads/main', dict(sha=revision, force=False), method='PATCH')

    def publish(self, pipeline, payload):
        from daqr.config.tae_workflow import WorkflowStore

        stores = pipeline._registry._stores
        canonical, workflows = stores['pzg8794/quantum-pipelines'], stores['pzg8794/TAE_Workflow']
        reference = validate_reference(pipeline.pipeline_reference)
        if reference['repository'] != canonical.repository:
            raise ValueError('Canonical pipeline repository required')
        head = self._head(canonical)
        if head != reference['commit']:
            raise ValueError('Canonical pipeline head changed; reload before adoption')
        original_text = self._read(canonical, head, reference['path'])
        record_match, original_record = self._block(original_text, 'CRISP-PIPELINE-RECORD')
        number = normalize_pipeline_id(original_record.get('pipeline_id'))
        key = 'Pipeline_' + str(number)
        if reference['path'] != key + '/PIPELINE.md':
            raise ValueError('Exact canonical pipeline path required')
        workflow_head, index, original_workflow = WorkflowStore.load(workflows, key)
        entry = deepcopy(index[key])
        infrastructure = payload['workflow']['infrastructure']
        expected = prepare_adoption(original_record, original_workflow, entry,
            infrastructure['targetRuns'], infrastructure['trackerRef'])
        if payload != expected:
            raise ValueError('Payload must preserve exact current pipeline and workflow metadata')
        management_text = self._read(canonical, head, 'MANAGEMENT.md')
        management_match, management = self._block(management_text, 'CRISP-MANAGEMENT-RECORD')
        rows = [row for row in management['pipelines'] if row.get('pipeline_id') == number]
        if len(rows) != 1 or 'pipelineStatus' not in entry:
            raise ValueError('Unique original management row and exact indexed status required')
        status = deepcopy(entry['pipelineStatus'])
        definitions = payload['workflow']['objectDefinitions']
        if original_workflow == payload['workflow'] and entry.get('infrastructureRef'):
            version = entry['version']
        else:
            root = workflows.api('git/commits/' + workflow_head)['tree']['sha']
            root_tree = workflows.api('git/trees/' + root)
            if root_tree.get('truncated'):
                raise ValueError('Complete workflow root tree required')
            globals_only = {'index.json', 'status-default-Spectrum.json', 'status-default-nonSpectrum.json'}
            tree = [{field: item[field] for field in ('path', 'mode', 'type', 'sha')}
                for item in root_tree['tree'] if item['path'] in globals_only and item['type'] == 'blob']
            if {item['path'] for item in tree} != globals_only:
                raise ValueError('Existing global index and defaults blobs required')
            files = {'workflow.json': payload['workflow'], 'pipeline_status.json': status,
                'infrastructure.json': infrastructure, 'object_definitions.json': definitions}
            for cohort in definitions['cohorts']:
                files['cohorts/' + cohort + '/definition.json'] = dict(
                    pipelineId=number, cohort=cohort, observed=False,
                    allocators=deepcopy(definitions['allocators']), threats=deepcopy(definitions['threats']),
                    models=deepcopy(definitions['models']))
            tree.extend(dict(path=path, mode='100644', type='blob', content=self._encode(value))
                for path, value in files.items())
            own_tree = workflows.api('git/trees', dict(tree=tree))['sha']
            version = self._commit(workflows, workflow_head, own_tree, 'Adopt ' + key + ' metadata')
            entry['version'] = version
            for field, path in (('workflowRef', 'workflow.json'), ('statusRef', 'pipeline_status.json'),
                    ('infrastructureRef', 'infrastructure.json')):
                entry[field] = dict(repository=workflows.repository, commit=version, path=path)
            entry['infrastructure'] = deepcopy(infrastructure)
            index = deepcopy(index)
            index[key] = entry
            indexed_tree = workflows.api('git/trees', dict(base_tree=own_tree, tree=[dict(
                path='index.json', mode='100644', type='blob', content=self._encode(index))]))['sha']
            final = self._commit(workflows, version, indexed_tree, 'Index adopted ' + key)
            self._advance(workflows, workflow_head, final)
            if json.loads(self._read(workflows, final, 'index.json')) != index:
                raise RuntimeError('Published workflow index readback differs; preserve published version')
        for path, value in (('workflow.json', payload['workflow']), ('pipeline_status.json', status)):
            if json.loads(self._read(workflows, version, path)) != value:
                raise RuntimeError('Published workflow readback differs; canonical publication withheld')
        record = deepcopy(payload['record'])
        record['workflowRef'] = deepcopy(entry['workflowRef'])
        updated_text = original_text[:record_match.start(1)] + self._encode(record).rstrip() + original_text[record_match.end(1):]
        row = rows[0]
        row['record'] = dict(row.get('record') or {}, path=reference['path'],
            bytes=len(updated_text.encode()), sha256=hashlib.sha256(updated_text.encode()).hexdigest())
        row['infrastructure'], row['workflowRef'] = deepcopy(infrastructure), deepcopy(entry['workflowRef'])
        updated_management = management_text[:management_match.start(1)] + self._encode(management).rstrip() + management_text[management_match.end(1):]
        if updated_text == original_text and updated_management == management_text:
            return dict(pipelineId=number, workflowRef=deepcopy(entry['workflowRef']), pipelineCommit=head, changed=False)
        base = canonical.api('git/commits/' + head)['tree']['sha']
        tree = canonical.api('git/trees', dict(base_tree=base, tree=[dict(path=path,
            mode='100644', type='blob', content=content) for path, content in
            ((reference['path'], updated_text), ('MANAGEMENT.md', updated_management))]))['sha']
        revision = self._commit(canonical, head, tree, 'Link adopted ' + key + ' metadata')
        self._advance(canonical, head, revision)
        for path, value in ((reference['path'], updated_text), ('MANAGEMENT.md', updated_management)):
            if self._read(canonical, revision, path) != value:
                raise RuntimeError('Canonical publication readback differs; preserve published commits')
        return dict(pipelineId=number, workflowRef=deepcopy(entry['workflowRef']), pipelineCommit=revision, changed=True)
