"""Metadata-only status reconciliation; never loads or executes scientific states."""
import copy

from .tae_workflow import pipeline_readiness_status, pipeline_status, recorded_execution_status


def complete(counter):
    return (isinstance(counter, dict) and type(counter.get('yes')) is int
        and type(counter.get('expected')) is int and counter['expected'] > 0
        and counter['yes'] == counter['expected'])


def audit_workflow_index(index, catalog, history, documents=None):
    updated = copy.deepcopy(index)
    records = []
    catalog_rows = {row['pipelineId']: row for row in catalog['pipelines']}
    jobs = {job['id']: job for job in history['jobs']}
    for key, entry in updated.items():
        table = entry['table']
        original = table.get('status')
        resolved = None
        reason = 'Insufficient same-target object evidence; previous lifecycle retained'
        evidence = []
        active_execution = None
        document = (documents or {}).get(key)
        if document is not None:
            result = pipeline_status(document)
            resolved = result['status']
            reason = 'Native planned allocator/cohort/threat/model status objects'
            if (result.get('executionStatus') or {}).get('state') == 'running':
                active_execution = copy.deepcopy(result['executionStatus'])
        else:
            job_id = (table.get('progressSource') or {}).get('progressJobId')
            job = jobs.get(job_id)
            if job:
                reason = 'Matching continuation receipt lacks per-cohort predecessor proof; aggregate reused counts cannot establish missing versus incomplete cohorts'
            source = catalog_rows.get(table['pipelineNumber'])
            if resolved is None and not job_id and source:
                status = source['status']
                facts = status.get('tableFacts') or {}
                rows = (status.get('queryIndex') or {}).get('rows')
                group = ((entry.get('pipelineStatus') or {}).get('migration') or {}).get('group')
                if status.get('capture_complete') is True and complete(facts.get('complete')) and group == 'nonSpectrum' and rows:
                    allocators = {'Default', 'Random', 'Dynamic', 'ThompsonSampling'}
                    cohorts = {'S' + str(scale) + capacity for scale in (1, 1.5, 2) for capacity in ('T', 'Tb')}
                    threats = {'none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive'}
                    observed = set()
                    valid = True
                    for row in rows:
                        scale = row.get('scale')
                        capacity = row.get('baseCapacity')
                        allocator = row.get('allocator')
                        if (allocator not in allocators or type(capacity) is not bool
                                or type(scale) not in (int, float) or scale not in (1, 1.5, 2)
                                or set(row.get('threats') or []) != threats):
                            valid = False
                            break
                        observed.add((allocator, 'S' + format(scale, 'g') + ('Tb' if capacity else 'T')))
                    if valid:
                        missing = sorted((allocator, cohort) for allocator in allocators for cohort in cohorts
                            if (allocator, cohort) not in observed)
                        evidence.append(dict(kind='complete-saved-source-scope', source=catalog['commit'],
                            missingAllocatorCohorts=missing, sourceRefs=facts.get('inputRefs', [])))
                        if missing:
                            resolved = 'stopped'
                            reason = 'All observed saved cohorts are complete; entire expected allocator/cohort scopes are absent'
                        else:
                            readiness = copy.deepcopy(table.get('readiness') or {})
                            for flag, field in (('fairness', 'fairnessComplete'), ('prepared', 'preparedComplete')):
                                readiness[field] = (True if status.get(flag) is True and complete(facts.get(flag))
                                    else False if status.get(flag) is False else None)
                            resolved = pipeline_readiness_status((table.get('stageStatus') or {}).get('evaluators'), readiness)
                            table['readiness'] = readiness
                            reason = 'Complete same-pipeline saved scope with explicit evaluation/fairness/preparation evidence'
        if resolved is not None:
            table['status'] = resolved
            table['readinessState'] = resolved
        badge = active_execution or recorded_execution_status(table.get('status'))
        if badge is not None:
            badge['notice'] += ' Status audit: ' + reason + '.'
        table['executionStatus'] = badge
        if isinstance(entry.get('pipelineStatus'), dict) and not entry.get('statusRef'):
            entry['pipelineStatus'].update(status=table.get('status'), readinessState=table.get('status'),
                readiness=copy.deepcopy(table.get('readiness')), executionStatus=copy.deepcopy(badge))
        audit = dict(pipeline=key, previous=original, status=table.get('status'),
            workflowVersion=entry['version'], rules='owner-20261116-ready-without-prepared',
            verified=resolved is not None, reason=reason, evidence=evidence,
            catalogCommit=catalog['commit'], historyRef=copy.deepcopy(history.get('git')))
        entry['statusAudit'] = audit
        records.append(audit)
    return dict(index=updated, records=records)
