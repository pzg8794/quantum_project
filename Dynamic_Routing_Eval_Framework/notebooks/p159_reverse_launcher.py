"""Run the two trailing Pipeline 159 allocator rows, without status publication."""

import ast
import base64
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import fcntl
import gzip
import json
import math
import os
from pathlib import Path
import pickle
import re
import shutil
import sys
import tempfile
import time


PIPELINE = 'Pipeline_159'
KEY = 'pipeline-159'
EXECUTION = 'p159-from-p155-34fa18cab8194b50'
ROWS = ('ThompsonSampling', 'Dynamic')


def reverse_scopes(plan):
    return [(allocator, cohort) for allocator in reversed(plan['allocators']) if allocator in ROWS
            for cohort in reversed(plan['cohorts'])]


def ahead_of_forward(plan, runtime, allocator, cohort):
    active = (runtime.get('allocator'), runtime.get('cohort'))
    if runtime.get('state') != 'running':
        return True
    updated = runtime['updated']
    if not 0 <= time.time() - updated <= runtime.get('heartbeatTimeout', 180):
        return False
    ordered = [(name, group) for name in plan['allocators'] for group in plan['cohorts']]
    return (active in ordered and active[1] != cohort
            and ordered.index((allocator, cohort)) > ordered.index(active) + 1)


def profiles_from(notebook):
    cell = next(cell for cell in json.loads(notebook.read_text())['cells'] if cell.get('id') == 'profiles')
    assignment = ast.parse(''.join(cell['source'])).body[0]
    literal = ast.literal_eval(assignment.value.args[0].args[0].args[0])
    return json.loads(gzip.decompress(base64.b64decode(literal)))


def restore(snapshot, allocator, threat, position, frames, models, decode_result):
    key = f'{allocator}/{threat}/{position}'
    entry = snapshot.experiments[key]
    if entry.get('state'):
        payload = pickle.loads(snapshot.read(key, 'state'))
        if payload['id'] != position or not payload['is_complete'] or payload['frames_count'] != frames:
            raise ValueError(f'Invalid runner identity: {key}')
        row = dict(results=payload['results'], winner=payload.get('winner'), exp_id=position)
    else:
        cohort = re.fullmatch(r'S(1|1\.5|2)(Tb?)', snapshot.identity['cohort'])
        row = decode_result(snapshot, key, pipeline=entry['source']['pipeline'],
                            set_id=f'{allocator}:{cohort[2]}:{cohort[1]}', threat=threat,
                            position=position, frames=frames, models=models)
    if set(row['results']) != set(models) or any(
            result.get('error') or result['frames_count'] != frames
            or not math.isfinite(float(result['final_reward'])) for result in row['results'].values()):
        raise ValueError(f'Invalid saved model results: {key}')
    return row


def main():
    from cohort_run_publication import SharedCohortStore
    from daqr.config import tae_workflow
    from daqr.config.experiment_config import ExperimentConfiguration
    from daqr.config.gd_backup_manager import GoogleDriveBackupManager
    from daqr.core import qubit_allocator
    from daqr.evaluation import experiment_runner, model_process_executor
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
    from evaluator_derived_results import read_completed_result
    from p155_causal_history import CausalExperimentConfiguration
    from p155_remote_archive import ExperimentArchive
    from p159_staged_continuation import NotebookLog, optional_log
    from p159_worker_handoff import model_worker_handoff

    class ReverseArchive(ExperimentArchive):
        log_path = None

        def _handoff(self, key, checkpoint, models, evaluator, *, log=None):
            super()._handoff(key, checkpoint, models, evaluator, log=self.log_path)
            if self.log_path is not None:
                self.log_backup_pending = not self.remove_verified_log(key, self.log_path)

    class NoStatus:
        pending = False
        runtime = {}

        def transition(self, *_args):
            return False

    tae_workflow._WORKFLOWS[PIPELINE] = NoStatus()
    experiment_runner.observe_model = model_process_executor.observe_model = lambda *_args: None
    profiles = profiles_from(Path(sys.argv[1]))
    with (Path(tempfile.gettempdir()) / 'pipeline-159-notebook.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        workflow_store, store = tae_workflow.WorkflowStore(), SharedCohortStore()
        _, _, workflow = workflow_store.load(PIPELINE)
        binding, plan = workflow['executionBinding'], workflow['plan']
        if binding['executionId'] != EXECUTION or str(binding['storage']['pipelineId']) != '159' or plan['runs'] != 10:
            raise ValueError('Pipeline 159 is not bound to the approved ten-run execution')
        drive = GoogleDriveBackupManager.pipeline_creation_drive_service()
        drive.drives().get(driveId=binding['storage']['driveId'], fields='id').execute()
        os.environ['DAQR_MODEL_MAX_WORKERS'] = '4'
        scopes = reverse_scopes(plan)
        print(f'Reverse loop: {len(scopes)} scopes in {", ".join(ROWS)}; monitoring off', flush=True)
        for allocator, cohort in scopes:
            replay = 'Tb' if cohort.endswith('Tb') else 'T'
            profile = profiles[f'{allocator}:{replay}:{cohort[1:-len(replay)]}']
            policy = profile['policy']
            for threat in reversed(plan['threats']):
                _, index, workflow = workflow_store.load(PIPELINE)
                if workflow['executionBinding'] != binding or workflow['plan'] != plan:
                    raise ValueError('Pipeline binding or plan changed')
                runtime = index[PIPELINE].get('runnerStatus') or {}
                snapshot = store.open_published(KEY, EXECUTION, cohort)
                key = f'{allocator}/{threat}/10'
                recorded = workflow['allocators'][allocator]['cohorts'][cohort]['threats'][threat]['experiments']
                if key in snapshot.experiments or recorded.get('10', {}).get('state') == 'done':
                    print(f'Skip {allocator}/{cohort}/{threat}/10: already recorded', flush=True)
                    continue
                if not ahead_of_forward(plan, runtime, allocator, cohort):
                    print(f'Reverse boundary reached at {allocator}/{cohort}; no overlapping work started.', flush=True)
                    return
                missing = [position for position in range(1, 10)
                           if f'{allocator}/{threat}/{position}' not in snapshot.experiments]
                if missing:
                    print(f'Skip {key} in {cohort}: missing predecessors {missing}', flush=True)
                    continue
                def restore_position(position):
                    frames = policy['baseFrames'] + (position - 1) * policy['frameStep']
                    return restore(snapshot, allocator, threat, position, frames, plan['models'], read_completed_result)

                with ThreadPoolExecutor(max_workers=4) as workers:
                    saved = dict(zip(range(1, 10), workers.map(restore_position, range(1, 10)), strict=True))
                _, latest, current_workflow = workflow_store.load(PIPELINE)
                if current_workflow['executionBinding'] != binding or current_workflow['plan'] != plan:
                    raise ValueError('Pipeline binding or plan changed during restore')
                if not ahead_of_forward(plan, latest[PIPELINE].get('runnerStatus') or {}, allocator, cohort):
                    print(f'Reverse boundary reached at {allocator}/{cohort}; no overlapping work started.', flush=True)
                    return
                fresh = store.open_published(KEY, EXECUTION, cohort)
                if key in fresh.experiments:
                    continue
                run = store.open_run(KEY, EXECUTION, cohort)
                if run.head != fresh.head or fresh.head != snapshot.head:
                    raise RuntimeError('Checkpoint pin changed during restore; no experiment started for this scope')
                staging = Path(tempfile.mkdtemp(prefix='p159-reverse-'))
                persisted = False
                evaluator = None
                try:
                    original = profile['attacks'][threat]
                    settings = deepcopy(original['configuration'])
                    allocation = settings.pop('allocator')
                    physics = settings.get('physics_params') or {}
                    if 'entanglement_success_factor' in physics:
                        settings['testbed_config'] = dict(settings.get('testbed_config') or {},
                            entanglement_success_factor=physics.pop('entanglement_success_factor'))
                    settings.update(runs=10, resume=False, use_last_backup=False, overwrite=False,
                                    pipeline_storage=binding['storage'], staging_dir=staging, drive_service=drive,
                                    scenarios={threat: settings['scenarios'][threat]})
                    causal = threat in ('adaptive', 'onlineadaptive')
                    factory = CausalExperimentConfiguration if causal else ExperimentConfiguration
                    config = factory(allocator=getattr(qubit_allocator, allocation['class'])(**allocation['kwargs']), **settings)
                    for model, model_settings in original['modelSettings'].items():
                        for field in ('kwargs', 'seed_offset', 'runner_type'):
                            config.algorithm_configs[model][field] = deepcopy(model_settings[field])
                    if causal:
                        config.bind_causal_models()
                    config.resume_allow_drive_downloads = False
                    config.remote_experiment_archive = True
                    evaluator = MultiRunEvaluator(configs=config, base_frames=policy['baseFrames'],
                        frame_step=policy['frameStep'], base_seed=policy['baseSeed'], attack_type=threat)
                    evaluator.env_experiments = {threat: saved}
                    archive = ReverseArchive(config, run, staging, drive_factory=lambda: drive)
                    evaluator._experiment_archive = archive
                    print(f'Start {allocator}/{cohort}/{threat}/10: all nine predecessors verified', flush=True)
                    with optional_log((staging / 'experiment.log').open, 'w', encoding='utf-8') as output:
                        archive.log_path = Path(output.name) if output else None
                        with (redirect_stdout(NotebookLog(sys.stdout, output)),
                              redirect_stderr(NotebookLog(sys.stderr, output)), model_worker_handoff()):
                            evaluator.test_stochastic_environment(attack_type=threat, scenarios=config.test_scenarios,
                                                                  cal_winner=True, parellel=False)
                    current = store.open_published(KEY, EXECUTION, cohort)
                    restore(current, allocator, threat, 10, policy['baseFrames'] + 9 * policy['frameStep'],
                            plan['models'], read_completed_result)
                    persisted = not getattr(archive, 'log_backup_pending', False)
                    print(f'Verified {allocator}/{cohort}/{threat}/10 in Git', flush=True)
                finally:
                    if evaluator is not None:
                        evaluator.cleanup(verbose=False, cooldown_seconds=0)
                    if persisted:
                        shutil.rmtree(staging)
                    else:
                        print(f'Staging retained: {staging}', flush=True)
        print('Reverse pass finished both allocator rows.', flush=True)


if __name__ == '__main__':
    main()
