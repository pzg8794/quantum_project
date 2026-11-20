import base64
import hashlib
import json
import re

from p155_github_checkpoint_store import GitHubCheckpointStore


class CohortVersions(GitHubCheckpointStore):
    def __init__(self, owner, cohort):
        if cohort not in self.cohorts:
            raise ValueError('Unknown cohort')
        self.cohort = cohort
        super().__init__(f'{owner}/tae-cohort-{cohort.lower().replace(".", "-")}')

    def open_pipeline(self, pipeline_key, execution_id):
        if not re.fullmatch(r'pipeline-[1-9][0-9]*', pipeline_key):
            raise ValueError('Expected pipeline-<number>')
        if not execution_id:
            raise ValueError('Expected the pipeline execution identity')
        head = self._api('/git/ref/heads/main')['object']['sha']
        tree = self._api('/git/commits/' + head)['tree']['sha']
        if tree == self.empty_tree_sha:
            index = dict(cohort=self.cohort, pipelines={})
        else:
            index = self._read_index('index.json', head)
            if index['cohort'] != self.cohort:
                raise ValueError('Wrong cohort index')
        published = index['pipelines'].get(pipeline_key)
        experiments = {}
        if published:
            snapshot = self._read_index(published['index'], published['commit'])
            if (snapshot['cohort'], snapshot['pipeline'], snapshot['execution']) != (
                    self.cohort, pipeline_key, execution_id):
                raise ValueError('Wrong pipeline snapshot')
            experiments = snapshot['experiments']
        return PipelineCohort(self, pipeline_key, execution_id, head, tree, index, experiments)

    def _read_index(self, path, commit):
        result = self._api(f'/contents/{path}?ref={commit}')
        return json.loads(base64.b64decode(result['content']))

    def _commit(self, parent, tree, files, message):
        entries = []
        for path, content in files.items():
            blob = self._api('/git/blobs', payload=dict(
                content=base64.b64encode(content).decode(), encoding='base64'))['sha']
            entries.append(dict(path=path, mode='100644', type='blob', sha=blob))
        payload = dict(tree=entries)
        if tree != self.empty_tree_sha:
            payload['base_tree'] = tree
        tree = self._api('/git/trees', payload=payload)['sha']
        commit = self._api('/git/commits', payload=dict(
            message=message, tree=tree, parents=[parent]))['sha']
        return commit, tree


class PipelineCohort:
    def __init__(self, store, pipeline, execution, head, tree, index, experiments):
        self.store = store
        self.pipeline = pipeline
        self.execution = execution
        self.head = head
        self.tree = tree
        self.index = index
        self.experiments = experiments

    def lookup(self, experiment_key):
        return self.experiments.get(experiment_key)

    def read_log(self, experiment_key):
        content = self._read_artifact(experiment_key, 'log')
        return None if content is None else content.decode('utf-8')

    def read_state(self, experiment_key):
        return self._read_artifact(experiment_key, 'state')

    def _read_artifact(self, experiment_key, kind):
        reference = (self.lookup(experiment_key) or {}).get(kind)
        if reference is None:
            return None
        return self.store.read(reference['commit'], reference['path'],
                               reference['size'], reference['sha256'])

    def publish_finished(self, experiment_key, state_path, log_path=None):
        if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*', experiment_key):
            raise ValueError('Expected allocator/threat/experiment-number')
        if state_path.suffix != '.pkl':
            raise ValueError('Expected an original experiment checkpoint')
        previous = self.lookup(experiment_key) or {}
        files = {}
        references = dict(previous)
        scope = f'{self.pipeline}/{experiment_key}'
        for kind, source in (('state', state_path), ('log', log_path)):
            if source is None:
                continue
            if source.stat().st_size > 50 * 1024**2:
                raise ValueError(f'{kind} exceeds the cohort Git storage budget')
            data = source.read_bytes()
            if not data:
                raise ValueError(f'Empty experiment {kind}')
            if kind == 'log':
                data.decode('utf-8')
            digest = hashlib.sha256(data).hexdigest()
            if kind in previous and previous[kind] is not None:
                if previous[kind]['sha256'] != digest:
                    raise ValueError(f'Refusing to replace a published experiment {kind}')
                continue
            path = f'{scope}/{source.name}' if kind == 'state' else f'{scope}/experiment.log'
            files[path] = data
            references[kind] = dict(path=path, size=len(data), sha256=digest)
        if not files:
            return False
        references.setdefault('log', None)
        data_commit, tree = self.store._commit(self.head, self.tree, files,
                                               f'{self.pipeline}: {experiment_key} artifacts')
        for reference in references.values():
            if reference is not None:
                reference.setdefault('commit', data_commit)
        experiments = {**self.experiments, experiment_key: references}
        snapshot_path = f'{self.pipeline}/experiments.json'
        snapshot = dict(cohort=self.store.cohort, pipeline=self.pipeline, execution=self.execution,
                        experiments=experiments)
        snapshot_commit, tree = self.store._commit(data_commit, tree,
            {snapshot_path: json.dumps(snapshot, sort_keys=True).encode()}, f'{self.pipeline}: experiment index')
        index = dict(self.index, latest=self.pipeline, pipelines={**self.index['pipelines'],
            self.pipeline: dict(commit=snapshot_commit, index=snapshot_path)})
        head, tree = self.store._commit(snapshot_commit, tree,
            {'index.json': json.dumps(index, sort_keys=True).encode()}, f'{self.pipeline}: publish cohort version')
        self.store._api('/git/refs/heads/main', payload=dict(sha=head, force=False), method='PATCH')
        self.head, self.tree, self.index, self.experiments = head, tree, index, experiments
        return True
