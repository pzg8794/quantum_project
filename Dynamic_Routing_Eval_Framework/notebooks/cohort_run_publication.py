import base64
import hashlib
import json
import re
from urllib.error import HTTPError

from cohort_versions import CohortVersions
from p155_github_checkpoint_store import CohortCheckpointSearch, GitHubCheckpointStore


class SharedCohortStore(CohortVersions):
    def __init__(self, repository=GitHubCheckpointStore.shared_repository):
        GitHubCheckpointStore.__init__(self, repository)

    @staticmethod
    def encode(document):
        return json.dumps(document, sort_keys=True).encode()

    def ref(self, name):
        try:
            return self._api('/git/ref/' + name)['object']['sha']
        except HTTPError as error:
            if error.code != 404:
                raise
            return None

    def tree(self, commit):
        return self._api('/git/commits/' + commit)['tree']['sha']

    def advance(self, ref, commit):
        self._api('/git/refs/' + ref, payload=dict(sha=commit, force=False), method='PATCH')

    def update_index(self, edit, *, before_push=None):
        for attempt in range(5):
            head = self.ref('heads/main')
            index = self._read_index('index.json', head)
            if not edit(index):
                return attempt
            commit, _ = self._commit(head, self.tree(head), {'index.json': self.encode(index)},
                                     'Update pinned pipeline cohort versions')
            if before_push is not None and not attempt:
                before_push()
            try:
                self.advance('heads/main', commit)
            except HTTPError as error:
                if error.code not in (409, 422) or self.ref('heads/main') == head:
                    raise
            else:
                return attempt
        raise RuntimeError('Shared cohort index changed repeatedly; retry publication')

    def open_run(self, pipeline, execution, cohort):
        if (not re.fullmatch(r'pipeline-[1-9][0-9]*', pipeline)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', execution)
                or cohort not in self.cohorts):
            raise ValueError('Invalid pipeline/cohort execution identity')
        identity = dict(pipeline=pipeline, execution=execution, cohort=cohort)
        branch = f'runs/{pipeline}/{execution}/{cohort}'
        head = self.ref('heads/' + branch)
        index = self._read_index('index.json', self.ref('heads/main'))
        prior = index['pipelines'].get(pipeline)
        if prior and prior['execution'] != execution:
            raise ValueError('Pipeline key is already bound to another execution')
        published = prior['cohorts'].get(cohort) if prior else None
        if head is None:
            base = published['commit'] if published else self.ref('heads/cohort/' + cohort)
            document = (self._read_index('run.json', base) if published and published.get('tag')
                        else dict(identity, experiments={}))
            head, _ = self._commit(base, self.tree(base), {'run.json': self.encode(document)},
                                   f'Open {branch}')
            try:
                self._api('/git/refs', payload=dict(ref='refs/heads/' + branch, sha=head))
            except HTTPError as error:
                head = self.ref('heads/' + branch)
                if error.code not in (409, 422) or head is None:
                    raise
        return RunCohort(self, identity, branch, head, published)

    def open_published(self, pipeline, execution, cohort):
        reference = self.pipeline_cohorts(pipeline, execution)[cohort]
        if not reference.get('tag') or self.ref('tags/' + reference['tag']) != reference['commit']:
            raise ValueError('No verified run snapshot for this cohort')
        return RunCohort(self, dict(pipeline=pipeline, execution=execution, cohort=cohort),
                         reference['branch'], reference['commit'], reference)


class RunCohort:
    def __init__(self, store, identity, branch, head, prior):
        self.store, self.identity, self.branch, self.head, self.prior = store, identity, branch, head, prior
        document = store._read_index('run.json', head)
        if any(document[key] != value for key, value in identity.items()):
            raise ValueError('Run snapshot belongs to another execution')
        self.experiments = document['experiments']

    def recovery_search(self, experiment_key, directory, commit):
        if self.identity['pipeline'] != 'pipeline-155' or self.identity['cohort'] != 'S2T':
            raise ValueError('Recovery snapshot is scoped to Pipeline 155 S2T')
        allocator, threat, position = experiment_key.split('/')
        labels = {'adaptive': 'Adversarial_Adaptive', 'markov': 'Adversarial_Markov',
                  'stochastic': 'Stochastic_Random'}
        if allocator != 'Dynamic' or position != '9' or threat not in labels:
            return None
        tag = f"recovery/pipeline-155/{self.identity['execution']}/S2T/{commit}"
        if self.store.ref('tags/' + tag) != commit:
            raise ValueError('Recovery snapshot tag differs')
        manifest = self.store._read_index('recovery/Dynamic/manifest.json', commit)
        if any(manifest.get(key) != value for key, value in self.identity.items()) or manifest.get('allocator') != allocator:
            raise ValueError('Recovery manifest identity differs')
        entries = []
        for relative, reference in manifest['files'].items():
            component, day, filename = relative.split('/')
            if reference['path'] != 'recovery/Dynamic/' + relative:
                raise ValueError('Recovery artifact path differs')
            if f'-Dynamic_{labels[threat]}-' in filename:
                entries.append(dict(reference, path=f'quantum_data_lake/{component}/{day}/{filename}',
                                    original_path=reference['path']))
        cache = directory / f'{commit}-{threat}'
        cache.mkdir(exist_ok=True)
        return _RunCheckpointSearch(self.store, commit, entries, cache)

    def checkpoint_search(self, experiment_key, directory):
        if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*', experiment_key):
            raise ValueError('Expected allocator/threat/experiment-number')
        record = self.experiments.get(experiment_key, {})
        entries = []
        for component, references in (
            ('framework_state', [record['state']] if record.get('state') else []),
            ('model_state', record.get('models', {}).values()),
        ):
            for reference in references:
                filename = reference['path'].rsplit('/', 1)[-1]
                if not reference['path'].startswith(f'experiments/{experiment_key}/'):
                    raise ValueError('Checkpoint path belongs to another experiment')
                entries.append(dict(reference, path=f'quantum_data_lake/{component}/pinned/{filename}',
                                    original_path=reference['path']))
        cache_key = hashlib.sha256(f'{self.head}:{experiment_key}'.encode()).hexdigest()
        cache = directory / cache_key
        cache.mkdir(exist_ok=True)
        return _RunCheckpointSearch(self.store, self.head, entries, cache)

    def read(self, key, kind):
        item = self.experiments.get(key, {}).get(kind)
        if item is None:
            return None
        return self.store.read(self.head, item['path'], item['size'], item['sha256'])

    def save_finished(self, key, checkpoint, log=None, *, models=None, evaluator=None):
        if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*', key):
            raise ValueError('Expected allocator/threat/experiment-number')
        if checkpoint.suffix != '.pkl':
            raise ValueError('Expected an original experiment checkpoint')
        files, record = {}, dict(self.experiments.get(key, {}))
        for kind, source in (('state', checkpoint), ('log', log)):
            if source is None:
                continue
            if not 0 < source.stat().st_size <= 50 * 1024**2:
                raise ValueError(f'Invalid experiment {kind} size')
            data = source.read_bytes()
            if kind == 'log':
                data.decode('utf-8')
            digest = hashlib.sha256(data).hexdigest()
            if record.get(kind) is not None:
                if record[kind]['sha256'] == digest:
                    continue
                if kind != 'log':
                    raise ValueError(f'Refusing to replace existing experiment {kind}')
            path = f'experiments/{key}/{source.name if kind == "state" else "experiment.log"}'
            files[path] = data
            record[kind] = dict(path=path, size=len(data), sha256=digest)
        if models is not None:
            model_records = dict(record.get('models', {}))
            for name, source in models.items():
                if name != source.name or not re.fullmatch(r'[^/\\\x00-\x1f]+\.pkl', name):
                    raise ValueError('Exact original model filename required')
                if not 0 < source.stat().st_size <= 50 * 1024**2:
                    raise ValueError('Invalid model checkpoint size')
                data = source.read_bytes()
                path = f'experiments/{key}/models/{name}'
                reference = dict(path=path, size=len(data), sha256=hashlib.sha256(data).hexdigest())
                if name in model_records and model_records[name] != reference:
                    raise ValueError('Refusing to replace a published model checkpoint')
                if name not in model_records:
                    files[path] = data
                model_records[name] = reference
            record['models'] = model_records
        previous = self.experiments.get(key)
        if evaluator is not None:
            record['evaluator'] = evaluator
        if not files and record == previous:
            return False
        record.setdefault('log', None)
        experiments = {**self.experiments, key: record}
        files['run.json'] = self.store.encode(dict(self.identity, experiments=experiments))
        head, _ = self.store._commit(self.head, self.store.tree(self.head), files, f'Save {key}')
        self.store.advance('heads/' + self.branch, head)
        self.head, self.experiments = head, experiments
        return True

    def publish(self, *, before_push=None):
        if not self.experiments or self.store.ref('heads/' + self.branch) != self.head:
            raise ValueError('Publish only a current, nonempty run branch')
        pipeline, execution, cohort = (self.identity[key] for key in ('pipeline', 'execution', 'cohort'))
        tag = f'versions/{pipeline}/{execution}/{cohort}/{self.head}'
        if self.store.ref('tags/' + tag) is None:
            try:
                self.store._api('/git/refs', payload=dict(ref='refs/tags/' + tag, sha=self.head))
            except HTTPError as error:
                if error.code not in (409, 422) or self.store.ref('tags/' + tag) != self.head:
                    raise
        if self.store.ref('tags/' + tag) != self.head:
            raise ValueError('Immutable snapshot tag does not match its commit')
        reference = dict(branch='cohort/' + cohort, commit=self.head, tag=tag)

        def edit(index):
            entry = index['pipelines'].setdefault(pipeline, dict(execution=execution, cohorts={}))
            if entry['execution'] != execution:
                raise ValueError('Pipeline key is already bound to another execution')
            current = entry['cohorts'].get(cohort)
            if current == reference:
                return False
            if current != self.prior:
                raise ValueError('Cohort version changed; refusing to replace a newer snapshot')
            entry['cohorts'][cohort] = reference
            return True

        retries = self.store.update_index(edit, before_push=before_push)
        if self.store.pipeline_cohorts(pipeline, execution)[cohort] != reference:
            raise ValueError('Published cohort version failed readback')
        self.prior = reference
        return retries


class _RunCheckpointSearch(CohortCheckpointSearch):
    def lookup(self, component, filename):
        key = (component, filename)
        matches = self.entries.get(key, [])
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError('Ambiguous pinned checkpoint: ' + filename)
        if key not in self.staged:
            reference = dict(matches[0], path=matches[0]['original_path'])
            directory = self.directory / component
            directory.mkdir(exist_ok=True)
            path = directory / filename
            if path.is_file():
                data = path.read_bytes()
                if len(data) != reference['size'] or hashlib.sha256(data).hexdigest() != reference['sha256']:
                    raise ValueError('Cached checkpoint integrity check failed')
            else:
                path = self.store.stage(self.commit, reference, directory)
            self.staged[key] = path
        return str(self.staged[key])
