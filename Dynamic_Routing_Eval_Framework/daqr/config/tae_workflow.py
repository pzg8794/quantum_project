"""Threat-boundary workflow metadata, independent of scientific state loading."""
import base64
import copy
from functools import wraps
import json
import os
from pathlib import Path
import re
import tempfile
import time
import stat
import subprocess

from .pipeline_backup_index import GitHubBackupIndexStore, encoded_index
from .pipeline_storage import read_private_json


def safe_key(value):
    value = str(value)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', value) or value in ('.', '..'):
        raise ValueError('Safe workflow identity required')
    return value


def status(children):
    values = list(children)
    done = sum(value['state'] == 'done' for value in values)
    state = ('done' if values and done == len(values) else
             'running' if any(value['state'] == 'running' for value in values) else
             'resume' if done or any(value['state'] == 'resume' for value in values) else 'none')
    return dict(state=state, current=done, expected=len(values))


def allocator_document(document):
    if 'allocators' in document:
        return document
    migrated = {key: copy.deepcopy(value) for key, value in document.items() if key != 'cohorts'}
    migrated['allocators'] = {}
    for cohort, node in document.get('cohorts', {}).items():
        for allocator, value in node['allocators'].items():
            migrated['allocators'].setdefault(allocator, dict(cohorts={}))['cohorts'][cohort] = value
    return migrated


def merge_workflow(target, source):
    if target.get('state') == 'done':
        return
    if source.get('state') == 'none' and target.get('state') in ('running', 'resume'):
        return
    for key, value in source.items():
        if key == 'settings' and key in target and target[key] != value:
            raise ValueError('Concurrent shared subset settings differ')
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_workflow(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def recorded_execution_status(recorded_status):
    notice = 'Recorded workflow status; not a live-process observation.'
    if recorded_status == 'running':
        return dict(state='running', label='Running', notice=notice)
    if recorded_status in ('complete', 'completed', 'ready'):
        return dict(state='idle', label='Ready', notice=notice)
    if recorded_status == 'done':
        return dict(state='idle', label='Done', notice=notice)
    if recorded_status in (None, '', 'none', 'unindexed', 'unknown', 'unobserved'):
        return None
    if recorded_status == 'not-running':
        return dict(state='idle', label='Not running', notice=notice)
    if recorded_status in ('stopped', 'issue'):
        return dict(state='warning', label=recorded_status.capitalize(), notice=notice)
    return dict(state='warning', label='Resume', notice=notice)


def backfill_table_execution_status(index):
    updated = copy.deepcopy(index)
    for pipeline, entry in updated.items():
        if not re.fullmatch(r'Pipeline_[1-9][0-9]*', pipeline):
            raise ValueError('Exact workflow pipeline identity required')
        table = entry.get('table')
        if table is None:
            continue
        if table.get('pipelineNumber') != int(pipeline.removeprefix('Pipeline_')):
            raise ValueError('Workflow table pipeline differs')
        table['executionStatus'] = recorded_execution_status(table.get('status'))
    return updated


PIPELINE_STATUS_DEFAULTS = {
    'nonSpectrum': {
        'allocator': dict(current=0, expected=4, unit='allocators'),
        'cohort': dict(current=0, expected=24, unit='allocator-cohort scopes'),
        'experiment': dict(current=0, expected=120, unit='allocator-cohort-threat scopes'),
        'model': dict(current=0, expected=600, unit='allocator-cohort-threat-model scopes'),
        'evaluators': dict(allocators=dict(completed=0, expected=4),
                           experiments=dict(completed=0, expected=120),
                           models=dict(completed=0, expected=600)),
    },
    'Spectrum': {
        'allocator': dict(current=0, expected=4, unit='allocators'),
        'cohort': dict(current=0, expected=48, unit='allocator-cohort scopes'),
        'experiment': dict(current=0, expected=240, unit='allocator-cohort-threat scopes'),
        'model': dict(current=0, expected=1200, unit='allocator-cohort-threat-model scopes'),
        'evaluators': dict(allocators=dict(completed=0, expected=4),
                           experiments=dict(completed=0, expected=240),
                           models=dict(completed=0, expected=1200)),
        'templateProvenance': dict(levels=['m2', 'm3'], capacities=['T', 'Tb'],
            scales=[1, 1.5, 2], sources=['daqr/campaigns/spectrum_three.py:208',
                'daqr/campaigns/medium_tier1.py:22', 'notebooks/spectrum-three']),
    },
}


def default_pipeline_status(group):
    if group not in PIPELINE_STATUS_DEFAULTS:
        raise ValueError('Verified pipeline status group required')
    return copy.deepcopy(PIPELINE_STATUS_DEFAULTS[group])


def initialize_pipeline_status(group, prior=None, *, new_pipeline=False):
    """Overlay recorded fields on isolated group defaults, without I/O.

    Missing/null counters use defaults, not recovered execution evidence.
    Non-null prior values (including zero and status) always win.
    The caller must supply the verified group, never infer it from an ID.
    """
    if prior is not None and not isinstance(prior, dict):
        raise ValueError('Recorded pipeline status mapping required')
    if type(new_pipeline) is not bool:
        raise ValueError('Explicit new pipeline boolean required')
    result = default_pipeline_status(group)
    defaulted = []
    for name in ('allocator', 'cohort', 'experiment', 'model'):
        counter = (prior or {}).get(name)
        if counter is not None and not isinstance(counter, dict):
            raise ValueError('Recorded pipeline counter mapping required: ' + name)
        for field in ('current', 'expected'):
            if (counter or {}).get(field) is None:
                defaulted.append(name + '.' + field)
    evaluators = (prior or {}).get('evaluators') or {}
    if not isinstance(evaluators, dict):
        raise ValueError('Recorded evaluator status mapping required')
    for name in ('allocators', 'experiments', 'models'):
        counter = evaluators.get(name)
        if counter is not None and not isinstance(counter, dict):
            raise ValueError('Recorded evaluator counter mapping required: ' + name)
        for field in ('completed', 'expected'):
            if (counter or {}).get(field) is None:
                defaulted.append('evaluators.' + name + '.' + field)

    def overlay(target, source):
        for key, value in source.items():
            if value is None:
                continue
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                overlay(target[key], value)
            else:
                target[key] = copy.deepcopy(value)

    overlay(result, prior or {})
    provenance = result.setdefault('defaultedStatusProvenance', {})
    if not isinstance(provenance, dict):
        raise ValueError('Defaulted status provenance mapping required')
    provenance.setdefault('group', group)
    provenance.setdefault('source', 'PIPELINE_STATUS_DEFAULTS')
    provenance.setdefault('recoveredEvidence', False)
    provenance['fields'] = list(dict.fromkeys(list(provenance.get('fields') or []) + defaulted))
    return result


def normalize_published_status(document, projected, previous_entry):
    """Fill structural publication gaps using recorded values, then defaults."""
    previous = previous_entry.get('pipelineStatus') or {}
    group = (previous.get('migration') or {}).get('group') or (previous.get('defaultedStatusProvenance') or {}).get('group')
    if group is None:
        spectrum = (document.get('settings') or {}).get('spectrum')
        group = 'Spectrum' if spectrum is True else 'nonSpectrum' if spectrum is False else None
    merged = copy.deepcopy(projected)
    if group is None:
        return merged
    metrics = ('allocator', 'cohort', 'experiment', 'model', 'evaluators')

    def fill_missing(target, source):
        for key, value in source.items():
            if target.get(key) is None:
                target[key] = copy.deepcopy(value)
            elif isinstance(target[key], dict) and isinstance(value, dict):
                fill_missing(target[key], value)

    for name in metrics:
        if merged.get(name) is None:
            merged[name] = {}
        fill_missing(merged[name], previous.get(name) or {})
    if merged.get('defaultedStatusProvenance') is None and previous.get('defaultedStatusProvenance') is not None:
        merged['defaultedStatusProvenance'] = copy.deepcopy(previous['defaultedStatusProvenance'])
    normalized = initialize_pipeline_status(group, merged)
    for key, value in projected.items():
        if key not in metrics and key != 'defaultedStatusProvenance':
            normalized[key] = copy.deepcopy(value)
    return normalized


def incomplete_evaluation_status(document):
    if not isinstance(document, dict):
        return 'resume'
    nodes = []
    for allocator in document.get('allocators', {}).values():
        nodes.append(allocator)
        for cohort in allocator.get('cohorts', {}).values():
            nodes.append(cohort)
            for threat in cohort.get('threats', {}).values():
                nodes.append(threat)
                for experiment in threat.get('experiments', {}).values():
                    nodes.append(experiment)
                    nodes.extend(experiment.get('models', {}).values())
    evaluated = (document.get('stageStatus') or {}).get('evaluators') or {}
    stages = document.get('stageStatus') or {}
    zero_counters = [stages.get(name) for name in ('allocators', 'cohorts', 'experiments', 'models')]
    zero_counters.extend(evaluated.get(name) for name in ('allocators', 'experiments', 'models'))
    explicitly_zero = all(isinstance(counter, dict)
        and type(counter.get('completed', counter.get('current'))) is int
        and counter.get('completed', counter.get('current')) == 0 for counter in zero_counters)
    readiness = document.get('readiness') or {}
    postprocessing_artifacts = any(readiness.get(name) is True for name in
        ('fairnessComplete', 'fairnessVerified', 'preparedComplete', 'prepared'))
    if document.get('plan') and explicitly_zero and not postprocessing_artifacts and not any(
            node.get('state') not in (None, 'none', 'not-run') for node in nodes):
        return 'not-running'
    def incomplete(node):
        return isinstance(node, dict) and 'state' in node and node['state'] != 'done'
    plan = document.get('plan') or {}
    expected_threats = set(plan.get('threats', []))
    expected_models = set(plan.get('models', []))
    expected_positions = {str(number) for number in range(1, plan.get('runs', 0) + 1)}
    for allocator in document.get('allocators', {}).values():
        if incomplete(allocator):
            return 'issue'
        for cohort in allocator.get('cohorts', {}).values():
            if incomplete(cohort):
                return 'issue'
            if expected_threats - set(cohort.get('threats', {})):
                return 'issue'
            for threat in cohort.get('threats', {}).values():
                if incomplete(threat):
                    return 'issue'
                if expected_positions - set(threat.get('experiments', {})):
                    return 'issue'
                for experiment in threat.get('experiments', {}).values():
                    if expected_models - set(experiment.get('models', {})):
                        return 'issue'
                    if experiment.get('state') != 'done' or any(model.get('state') != 'done'
                            for model in experiment.get('models', {}).values()):
                        return 'issue'
    if plan and (set(plan.get('allocators', [])) - set(document.get('allocators', {}))
            or any(set(plan.get('cohorts', [])) - set(allocator.get('cohorts', {}))
                for allocator in document.get('allocators', {}).values())):
        return 'stopped'
    return 'resume'


def pipeline_readiness_status(evaluators, readiness, document=None, execution_complete=False):
    """Require explicit evaluation counters and independent completion flags."""
    incomplete_status = incomplete_evaluation_status(document)
    if incomplete_status in ('issue', 'stopped', 'not-running'):
        return incomplete_status
    if document is not None and not execution_complete:
        return 'resume'
    if not isinstance(evaluators, dict):
        return 'resume' if execution_complete else incomplete_status
    for name in ('allocators', 'experiments', 'models'):
        counter = evaluators.get(name)
        if not isinstance(counter, dict):
            return 'resume' if execution_complete else incomplete_status
        current = counter.get('completed', counter.get('current'))
        expected = counter.get('expected')
        if type(current) is not int or type(expected) is not int:
            return 'resume' if execution_complete else incomplete_status
        if expected <= 0 or current != expected:
            return incomplete_status
    if not isinstance(readiness, dict):
        return 'resume'
    fairness = readiness.get('fairnessComplete', readiness.get('fairnessVerified'))
    prepared = readiness.get('preparedComplete', readiness.get('prepared'))
    if fairness is not True:
        return 'resume'
    return 'done' if prepared is True else 'ready'


def pipeline_status(document):
    """Project native saved positions against an explicit whole-pipeline roster."""
    normalized = allocator_document(document)
    pipeline = normalized.get('pipeline', '')
    if not re.fullmatch(r'Pipeline_[1-9][0-9]*', pipeline):
        raise ValueError('Exact workflow pipeline identity required')
    plan = normalized.get('plan')
    rosters = {}
    if plan is not None:
        if not isinstance(plan, dict):
            raise ValueError('Explicit pipeline plan required')
        for field in ('allocators', 'cohorts', 'threats', 'models'):
            values = plan.get(field)
            if (not isinstance(values, list) or not values
                    or any(not isinstance(value, str) or not value for value in values)
                    or len(set(values)) != len(values)):
                raise ValueError('Explicit unique plan roster required: ' + field)
            rosters[field] = set(values)
        cohort_pattern = r'S[0-9]+(?:\.[0-9]+)?Tb?'
        if (normalized.get('settings') or {}).get('spectrum') is True:
            cohort_pattern = r'(?:m[23]:)?' + cohort_pattern
        if any(not re.fullmatch(cohort_pattern, name) for name in rosters['cohorts']):
            raise ValueError('Explicit planned cohort identity required')
        if type(plan.get('runs')) is not int or plan['runs'] <= 0:
            raise ValueError('Explicit positive plan runs required')
    completed_experiments = completed_models = completed_allocators = completed_cohorts = 0
    completed_threat_scopes = completed_model_scopes = 0
    running = False
    for allocator_name, allocator in normalized.get('allocators', {}).items():
        if plan is not None and allocator_name not in rosters['allocators']:
            raise ValueError('Observed allocator outside pipeline plan')
        allocator_done = 0
        for cohort_name, cohort in allocator.get('cohorts', {}).items():
            if plan is not None and cohort_name not in rosters['cohorts']:
                raise ValueError('Observed cohort outside pipeline plan')
            cohort_done = 0
            for threat_name, threat in cohort.get('threats', {}).items():
                if plan is not None and threat_name not in rosters['threats']:
                    raise ValueError('Observed threat outside pipeline plan')
                if plan is not None:
                    positions = threat.get('experiments', {})
                    planned_positions = [positions.get(str(number), {}) for number in range(1, plan['runs'] + 1)]
                    completed_threat_scopes += all(position.get('state') == 'done' for position in planned_positions)
                    completed_model_scopes += sum(all(position.get('models', {}).get(name, {}).get('state') == 'done'
                        for position in planned_positions) for name in rosters['models'])
                for position, experiment in threat.get('experiments', {}).items():
                    if plan is not None and str(position) not in {str(number) for number in range(1, plan['runs'] + 1)}:
                        raise ValueError('Observed experiment position outside pipeline plan')
                    done = experiment.get('state') == 'done'
                    completed_experiments += done
                    cohort_done += done
                    running = running or experiment.get('state') == 'running'
                    for model_name, model in experiment.get('models', {}).items():
                        if plan is not None and model_name not in rosters['models']:
                            raise ValueError('Observed model outside pipeline plan')
                        completed_models += model.get('state') == 'done'
                        running = running or model.get('state') == 'running'
            if plan is not None and cohort_done == len(rosters['threats']) * plan['runs']:
                completed_cohorts += 1
                allocator_done += 1
        if plan is not None and allocator_done == len(rosters['cohorts']):
            completed_allocators += 1
    expected_experiments = (len(rosters['allocators']) * len(rosters['cohorts'])
        * len(rosters['threats']) * plan['runs']) if plan is not None else None
    expected_threat_scopes = expected_experiments // plan['runs'] if plan is not None else None
    declared = normalized.get('state', normalized.get('status'))
    if isinstance(declared, dict):
        declared = declared.get('state')
    runtime = copy.deepcopy(normalized.get('runtime'))
    state = ('running' if running or declared == 'running' or isinstance(runtime, dict)
        and runtime.get('state') == 'running' else
        'done' if expected_experiments is not None and completed_experiments == expected_experiments
        and completed_models == expected_experiments * len(rosters['models']) else declared or
        ('resume' if completed_experiments or completed_models else 'none'))
    evaluators = copy.deepcopy((normalized.get('stageStatus') or {}).get('evaluators'))
    readiness = copy.deepcopy(normalized.get('readiness'))
    execution_complete = (expected_experiments is not None and completed_experiments == expected_experiments
        and completed_models == expected_experiments * len(rosters['models']))
    readiness_state = pipeline_readiness_status(evaluators, readiness, normalized, execution_complete)
    execution = recorded_execution_status(state)
    if state != 'running':
        execution = dict(state='idle' if readiness_state in ('ready', 'done', 'not-running') else 'warning',
            label={'resume': 'Resume', 'ready': 'Ready', 'done': 'Done',
                'stopped': 'Stopped', 'issue': 'Issue', 'not-running': 'Not running'}[readiness_state],
            notice='Recorded workflow status; not a live-process observation.')
    result = dict(pipeline=pipeline, runtime=runtime,
        allocator=dict(current=completed_allocators if plan is not None else None,
            expected=len(rosters['allocators']) if plan is not None else None, unit='allocators'),
        cohort=dict(current=completed_cohorts if plan is not None else None,
            expected=len(rosters['allocators']) * len(rosters['cohorts']) if plan is not None else None,
            unit='allocator-cohort scopes'),
        experiment=dict(current=completed_threat_scopes if plan is not None else None,
            expected=expected_threat_scopes, unit='allocator-cohort-threat scopes'),
        model=dict(current=completed_model_scopes if plan is not None else None,
            expected=expected_threat_scopes * len(rosters['models'])
            if plan is not None else None, unit='allocator-cohort-threat-model scopes'),
        runPositions=dict(experiment=dict(current=completed_experiments, expected=expected_experiments,
            unit='threat/run positions'), model=dict(current=completed_models,
            expected=expected_experiments * len(rosters['models']) if plan is not None else None,
            unit='model/run positions')),
        status=readiness_state, completionStatus=state, evaluators=evaluators, readiness=readiness,
        readinessState=readiness_state, executionStatus=execution)
    return result


def workflow_table_entry(document):
    pipeline = document.get('pipeline', '')
    if not re.fullmatch(r'Pipeline_[1-9][0-9]*', pipeline):
        raise ValueError('Exact workflow pipeline identity required')
    table = dict(pipelineNumber=int(pipeline.removeprefix('Pipeline_')),
        displayName=document.get('displayName') or pipeline.replace('_', ' '),
        status='unindexed', stageStatus=None, readiness=None,
        executionStatus=recorded_execution_status('unindexed'),
        scope='Observed registered allocator objects, threat/run positions and model/run positions; full pipeline expectations are unknown unless explicitly recorded')
    normalized = allocator_document(document)
    allocations, experiments, models = [], [], []
    for allocator in normalized['allocators'].values():
        allocator_positions = []
        for cohort in allocator['cohorts'].values():
            positions = [position for threat in cohort['threats'].values()
                         for position in threat['experiments'].values()]
            allocator_positions.extend(positions)
            experiments.extend(positions)
            models.extend(model for position in positions for model in position.get('models', {}).values())
        allocations.append(bool(allocator_positions) and bool(allocator['cohorts'])
            and all(cohort['threats'] and all(threat['experiments'] for threat in cohort['threats'].values())
                    for cohort in allocator['cohorts'].values())
            and all(position.get('state') == 'done' for position in allocator_positions))
    if not allocations:
        return table
    explicit_stages = document.get('stageStatus') or {}
    stages = {}
    for name, completed in (
            ('allocators', sum(allocations)),
            ('experiments', sum(position.get('state') == 'done' for position in experiments)),
            ('models', sum(model.get('state') == 'done' for model in models))):
        expected = explicit_stages.get(name, {}).get('expected')
        if expected is not None and (type(expected) is not int or expected < completed):
            raise ValueError('Explicit workflow expected count conflicts with observed completion')
        stages[name] = dict(completed=completed, expected=expected)
    stages['evaluators'] = copy.deepcopy(explicit_stages.get('evaluators'))
    declared_status = document.get('status')
    declared = document.get('state') or (declared_status.get('state')
        if isinstance(declared_status, dict) else declared_status)
    table.update(stageStatus=stages, readiness=copy.deepcopy(document.get('readiness')),
        status='complete' if declared == 'done' else 'running' if declared == 'running'
        or any(position.get('state') == 'running' for position in experiments) else 'partial')
    table['executionStatus'] = recorded_execution_status(table['status'])
    if document.get('plan') is not None:
        projected = pipeline_status(document)
        for plural, singular in (('allocators', 'allocator'), ('experiments', 'experiment'), ('models', 'model')):
            table['stageStatus'][plural] = dict(completed=projected[singular]['current'],
                expected=projected[singular]['expected'])
        table['readinessState'] = projected['readinessState']
        table['status'] = projected['readinessState']
        table['executionStatus'] = projected['executionStatus']
    return table


def backfill_workflow_tables(index, pinned_documents):
    updated = copy.deepcopy(index)
    for pipeline, pinned in pinned_documents.items():
        if pipeline not in index or pinned['version'] != index[pipeline]['version']:
            raise ValueError('Backfill document version must match the existing workflow index')
        if pinned['document'].get('pipeline') != pipeline:
            raise ValueError('Backfill document pipeline differs')
        updated[pipeline]['table'] = workflow_table_entry(pinned['document'])
    return updated


def migrate_saved_progress_values(index, snapshot):
    reference = snapshot.get('sourceRef')
    if (not isinstance(reference, dict) or reference.get('repository') != 'pzg8794/pipeline_runner'
            or not re.fullmatch(r'[a-f0-9]{40}', reference.get('commit', ''))
            or reference.get('path') != 'RUNS.md'
            or not re.fullmatch(r'[a-f0-9]{64}', reference.get('sha256', ''))
            or not isinstance(snapshot.get('statuses'), dict)):
        raise ValueError('Pinned original tracker snapshot required')
    updated = copy.deepcopy(index)
    keys = {'allocators', 'experiments', 'models'}
    for number, saved in snapshot['statuses'].items():
        if not isinstance(number, str) or not re.fullmatch(r'[1-9][0-9]*', number):
            raise ValueError('Exact tracker pipeline identity required')
        pipeline = 'Pipeline_' + number
        if pipeline not in updated:
            continue
        entry = updated[pipeline]
        if not re.fullmatch(r'[a-f0-9]{40}', entry.get('version', '')):
            raise ValueError('Pinned target workflow required')
        table = entry.get('table')
        if not isinstance(table, dict) or table.get('pipelineNumber') != int(number):
            raise ValueError('Tracker table pipeline identity differs')
        if (table.get('stageStatus') is not None
                and (table.get('sourceRef') or {}).get('repository') != reference['repository']):
            continue
        if (not isinstance(saved, dict) or saved.get('pipelineNumber', int(number)) != int(number)
                or saved.get('state') not in ('idle', 'warning', 'running')
                or not isinstance(saved.get('label'), str) or not saved['label'].strip()
                or not isinstance(saved.get('notice'), str)):
            raise ValueError('Recorded tracker status required')
        progress = saved.get('progress')
        if progress is not None:
            if (not isinstance(progress, dict) or set(progress) != {
                    'schema', 'sourceRuns', 'targetRuns', 'scope', 'scopeLabel', 'stages'}
                    or progress['schema'] != 'pipeline-execution-progress/v1'
                    or progress['scope'] != 'whole-pipeline'
                    or not isinstance(progress['scopeLabel'], str) or not progress['scopeLabel'].strip()
                    or len(progress['scopeLabel']) > 240
                    or type(progress['sourceRuns']) is not int or type(progress['targetRuns']) is not int
                    or not 0 < progress['sourceRuns'] <= progress['targetRuns'] <= 1000000):
                raise ValueError('Original whole-pipeline progress contract required')
            stages = progress['stages']
            if (not isinstance(stages, dict) or set(stages) != keys | {'evaluators'}
                    or not isinstance(stages['evaluators'], dict) or set(stages['evaluators']) != keys):
                raise ValueError('Complete saved stage counter shape required')
            for group in (stages, stages['evaluators']):
                for key in keys:
                    counter = group[key]
                    if (not isinstance(counter, dict) or set(counter) != {'completed', 'expected', 'reused'}
                            or any(type(value) is not int or not 0 <= value <= 9007199254740991
                                   for value in counter.values())
                            or not 0 <= counter['reused'] <= counter['completed'] <= counter['expected']
                            or counter['expected'] == 0):
                        raise ValueError('Valid saved counters required; no recomputation permitted')
            if not isinstance(saved.get('progressJobId'), str) or not saved['progressJobId']:
                raise ValueError('Saved progress job identity required')
            table['stageStatus'] = copy.deepcopy(stages)
            table['status'] = ('complete' if saved['state'] == 'idle' and saved['label'] == 'Ready'
                else 'running' if saved['state'] == 'running' and saved['label'] == 'Running'
                else 'partial')
        if not isinstance(saved.get('jobId'), str) or not saved['jobId']:
            raise ValueError('Saved tracker job identity required')
        table['executionStatus'] = dict(state=saved['state'], label=saved['label'],
            notice='Recorded tracker snapshot; not a live-process observation. Scope: '
                + (progress['scopeLabel'] if progress is not None else 'status only; no progress counters imported'))
        table['progressSource'] = dict(sourceRef=copy.deepcopy(reference), jobId=saved['jobId'],
            progressJobId=saved.get('progressJobId'), scope=progress['scope'] if progress else 'status-only',
            recordedNotice=saved['notice'])
    return updated


def migrate_recovered_source_metadata(index, recoveries):
    updated = copy.deepcopy(index)
    for pipeline, recovered in recoveries.items():
        match = re.fullmatch(r'Pipeline_([1-9][0-9]*)', pipeline)
        if not match or pipeline not in updated:
            raise ValueError('Existing exact recovery pipeline required')
        number = int(match.group(1))
        entry = updated[pipeline]
        table = entry.get('table')
        if (not re.fullmatch(r'[a-f0-9]{40}', entry.get('version', ''))
                or not isinstance(table, dict) or table.get('pipelineNumber') != number):
            raise ValueError('Pinned matching recovery table required')
        if table.get('stageStatus') is not None:
            continue
        kind = recovered.get('kind')
        def verify_reference(reference, repository, path):
            if (not isinstance(reference, dict) or reference.get('repository') != repository
                    or reference.get('path') != path
                    or not re.fullmatch(r'[a-f0-9]{40}', reference.get('commit', ''))
                    or not re.fullmatch(r'[a-f0-9]{64}', reference.get('sha256', ''))):
                raise ValueError('Exact immutable recovery source reference required')
        if kind == 'source-coverage':
            verify_reference(recovered.get('sourceRef'), 'pzg8794/quantum-pipeline-' + str(number), 'PIPELINE.md')
            coverage = recovered['coverage']
            for completed, expected in (('recorded_outcomes', 'expected_outcomes'),
                    ('observed_evaluators', 'expected_evaluators')):
                if (type(coverage.get(completed)) is not int or type(coverage.get(expected)) is not int
                        or not 0 <= coverage[completed] <= coverage[expected]):
                    raise ValueError('Recorded source-coverage counts required')
            if (type(coverage.get('prepared_evaluators')) is not int
                    or not 0 <= coverage['prepared_evaluators'] <= coverage['observed_evaluators']):
                raise ValueError('Recorded prepared source count required')
            recovery = dict(sourceRef=copy.deepcopy(recovered['sourceRef']),
                recoveredSourceCoverage={key: coverage[key] for key in (
                    'recorded_outcomes', 'expected_outcomes', 'observed_evaluators',
                    'expected_evaluators', 'prepared_evaluators')}, dataState='source-coverage-only')
            scope = 'Historical source coverage only; outcome and evaluator-file counts are not whole-pipeline stage counts'
        elif kind == 'single-set':
            receipts = recovered.get('receipts')
            if not isinstance(receipts, list) or not receipts:
                raise ValueError('Separate single-set receipts required')
            jobs = set()
            for receipt in receipts:
                verify_reference(receipt.get('sourceRef'), 'pzg8794/pipeline_runner', 'RUNS.md')
                job = receipt.get('jobId')
                progress = receipt.get('progress', {})
                if (receipt.get('pipelineNumber') != number or not isinstance(job, str) or not job
                        or job in jobs or progress.get('schema') != 'pipeline-execution-progress/v1'
                        or progress.get('scope') != 'single-set'
                        or not isinstance(progress.get('scopeLabel'), str) or not progress['scopeLabel'].strip()
                        or type(progress.get('sourceRuns')) is not int or type(progress.get('targetRuns')) is not int
                        or not 0 < progress['sourceRuns'] <= progress['targetRuns'] <= 1000000):
                    raise ValueError('Matching single-set receipt identity and scope required')
                jobs.add(job)
                stages = progress.get('stages', {})
                keys = {'allocators', 'experiments', 'models'}
                if (set(stages) != keys | {'evaluators'} or set(stages['evaluators']) != keys):
                    raise ValueError('Original single-set counter shape required')
                for group in (stages, stages['evaluators']):
                    for key in keys:
                        counter = group[key]
                        if (set(counter) != {'completed', 'expected', 'reused'}
                                or any(type(value) is not int for value in counter.values())
                                or not 0 <= counter['reused'] <= counter['completed'] <= counter['expected']
                                or counter['expected'] <= 0):
                            raise ValueError('Original single-set counters required')
            recovery = dict(singleSetProgress=[{key: copy.deepcopy(receipt[key])
                for key in ('sourceRef', 'jobId', 'pipelineNumber', 'progress')} for receipt in receipts],
                dataState='single-set-records-only')
            scope = 'Historical single-set receipts, kept separate; no pooled whole-pipeline progress'
        elif kind == 'planned':
            verify_reference(recovered.get('sourceRef'), 'pzg8794/pipeline_runner',
                'versions/native-continuation-Pipeline' + str(number) + '/PLAN.json')
            plan = recovered['plan']
            sets = plan.get('expectedSets')
            if (plan.get('pipelineNumber') != number or type(plan.get('targetRuns')) is not int
                    or plan['targetRuns'] <= 0 or not isinstance(sets, list) or not sets
                    or any(not isinstance(value, str) or not value for value in sets)
                    or len(set(sets)) != len(sets) or not isinstance(plan.get('state'), str)):
                raise ValueError('Matching recorded plan and explicit expected-set roster required')
            recovery = dict(sourceRef=copy.deepcopy(recovered['sourceRef']),
                plannedCounters=dict(expectedSets=len(sets), targetRuns=plan['targetRuns']),
                expectedSetIds=copy.deepcopy(sets), recordedPlanState=plan['state'],
                dataState='planned-no-completion-record')
            scope = 'Recorded plan only; no completion counters or execution inferred'
        else:
            raise ValueError('Explicit supported recovery scope required')
        table.update(recovery=recovery, scope=scope)
    return updated


def migrate_saved_table_values(index, legacy):
    if (legacy.get('repository') != 'pzg8794/pipeline_runner'
            or not re.fullmatch(r'[a-f0-9]{40}', legacy.get('commit', ''))
            or not isinstance(legacy.get('pipelines'), dict)):
        raise ValueError('Pinned original workflow index required')
    updated = copy.deepcopy(index)
    fields = ('pipelineNumber', 'displayName', 'status', 'stageStatus', 'readiness')
    for pipeline, target in updated.items():
        match = re.fullmatch(r'Pipeline_([1-9][0-9]*)', pipeline)
        if not match or not re.fullmatch(r'[a-f0-9]{40}', target.get('version', '')):
            raise ValueError('Exact target pipeline and immutable workflow version required')
        table = target.get('table')
        if table is not None and table.get('stageStatus') is not None:
            continue
        number = int(match.group(1))
        entry = legacy['pipelines'].get('Pipeline ' + str(number))
        if not isinstance(entry, dict) or not all(field in entry for field in fields if field != 'readiness'):
            continue
        if type(entry['pipelineNumber']) is not int or entry['pipelineNumber'] != number:
            raise ValueError('Historical table pipeline identity differs')
        if (entry.get('live') is True or entry['status'] in ('running', 'queued', 'active')
                or entry['stageStatus'] is None or entry.get('latest') is None):
            continue
        reference = entry['latest']
        if (not isinstance(reference, dict) or reference.get('repository') != legacy['repository']
                or not re.fullmatch(r'[a-f0-9]{40}', reference.get('commit', ''))
                or not re.fullmatch(r'[a-f0-9]{64}', reference.get('sha256', ''))
                or not re.fullmatch(r'Pipeline' + str(number) + r'-(?:s[A-Za-z0-9_]+-)+v[1-9][0-9]*', reference.get('tag', ''))
                or reference.get('path') != 'versions/' + reference.get('tag', '') + '/WORKFLOW.md'
                or not isinstance(reference.get('path'), str)
                or any(part in ('', '.', '..') for part in reference['path'].split('/'))
                or re.search(r'[\\\x00-\x1f]', reference['path'])
                or not isinstance(entry['stageStatus'], dict)):
            raise ValueError('Immutable historical workflow reference and saved table required')
        copied = copy.deepcopy(table or {})
        copied.update({field: copy.deepcopy(entry.get(field)) for field in fields})
        copied['executionStatus'] = recorded_execution_status(copied['status'])
        copied.update(sourceRef=copy.deepcopy(reference),
            sourceIndexRef=dict(repository=legacy['repository'], commit=legacy['commit']),
            scope='Historical saved workflow table snapshot; not current live execution or newly verified readiness')
        target['table'] = copied
    return updated


class WorkflowStore(GitHubBackupIndexStore):
    repository = 'pzg8794/TAE_Workflow'

    def load(self, pipeline):
        head = self.api('git/ref/heads/main')['object']['sha']
        tree = self.api('git/commits/' + head)['tree']['sha']
        entries = self.api('git/trees/' + tree)['tree']
        blobs = {entry['path']: entry['sha'] for entry in entries if entry['type'] == 'blob'}
        def read(name, default):
            if name not in blobs:
                return default
            return json.loads(base64.b64decode(self.api('git/blobs/' + blobs[name])['content']))
        index = read('index.json', {})
        if pipeline in index:
            saved = self.api('contents/workflow.json?ref=' + index[pipeline]['version'])
            document = json.loads(base64.b64decode(saved['content']))
            if document.get('pipeline') != pipeline:
                raise ValueError('Indexed workflow pipeline differs')
        else:
            document = read('workflow.json', {})
            if document.get('pipeline') != pipeline:
                document = dict(pipeline=pipeline, allocators={})
        return head, index, allocator_document(document)

    def publish(self, head, index, document, files):
        previous_entry = index.get(document['pipeline'], {})
        projected = normalize_published_status(document, pipeline_status(document), previous_entry)
        files = dict(files, **{'pipeline_status.json': encoded_index(projected),
            'workflow.json': encoded_index(document)})
        table = workflow_table_entry(document)
        if table.get('stageStatus') is None:
            table['stageStatus'] = {}
        for plural, singular in (('allocators', 'allocator'), ('cohorts', 'cohort'),
                                 ('experiments', 'experiment'), ('models', 'model')):
            source_counter = projected.get(singular) or {}
            if all(source_counter.get(field) is None for field in ('current', 'expected')):
                continue
            if table['stageStatus'].get(plural) is None:
                table['stageStatus'][plural] = {}
            counter = table['stageStatus'][plural]
            for field, source in (('completed', 'current'), ('expected', 'expected')):
                if counter.get(field) is None and source_counter.get(source) is not None:
                    counter[field] = copy.deepcopy(source_counter[source])
        for name, source_counter in (projected.get('evaluators') or {}).items():
            if table['stageStatus'].get('evaluators') is None:
                table['stageStatus']['evaluators'] = {}
            evaluated = table['stageStatus']['evaluators']
            if evaluated.get(name) is None:
                evaluated[name] = {}
            for field in ('completed', 'expected'):
                if evaluated[name].get(field) is None and source_counter.get(field) is not None:
                    evaluated[name][field] = copy.deepcopy(source_counter[field])
        previous_table = index.get(document['pipeline'], {}).get('table') or {}
        if 'recovery' in previous_table:
            table['recovery'] = copy.deepcopy(previous_table['recovery'])
        tree = self.api('git/trees', dict(tree=[dict(path=path, mode='100644', type='blob',
            content=content.decode()) for path, content in files.items()]))['sha']
        revision = self.api('git/commits', dict(message='Update ' + document['pipeline'] + ' threat workflow',
            tree=tree, parents=[head]))['sha']
        pipeline = document['pipeline']
        entry = dict(previous_entry,
            version=revision, table=table, pipelineStatus=projected,
            statusRef=dict(repository=self.repository, commit=revision, path='pipeline_status.json'),
            workflowRef=dict(repo=self.repository, commit=revision, path='workflow.json'))
        for _attempt in range(5):
            if index.get(pipeline, {}) != previous_entry:
                raise RuntimeError('Selected pipeline workflow changed; reload before publishing')
            updated = {**index, pipeline: entry}
            base_tree = self.api('git/commits/' + head)['tree']['sha']
            indexed_tree = self.api('git/trees', dict(base_tree=base_tree, tree=[dict(path='index.json',
                mode='100644', type='blob', content=encoded_index(updated).decode())]))['sha']
            final = self.api('git/commits', dict(message='Index ' + pipeline + ' workflow version',
                tree=indexed_tree, parents=[head, revision]))['sha']
            try:
                self.api('git/refs/heads/main', dict(sha=final, force=False), method='PATCH')
            except RuntimeError:
                current = self.api('git/ref/heads/main')['object']['sha']
                if current == head:
                    raise
                head = current
                saved = self.api('contents/index.json?ref=' + head)
                index = json.loads(base64.b64decode(saved['content']))
                if index.get(pipeline) == entry:
                    return head, index
            else:
                return final, updated
        raise RuntimeError('Workflow index changed repeatedly; publication pending')


class TAEWorkflow:
    def __init__(self, pipeline, store=None, *, defer_git=False):
        self.pipeline = safe_key(pipeline)
        self.store = store or WorkflowStore()
        self.status_root = Path(os.environ.get('TAE_STATUS_ROOT', str(Path(tempfile.gettempdir()) / 'tae-workflow-status')))
        self.head, self.index = None, {}
        self.document = dict(pipeline=self.pipeline, allocators={})
        if defer_git:
            path = self.status_root / (self.pipeline + '.json')
            if path.exists():
                previous = read_private_json(path, 1024 * 1024)
                if previous.get('pipeline') != self.pipeline or previous.get('document', {}).get('pipeline') != self.pipeline:
                    raise ValueError('Cached workflow pipeline differs')
                self.document = allocator_document(previous['document'])
        else:
            self.ensure_source()
        self.pending = False

    def ensure_source(self):
        if self.head is None:
            head, index, document = self.store.load(self.pipeline)
            document = allocator_document(document)
            merge_workflow(document, self.document)
            self.head, self.index, self.document = head, index, document

    def set_runtime(self, config, *, phase='cohort', state='running'):
        binding = getattr(config, 'pipeline_storage', None)
        if not binding or 'Pipeline_' + binding['pipelineId'] != self.pipeline:
            raise ValueError('Runtime pipeline identity differs')
        if state not in ('running', 'stopped', 'done'):
            raise ValueError('Invalid runtime state')
        self.runtime = dict(pipeline=self.pipeline, allocator=safe_key(str(config.allocator)),
            cohort='S' + format(float(config.scale), 'g') + ('Tb' if config.base_capacity else 'T'),
            state=state, phase=phase, updated=time.time())
        self.document['runtime'] = copy.deepcopy(self.runtime)
        return self.write_live_status()

    def write_live_status(self, synced=False):
        try:
            return self._write_live_status(synced)
        except Exception as error:
            try:
                print('TAE local status publication pending:', error)
            except Exception:
                pass
            return None

    def _write_live_status(self, synced=False):
        runtime = getattr(self, 'runtime', None)
        if runtime is not None:
            self.document['runtime'] = copy.deepcopy(runtime)
        elif getattr(self, 'current_log', None):
            allocator, capacity, scale = self.current_log.split(':')
            self.document['runtime'] = dict(pipeline=self.pipeline, allocator=allocator,
                cohort='S' + scale + capacity)
        self.status_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.status_root.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise ValueError('Private owned workflow status directory required')
        path = self.status_root / (self.pipeline + '.json')
        if not hasattr(self, 'process_birth'):
            self.process_birth = subprocess.check_output(['ps', '-p', str(os.getpid()), '-o', 'lstart='],
                env=dict(os.environ, LC_ALL='C'), text=True, timeout=5).strip()
        payload = dict(pipeline=self.pipeline, pid=os.getpid(), updated=time.time(),
            processBirth=self.process_birth, synced=synced,
            workflowVersion=self.index.get(self.pipeline, {}).get('version'),
            logs=getattr(self, 'live_logs', {}), currentLog=getattr(self, 'current_log', None),
            stagingDir=getattr(self, 'staging_dir', None),
            runtime=getattr(self, 'runtime', None),
            pipelineStatus=pipeline_status(self.document),
            document=self.document, status=json.loads(self.files()['status.json']))
        descriptor, name = tempfile.mkstemp(prefix=self.pipeline + '-', suffix='.tmp', dir=self.status_root)
        pending = Path(name)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(payload, stream, allow_nan=False)
            pending.replace(path)
        finally:
            pending.unlink(missing_ok=True)
        return path

    def transition(self, config, experiment, state):
        cohort = 'S' + format(float(config.scale), 'g') + ('Tb' if config.base_capacity else 'T')
        allocator = safe_key(str(config.allocator))
        threat = safe_key(config.attack_type.lower())
        manager = getattr(config, 'backup_mgr', None)
        log = getattr(manager, '_log_file', None)
        if manager is not None and log is not None and isinstance(getattr(log, 'name', None), str):
            self.staging_dir = str(manager.dir)
            self.current_log = allocator + ':' + ('Tb' if config.base_capacity else 'T') + ':' + format(float(config.scale), 'g')
            if not hasattr(self, 'live_logs'):
                self.live_logs = {}
            self.live_logs[self.current_log] = dict(path=log.name, targetRuns=config.runs)
        node = self.document['allocators'].setdefault(allocator, dict(cohorts={}))
        allocation = node['cohorts'].setdefault(cohort, dict(threats={}))
        settings = dict(scale=config.scale, base_capacity=config.base_capacity,
            runs=config.runs, models=list(config.models))
        if allocation.get('settings', settings) != settings:
            raise ValueError('Shared subset settings changed; use a distinct pipeline version')
        allocation['settings'] = settings
        for name in config.test_scenarios:
            allocation['threats'].setdefault(safe_key(name.lower()), dict(experiments={}))
        for item in allocation['threats'].values():
            for position in range(1, config.runs + 1):
                item['experiments'].setdefault(str(position), dict(state='none',
                    models={safe_key(name): dict(state='none') for name in config.models}))
        attack = allocation['threats'].setdefault(threat, dict(experiments={}))
        for position in range(1, config.runs + 1):
            attack['experiments'].setdefault(str(position), dict(state='none', models={}))
        previous = attack['experiments'].get(str(experiment), {})
        if previous.get('state') == 'done' and not getattr(config, 'overwrite', False):
            return False
        attack['experiments'][str(experiment)] = dict(state=state,
            models={safe_key(name): dict(state='done' if state in ('running', 'resume')
                and not getattr(config, 'overwrite', False)
                and previous.get('models', {}).get(name, {}).get('state') == 'done' else state)
                for name in config.models})
        self.pending = True
        self.write_live_status()
        return True

    def files(self):
        runtime = getattr(self, 'runtime', None)
        if runtime is not None:
            self.document['runtime'] = copy.deepcopy(runtime)
        elif getattr(self, 'current_log', None):
            allocator, capacity, scale = self.current_log.split(':')
            self.document['runtime'] = dict(pipeline=self.pipeline, allocator=allocator,
                cohort='S' + scale + capacity)
        files = {}
        allocators = []
        for allocator, node in self.document['allocators'].items():
            path = 'allocators/' + allocator
            cohorts = []
            for cohort, allocation in node['cohorts'].items():
                root = path + '/cohorts/' + cohort
                threats = []
                for threat, attack in allocation['threats'].items():
                    branch = root + '/threats/' + threat
                    current = status(attack['experiments'].values())
                    threats.append(current)
                    files[branch + '/experiment.json'] = encoded_index(attack)
                    files[branch + '/status.json'] = encoded_index(current)
                    models = {}
                    for position, experiment in attack['experiments'].items():
                        for name, value in experiment['models'].items():
                            models.setdefault(name, {})[position] = value
                    model_states = []
                    for name, positions in models.items():
                        summary = status(positions.values())
                        model_states.append(summary)
                        files[branch + '/models/' + name + '.json'] = encoded_index(dict(status=summary, runs=positions))
                    files[branch + '/models/status.json'] = encoded_index(status(model_states))
                summary = status(threats)
                cohorts.append(summary)
                files[root + '/cohort.json'] = encoded_index(dict(name=cohort, settings=allocation['settings']))
                files[root + '/status.json'] = encoded_index(summary)
            files[path + '/allocator.json'] = encoded_index(dict(name=allocator))
            summary = status(cohorts)
            allocators.append(summary)
            files[path + '/status.json'] = encoded_index(summary)
        files['status.json'] = encoded_index(status(allocators))
        files['workflow.json'] = encoded_index(self.document)
        files['pipeline_status.json'] = encoded_index(pipeline_status(self.document))
        return files

    def flush(self):
        if self.pending:
            self.ensure_source()
            try:
                self.head, self.index = self.store.publish(self.head, self.index, self.document, self.files())
            except RuntimeError:
                self.head, self.index, remote = self.store.load(self.pipeline)
                remote = allocator_document(remote)
                merge_workflow(remote, self.document)
                self.document = remote
                raise
            self.pending = False


_WORKFLOWS = {}
_PIPELINE_STATUS_HEADS = {}
_OBSERVING = set()


def track_pipeline_runtime(binding):
    pipeline = 'Pipeline_' + binding['pipelineId']
    def decorate(function):
        @wraps(function)
        def execute(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except BaseException:
                tracker = _WORKFLOWS.get(pipeline)
                if tracker is not None and getattr(tracker, 'runtime', None):
                    tracker.runtime.update(state='stopped', phase='pipeline-error', updated=time.time())
                    try:
                        tracker.write_live_status()
                    except Exception as error:
                        print('Pipeline runtime status pending:', error)
                raise
        return execute
    return decorate


def current_tracker(config):
    binding = getattr(config, 'pipeline_storage', None)
    if not binding:
        return None
    pipeline = 'Pipeline_' + binding['pipelineId']
    if pipeline not in _WORKFLOWS:
        _WORKFLOWS[pipeline] = TAEWorkflow(pipeline, defer_git=True)
    return _WORKFLOWS[pipeline]


def observe_completed_experiment(config, experiment, saved):
    """Observe the native completed-work skip; never load or execute an experiment."""
    try:
        tracker = current_tracker(config)
        if tracker is None:
            return
        results = saved.get('results', {})
        if not all(isinstance(results.get(name), dict) and not results[name].get('error')
                and 'final_reward' in results[name] for name in config.models):
            return
        tracker.transition(config, experiment, 'done')
    except Exception as error:
        print('TAE completed-status observation pending:', error)


def sync_completed_status(config):
    try:
        tracker = current_tracker(config)
        if tracker is not None and tracker.pending:
            persist_status(tracker, config.backup_mgr)
    except Exception as error:
        print('TAE completed-status publication pending:', error)


def observe_model(runner, model):
    try:
        binding = getattr(runner.configs, 'pipeline_storage', None)
        tracker = _WORKFLOWS.get('Pipeline_' + binding['pipelineId']) if binding else None
        if tracker is None:
            return
        cohort = 'S' + format(float(runner.configs.scale), 'g') + ('Tb' if runner.configs.base_capacity else 'T')
        node = tracker.document['allocators'][str(runner.configs.allocator)]['cohorts'][cohort]
        experiment = node['threats'][runner.configs.attack_type.lower()]['experiments'][str(runner.id)]
        experiment['models'][model] = dict(state='done')
        tracker.pending = True
        tracker.write_live_status()
    except Exception as error:
        print('TAE model-status observation pending:', error)


def publish_pipeline_status(pipeline, document):
    store = GitHubBackupIndexStore()
    if pipeline not in _PIPELINE_STATUS_HEADS:
        head = store.api('git/ref/heads/main')['object']['sha']
        root = store.api('git/commits/' + head)['tree']['sha']
        _PIPELINE_STATUS_HEADS[pipeline] = (head, root)
    head, root = _PIPELINE_STATUS_HEADS[pipeline]
    tree = store.api('git/trees', dict(base_tree=root, tree=[dict(
        path=pipeline + '/workflow_status/status.json', mode='100644', type='blob',
        content=encoded_index(document).decode())]))['sha']
    revision = store.api('git/commits', dict(message='Update ' + pipeline + ' collected states and status',
        parents=[head], tree=tree))['sha']
    try:
        store.api('git/refs/heads/main', dict(sha=revision, force=False), method='PATCH')
    except RuntimeError:
        _PIPELINE_STATUS_HEADS.pop(pipeline, None)
        raise
    _PIPELINE_STATUS_HEADS[pipeline] = (revision, tree)
    return revision


def persist_status(tracker, manager):
    tracker.ensure_source()
    tracker.document.setdefault('collected', {}).update(copy.deepcopy(getattr(manager, 'workflow_upload_receipts', {})))
    path = tracker.write_live_status()
    if path is None:
        return
    receipt = manager.upload_workflow_status(path)
    if not receipt:
        raise RuntimeError('Workflow status upload pending')
    document = dict(pipeline=tracker.pipeline, workflow=tracker.document,
        status=json.loads(tracker.files()['status.json']), drive=receipt,
        collected=copy.deepcopy(tracker.document['collected']))
    publish_pipeline_status(tracker.pipeline, document)
    tracker.flush()
    tracker.write_live_status(synced=True)


def tracked_experiment(function):
    @wraps(function)
    def execute(runner, *args, **kwargs):
        if id(runner) in _OBSERVING:
            return function(runner, *args, **kwargs)
        binding = getattr(getattr(runner, 'configs', None), 'pipeline_storage', None)
        if not binding:
            return function(runner, *args, **kwargs)
        if kwargs.get('attack_type') is not None:
            runner.configs.attack_type = kwargs['attack_type']
        elif len(args) > 3 and args[3] is not None:
            runner.configs.attack_type = args[3]
        pipeline = 'Pipeline_' + binding['pipelineId']
        tracker = None
        observe_result = False
        try:
            if pipeline not in _WORKFLOWS:
                _WORKFLOWS[pipeline] = TAEWorkflow(pipeline, defer_git=True)
            tracker = _WORKFLOWS[pipeline]
            observe_result = tracker.transition(runner.configs, runner.id, 'running')
        except Exception as error:
            print('TAE workflow publication pending:', error)
        _OBSERVING.add(id(runner))
        try:
            result = function(runner, *args, **kwargs)
        except BaseException:
            if tracker and observe_result:
                try:
                    tracker.transition(runner.configs, runner.id, 'resume')
                except Exception as error:
                    print('TAE workflow publication pending:', error)
            raise
        finally:
            _OBSERVING.discard(id(runner))
        if tracker and observe_result:
            try:
                for name in runner.configs.models:
                    value = runner.results.get(name)
                    if not isinstance(value, dict) or value.get('error') or 'final_reward' not in value:
                        raise RuntimeError('Model result incomplete; not marking done')
                    if name != 'Oracle' and (value.get('algorithm') != name
                            or value.get('frames_count') != runner.frames_count
                            or value.get('seed') != runner.experiment_seed + runner.algorithm_configs[name]['seed_offset']):
                        raise RuntimeError('Model identity differs; not marking done')
            except Exception as error:
                try:
                    tracker.transition(runner.configs, runner.id, 'resume')
                except Exception as status_error:
                    print('TAE live-status update pending:', status_error)
                print('TAE execution status incomplete:', error)
                return result
            if getattr(runner.configs, 'remote_experiment_archive', False):
                if not runner.save():
                    raise RuntimeError('Unable to stage complete runner for remote handoff')
                return result
            try:
                tracker.transition(runner.configs, runner.id, 'done')
            except Exception as error:
                print('TAE live-status update pending:', error)
                return result
            try:
                saved = runner.save()
                if not saved:
                    raise RuntimeError('Runner backup pending; live execution is done')
                manager = runner.configs.backup_mgr
                filename = Path(saved).name
                if hasattr(manager, 'workflow_upload_receipts'):
                    manager.workflow_upload_receipts.pop(filename, None)
                manager.load_new_entries()
                if filename not in getattr(manager, 'workflow_upload_receipts', {}):
                    manager._upload_file_to_drive('framework_state', Path(saved).parent.name, saved, filename)
                recorded = getattr(manager, 'workflow_upload_receipts', {})
                if filename not in recorded:
                    raise RuntimeError('Runner Drive receipt pending; live execution is done')
                cohort = 'S' + format(float(runner.configs.scale), 'g') + ('Tb' if runner.configs.base_capacity else 'T')
                attack = tracker.document['allocators'][str(runner.configs.allocator)]['cohorts'][cohort]['threats'][runner.configs.attack_type.lower()]
                attack['experiments'][str(runner.id)]['drive'] = copy.deepcopy(recorded[filename])
                persist_status(tracker, manager)
            except Exception as error:
                print('TAE workflow publication pending:', error)
        return result
    return execute
