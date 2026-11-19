import base64
import hashlib
import json
import re
import subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen


class GitHubCheckpointStore:
    shared_repository = 'pzg8794/tae-cohort-checkpoints'
    cohorts = ('S1T', 'S1.5T', 'S2T', 'S1Tb', 'S1.5Tb', 'S2Tb')
    empty_tree_sha = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

    def __getstate__(self):
        raise TypeError('Authenticated checkpoint clients must not be serialized')

    def __init__(self, repository):
        self.repository = repository
        self._token = subprocess.check_output(['gh', 'auth', 'token'], text=True, timeout=15).strip()
        if not self._api('')['private']:
            raise ValueError('Checkpoint repository must be private')

    def _api(self, path, *, payload=None, method=None):
        request = Request(
            'https://api.github.com/repos/' + self.repository + path,
            data=None if payload is None else json.dumps(payload).encode(),
            method=method,
            headers={'Authorization': 'Bearer ' + self._token,
                     'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json'})
        with urlopen(request, timeout=60) as response:
            if response.status == 204:
                return None
            return json.load(response)

    def branch_commit(self, cohort, *, create=False):
        if cohort not in self.cohorts:
            raise ValueError('Unknown cohort')
        branch = 'cohort/' + cohort
        branches = {item['name']: item['commit']['sha']
                    for item in self._api('/branches?per_page=100')}
        if branch in branches:
            return branches[branch]
        if not create:
            raise LookupError('Cohort branch is not provisioned: ' + branch)
        return self._api('/git/refs', payload={'ref': 'refs/heads/' + branch,
                                              'sha': branches['main']})['object']['sha']

    def read(self, commit, path, length, sha256):
        url = ('https://api.github.com/repos/' + self.repository + '/contents/'
               + quote(path) + '?ref=' + quote(commit))
        request = Request(url, headers={'Authorization': 'Bearer ' + self._token,
                                        'Accept': 'application/vnd.github.raw+json'})
        with urlopen(request, timeout=90) as response:
            data = response.read(length + 1)
        if len(data) != length or hashlib.sha256(data).hexdigest() != sha256:
            raise ValueError('Checkpoint content differs: ' + path)
        return data

    def manifest(self, cohort, commit):
        entry = self._api('/contents/drive-checkpoints.json?ref=' + quote(commit))
        document = json.loads(base64.b64decode(entry['content']))
        if document['cohort'] != cohort:
            raise ValueError('Checkpoint manifest belongs to a different cohort')
        return document['checkpoints']

    def pipeline_cohorts(self, pipeline_key, execution_id):
        entry = self._api('/contents/index.json?ref=main')
        index = json.loads(base64.b64decode(entry['content']))
        version = index['pipelines'][pipeline_key]
        if version['execution'] != execution_id:
            raise ValueError('Wrong pipeline execution')
        for cohort, reference in version['cohorts'].items():
            if (cohort not in self.cohorts or reference['branch'] != 'cohort/' + cohort
                    or not re.fullmatch('[0-9a-f]{40}', reference['commit'])):
                raise ValueError('Invalid pinned cohort reference')
        return version['cohorts']

    def stage(self, commit, entry, directory):
        path = directory / entry['path'].rsplit('/', 1)[-1]
        data = self.read(commit, entry['path'], entry['size'], entry['sha256'])
        with path.open('xb') as stream:
            stream.write(data)
        return path

    def stage_model_states(self, commit, entries, directory):
        by_filename = {}
        for entry in entries:
            if not entry['path'].startswith('quantum_data_lake/model_state/'):
                raise ValueError('Expected an original model-state path')
            filename = entry['path'].rsplit('/', 1)[-1]
            if filename in by_filename:
                raise ValueError('Select an exact saved model version: ' + filename)
            by_filename[filename] = entry
        return {filename: str(self.stage(commit, entry, directory))
                for filename, entry in by_filename.items()}

    def open_cohort(self, cohort, directory, *, create=False):
        commit = self.branch_commit(cohort, create=create)
        return self.open_cohort_version(cohort, commit, directory)

    def open_cohort_version(self, cohort, commit, directory):
        tree_sha = self._api('/git/commits/' + quote(commit))['tree']['sha']
        entries = [] if tree_sha == self.empty_tree_sha else self.manifest(cohort, commit)
        cache = directory / cohort
        cache.mkdir(exist_ok=True)
        return CohortCheckpointSearch(self, commit, entries, cache)


class CohortCheckpointSearch:
    def __init__(self, store, commit, entries, directory):
        self.store = store
        self.commit = commit
        self.directory = directory
        self.entries = {}
        self.git_backup_registry = {'framework_state': {}, 'model_state': {}}
        self.staged = {}
        for entry in entries:
            parts = entry['path'].split('/')
            if (len(parts) != 4 or parts[0] != 'quantum_data_lake'
                    or parts[1] not in ('framework_state', 'model_state')
                    or any(part in ('', '.', '..') for part in parts)):
                raise ValueError('Unexpected checkpoint path')
            self.entries.setdefault((parts[1], parts[-1]), []).append(entry)
            self.git_backup_registry[parts[1]][parts[-1]] = self.entries[(parts[1], parts[-1])]

    def lookup(self, component, filename):
        key = (component, filename)
        matches = self.entries.get(key, [])
        if not matches:
            return None
        if len({(entry['size'], entry['sha256']) for entry in matches}) != 1:
            raise ValueError('Multiple checkpoint versions; select an exact saved path: ' + filename)
        if key not in self.staged:
            directory = self.directory / component
            directory.mkdir(exist_ok=True)
            self.staged[key] = self.store.stage(self.commit, matches[0], directory)
        return str(self.staged[key])

    def runner_alternatives(self, filename, suffix):
        allocation = r"_\(\d+_\d+_\d+_\d+\)"
        def normalize(name):
            return re.sub(allocation + r"|\s+", "", name)
        alternatives = {}
        for component, candidate in self.entries:
            if component != 'framework_state' or candidate == filename:
                continue
            if not re.search(allocation + r"\.pkl$", candidate) or (suffix and suffix not in candidate):
                continue
            name = normalize(candidate)
            if suffix:
                name = name.replace(f'_{suffix}', '')
            if name == normalize(filename):
                alternatives[candidate] = self.lookup(component, candidate)
        return alternatives
