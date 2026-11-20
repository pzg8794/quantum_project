"""Pure, manual projection of pinned existing-workflow evidence; never publishes.

``migrate_workflow_status`` returns {index, pipeline_statuses, summary}. All six
arguments are JSON-like mappings and are copied, never mutated. Index keys bound
the approved scope (at most 26; no entries are created). group_by_pipeline explicitly maps
every index key to nonSpectrum or Spectrum; default_refs maps those groups to
immutable {repository, commit, path} references. No catalog-ID inference occurs.

pinned_documents maps pipeline -> {version, sourceRef, document}; version must
match index.version. Only native documents with an explicit plan are projected.
legacy_catalog maps pipeline -> {sourceRef, plan, ...}. Its plan has four unique
allocators, five threats, five models and six (Spectrum: twelve) cohorts, each
{baseCapacity: 'T'|'Tb', scale: positive number, tier: 'm2'|'m3' for Spectrum}.
history_snapshot is {sourceRef, jobs: [{id, pipeline, setGroups: [...]}]}.
Each setGroup has the same cohort fields and allocators keyed by planned name,
each containing attacks keyed by planned threat. A completed attack is exactly
{state: 'completed', current: 1, expected: 1}; optional models use that contract.
Only the job matching table.progressSource.progressJobId is used.

Fallback requires catalog.sourceCaptureComplete is True, explicit queryIndex
rows (cohort fields, allocator, threats: all five names), and an explicit False
latestPartialTargetReceipt. Rows are deduplicated, never treated as run counts.
Catalog/history references and pinned-document references require immutable Git
commit identities. The caller is responsible for retrieving/verifying bytes and
publishing returned pipeline_statuses plus index in ONE metadata transaction.

Lifecycle evidence comes only from table.stageStatus.evaluators (three counters:
allocators/experiments/models, completed == expected > 0) and table.readiness
{fairnessVerified: True, prepared: True}. The shared producer readiness policy
also accepts fairnessComplete/preparedComplete, whose explicit values take
precedence over aliases. Native producer fields are retained; the frontend table
projects normalized structural counters without changing its execution receipt.
Running is recorded separately, not asserted to be a live observation.
"""

import copy
import math
import re

from .tae_workflow import initialize_pipeline_status, pipeline_readiness_status, pipeline_status


_METRICS = ('allocator', 'cohort', 'experiment', 'model')
_SCHEMA = 'existing-workflow-structural/v1'


class _AmbiguousEvidence(ValueError):
    pass


def _reference(value):
    if (not isinstance(value, dict) or not value.get('repository')
            or not value.get('path')
            or not re.fullmatch(r'[a-f0-9]{40}', value.get('commit', ''))):
        raise ValueError('Immutable source reference required')


def _cohort(value, group):
    capacity, scale = value.get('baseCapacity'), value.get('scale')
    if (capacity not in ('T', 'Tb') or type(scale) not in (int, float)
            or not math.isfinite(scale) or scale <= 0):
        raise _AmbiguousEvidence('Explicit capacity and finite positive scale required')
    tier = value.get('tier') if group == 'Spectrum' else None
    if group == 'Spectrum' and tier not in ('m2', 'm3'):
        raise _AmbiguousEvidence('Explicit Spectrum m2/m3 tier required')
    return capacity, scale, tier


def _complete(value):
    return (isinstance(value, dict) and value.get('state') == 'completed'
            and type(value.get('current')) is int and value['current'] == 1
            and type(value.get('expected')) is int and value['expected'] == 1)


def _lifecycle(table):
    if table.get('plan') is not None and isinstance(table.get('allocators'), dict):
        return pipeline_status(table)['status'].capitalize()
    return pipeline_readiness_status((table.get('stageStatus') or {}).get('evaluators'),
                                     table.get('readiness'),
                                     table if isinstance(table.get('allocators'), dict) else None).capitalize()


def _legacy_counts(pipeline, table, catalog, history, group):
    if not catalog:
        return None, False, 'No explicit legacy scope catalog', []
    _reference(catalog.get('sourceRef'))
    plan = catalog['plan']
    rosters = {}
    for field, size in (('allocators', 4), ('threats', 5), ('models', 5)):
        roster = plan.get(field)
        if (not isinstance(roster, list) or len(roster) != size
                or any(not isinstance(name, str) or not name for name in roster)
                or len(set(roster)) != size):
            raise ValueError('Explicit shared legacy roster required: ' + field)
        rosters[field] = set(roster)
    cohorts = [_cohort(value, group) for value in plan['cohorts']]
    required = 12 if group == 'Spectrum' else 6
    if len(cohorts) != required or len(set(cohorts)) != required:
        raise ValueError('Explicit unique shared cohort roster required')
    cohorts = set(cohorts)
    job_id = (table.get('progressSource') or {}).get('progressJobId')
    jobs = [job for job in history.get('jobs', [])
            if job_id and job.get('id') == job_id and job.get('pipeline') == pipeline]
    if len(jobs) > 1:
        return None, False, 'Ambiguous matching progress job', []
    groups = jobs[0].get('setGroups') if jobs else None
    attacks_done, models_done = set(), set()
    lower_bound = False
    references = [catalog['sourceRef']]
    if groups:
        _reference(history.get('sourceRef'))
        references.append(history['sourceRef'])
        for item in groups:
            cohort = _cohort(item, group)
            if cohort not in cohorts:
                raise ValueError('History cohort outside explicit plan')
            for allocator, node in item['allocators'].items():
                if allocator not in rosters['allocators']:
                    raise ValueError('History allocator outside explicit plan')
                for threat, attack in node['attacks'].items():
                    if threat not in rosters['threats']:
                        raise ValueError('History threat outside explicit plan')
                    scope = (allocator, cohort, threat)
                    states = attack.get('models')
                    if _complete(attack):
                        attacks_done.add(scope)
                        if states is None:
                            lower_bound = True
                            models_done.update((scope, model) for model in rosters['models'])
                    if states is not None:
                        if not set(states) <= rosters['models']:
                            raise ValueError('History model outside explicit plan')
                        models_done.update((scope, model) for model, state in states.items()
                                           if _complete(state))
    else:
        if (catalog.get('sourceCaptureComplete') is not True
                or catalog.get('latestPartialTargetReceipt') is not False
                or not catalog.get('queryIndex')):
            return None, False, 'No matching groups or unconflicted complete source coverage', references
        lower_bound = True
        for row in catalog['queryIndex']:
            cohort = _cohort(row, group)
            allocator = row['allocator']
            if cohort not in cohorts or allocator not in rosters['allocators']:
                raise ValueError('Source coverage outside explicit plan')
            if set(row.get('threats', [])) != rosters['threats']:
                return None, False, 'Source coverage row lacks five explicit threats', references
            for threat in rosters['threats']:
                scope = (allocator, cohort, threat)
                attacks_done.add(scope)
                models_done.update((scope, model) for model in rosters['models'])
    cohorts_done = {(allocator, cohort) for allocator in rosters['allocators'] for cohort in cohorts
                    if all((allocator, cohort, threat) in attacks_done for threat in rosters['threats'])}
    allocators_done = sum(all((allocator, cohort) in cohorts_done for cohort in cohorts)
                          for allocator in rosters['allocators'])
    return dict(zip(_METRICS, (allocators_done, len(cohorts_done), len(attacks_done),
                               len(models_done)))), lower_bound, None, references


def migrate_workflow_status(index, pinned_documents, group_by_pipeline,
                            legacy_catalog, history_snapshot, default_refs):
    """Build a publication bundle, with no I/O, resets or source mutation."""
    if len(index) > 26:
        raise ValueError('Manual migration is bounded to 26 approved existing workflows')
    if set(index) != set(group_by_pipeline):
        raise ValueError('Explicit group mapping must match approved existing index exactly')
    updated = copy.deepcopy(index)
    statuses = {}
    summary = dict(pipelines=len(index), native=0, legacy=0, ambiguous=0, modelLowerBounds=0)
    for pipeline, entry in updated.items():
        if not re.fullmatch(r'Pipeline_[1-9][0-9]*', pipeline):
            raise ValueError('Exact existing pipeline identity required')
        if not re.fullmatch(r'[a-f0-9]{40}', entry.get('version', '')):
            raise ValueError('Pinned existing workflow version required')
        group = group_by_pipeline[pipeline]
        result = initialize_pipeline_status(group)
        _reference(default_refs.get(group))
        table = entry.get('table')
        if not isinstance(table, dict) or table.get('pipelineNumber') != int(pipeline.split('_')[1]):
            raise ValueError('Matching existing table required')
        entry.setdefault('legacySnapshot', copy.deepcopy({key: entry[key]
                         for key in ('table', 'pipelineStatus') if key in entry}))
        pinned = pinned_documents.get(pipeline)
        counts, lower_bound, reason, references = None, False, None, []
        lifecycle_source = table
        execution_running = table.get('status') == 'running'
        if pinned and pinned.get('document', {}).get('plan') is not None:
            _reference(pinned.get('sourceRef'))
            if (pinned.get('version') != entry['version']
                    or pinned['sourceRef']['commit'] != pinned['version']
                    or pinned['document'].get('pipeline') != pipeline):
                raise ValueError('Pinned native workflow identity/version differs')
            native = pipeline_status(pinned['document'])
            if any(native[name]['expected'] != result[name]['expected'] for name in _METRICS):
                raise ValueError('Native plan differs from shared group schema')
            result.update(copy.deepcopy(native))
            counts = {name: native[name]['current'] for name in _METRICS}
            references = [pinned['sourceRef']]
            lifecycle_source = pinned['document']
            execution_running = (native.get('executionStatus') or {}).get('state') == 'running'
            summary['native'] += 1
        else:
            try:
                counts, lower_bound, reason, references = _legacy_counts(
                    pipeline, table, legacy_catalog.get(pipeline), history_snapshot, group)
            except _AmbiguousEvidence as error:
                reason = str(error)
                references = [legacy_catalog[pipeline]['sourceRef']]
            summary['legacy'] += 1
        prior = entry.get('pipelineStatus') or {}
        status_ref = entry.get('statusRef') or {}
        if (counts is None and status_ref.get('commit') == entry['version']
                and status_ref.get('repository') and status_ref.get('path') == 'pipeline_status.json'
                and prior.get('pipeline') == pipeline
                and all((prior.get(name) or {}).get('expected') == result[name]['expected']
                        and (prior.get(name) or {}).get('unit') == result[name]['unit']
                        for name in _METRICS)):
            counts = {name: prior[name].get('current') for name in _METRICS}
            result.update(copy.deepcopy(prior))
            references.append(copy.deepcopy(status_ref))
            reason = None
        previous = prior.get('migration') or {}
        if previous.get('schema') == _SCHEMA:
            if previous.get('group') != group:
                raise ValueError('Previously migrated group differs; explicit reconciliation required')
            for reference in previous.get('evidenceRefs', []):
                if reference not in references:
                    references.append(copy.deepcopy(reference))
        for name in _METRICS:
            current = counts[name] if counts is not None else None
            old = prior.get(name) or {}
            if (current is None and old.get('expected') == result[name]['expected']
                    and old.get('unit') == result[name]['unit']
                    and type(old.get('current')) is int):
                current = old['current']
            if (previous.get('schema') == _SCHEMA and previous.get('group') == group
                    and old.get('expected') == result[name]['expected']
                    and type(old.get('current')) is int):
                current = max(current or 0, old['current'])
                lower_bound = lower_bound or previous.get('modelLowerBound', False)
            if current is not None and (type(current) is not int or not 0 <= current <= result[name]['expected']):
                raise ValueError('Verified structural count outside shared expectation')
            result[name]['current'] = current
        result['lifecycle'] = _lifecycle(lifecycle_source)
        result['pipeline'] = pipeline
        result['status'] = result['lifecycle'].lower()
        result['readinessState'] = result['status']
        result['evaluators'] = copy.deepcopy((lifecycle_source.get('stageStatus') or {}).get('evaluators'))
        result['readiness'] = copy.deepcopy(lifecycle_source.get('readiness'))
        if not pinned or pinned.get('document', {}).get('plan') is None:
            result['executionStatus'] = copy.deepcopy(table.get('executionStatus'))
            execution_running = ((table.get('executionStatus') or {}).get('state') == 'running'
                                 or execution_running)
        result['executionRunning'] = execution_running
        result['migration'] = dict(schema=_SCHEMA, group=group,
            defaultRef=copy.deepcopy(default_refs[group]), evidenceRefs=copy.deepcopy(references),
            ambiguityReason=reason, modelLowerBound=bool(lower_bound),
            currentLowerBounds=['model'] if lower_bound else [])
        entry['pipelineStatus'] = result
        stages = table.setdefault('stageStatus', {})
        if stages is None:
            stages = table['stageStatus'] = {}
        for plural, singular in (('allocators', 'allocator'), ('experiments', 'experiment'),
                                 ('models', 'model')):
            counter = stages.setdefault(plural, {})
            counter.update(completed=result[singular]['current'], expected=result[singular]['expected'])
        table['status'] = result['status']
        table['readinessState'] = result['readinessState']
        statuses[pipeline] = copy.deepcopy(result)
        summary['ambiguous'] += reason is not None
        summary['modelLowerBounds'] += bool(lower_bound)
    return dict(index=updated, pipeline_statuses=statuses, summary=summary)
