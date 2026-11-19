"""Pipeline 154's original eight-run sources, using the existing notebook flow."""
from copy import deepcopy
import json
from pathlib import Path
import time

from googleapiclient.errors import HttpError

from .completion_notebook import ALLOCATORS, THREATS
from .seven_run_notebook import SevenRunPipelineNotebook


PROFILE = json.loads(Path(__file__).with_name('pipeline154_sources.json').read_bytes())


def eight_run_scopes(queues):
    expected = {allocator + ':' + capacity + ':' + scale for allocator in ALLOCATORS
        for capacity in ('T', 'Tb') for scale in ('1', '1.5', '2')}
    groups = {}
    for queue in queues:
        if str(queue.get('pipelineId')) != '154' or queue.get('testOnly') is True:
            raise ValueError('Only original Pipeline 154 production sources are accepted')
        for name, group in queue['sets'].items():
            if name not in expected or name in groups or set(group['attacks']) != set(THREATS):
                raise ValueError('Duplicate or foreign eight-run subset')
            if not group.get('finalizationRefs', {}).get('evaluation'):
                raise ValueError('Original completed output reference required')
            for attack in group['attacks'].values():
                if attack.get('state') != 'done' or attack.get('context', {}).get('run') != 8:
                    raise ValueError('Do not replay unfinished eight-run work as completed')
            groups[name] = deepcopy(group)
    if set(groups) != expected:
        raise ValueError('All 24 original eight-run subsets require source evidence')
    return groups


class EightRunPipelineNotebook(SevenRunPipelineNotebook):
    pipeline_number = 154
    target_runs = 8
    predecessor_pipeline_number = 152
    original_directory_prefix = 'eight-original-'
    queue_refs = tuple(PROFILE['queueRefs'])

    def load_groups(self):
        return eight_run_scopes(self.queues)

    def recover(self, set_id):
        for attempt in range(4):
            try:
                return super().recover(set_id)
            except HttpError as error:
                content = json.loads(error.content)
                reasons = {item.get('reason') for item in content.get('error', {}).get('errors', [])}
                if (attempt == 3 or error.resp.status not in (403, 429)
                        or not reasons.intersection({'rateLimitExceeded', 'userRateLimitExceeded'})):
                    raise
                delay = 60 * 2 ** attempt
                print(f'Drive request-rate backoff: {delay}s; saved completed work is retained', flush=True)
                time.sleep(delay)
