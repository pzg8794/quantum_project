"""Model processes with original persistence/resume operations owned by the parent."""
from contextlib import contextmanager
from copy import deepcopy
import multiprocessing
from multiprocessing.connection import wait
import os
import pickle
import time
import traceback
from types import SimpleNamespace
from daqr.config.tae_workflow import observe_model


@contextmanager
def single_thread_environment():
    names = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')
    previous = {name: os.environ.get(name) for name in names}
    try:
        os.environ.update({name: '1' for name in names})
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def model_state(config, model):
    state = config._build_save_dict(model)
    state.pop('configs', None)
    return state


def send(connection, value):
    connection.send_bytes(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))


def receive(connection):
    return pickle.loads(connection.recv_bytes(512 * 1024**2))


def worker(payload, model_name, connection):
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        payload = pickle.loads(payload)
        config = payload['configuration_class'].__new__(payload['configuration_class'])
        config.__dict__.update(payload['configuration'])
        config.backup_mgr = SimpleNamespace(**payload['storage_paths'])
        config.base_model = None
        if payload['oracle_model'] is not None:
            oracle_class, oracle_state = payload['oracle_model']
            config.base_model = oracle_class.__new__(oracle_class)
            config.base_model.__dict__.update(oracle_state)
            config.base_model.configs = config
        def request(action, model):
            send(connection, (action, type(model), model_state(config, model), config.overwrite))
            response = receive(connection)
            if response[0] == 'error':
                raise RuntimeError(response[1])
            if action == 'resume' and response[1]:
                model.__dict__.update(response[2])
                model.configs = config
            return response[1]
        config.save_obj = lambda model: request('save', model)
        config.resume_obj = lambda model, **kwargs: request('resume', model)
        config.can_resume = lambda model: request('can_resume', model)
        runner = payload['runner_class'].__new__(payload['runner_class'])
        runner.__dict__.update(payload['runner'])
        runner.configs = config
        runner.save = lambda: None
        runner.run_single_model(model_name, payload['base_model'], is_parallel=True)
        send(connection, ('result', model_name, runner.results[model_name], os.getpid(),
                         torch.get_num_threads(), torch.get_num_interop_threads()))
    except BaseException:
        send(connection, ('error', model_name, traceback.format_exc()))
    finally:
        connection.close()


def service_request(runner, message):
    action, model_class, state, overwrite = message
    if action not in ('save', 'resume', 'can_resume') or state.get('component') != 'model_state':
        raise ValueError('Only original model save/resume requests are permitted')
    model = model_class.__new__(model_class)
    model.__dict__.update(state)
    model.configs = runner.configs
    model.cleanup = lambda *args, **kwargs: None
    original_overwrite = runner.configs.overwrite
    try:
        runner.configs.overwrite = overwrite
        if action == 'save':
            saved = runner.configs.save_obj(model)
            if saved is False or saved is None:
                raise OSError('Original model checkpoint save failed')
            return ('ok', saved)
        if action == 'can_resume':
            return ('ok', runner.configs.can_resume(model))
        resumed = runner.configs.resume_obj(model)
        return ('ok', resumed, model_state(runner.configs, model) if resumed else None)
    finally:
        runner.configs.overwrite = original_overwrite


def run_models(runner, models, base_model, max_workers, timeout):
    if type(max_workers) is not int or not 1 <= max_workers <= 4:
        raise ValueError('Use one to four model processes')
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 86400:
        raise ValueError('Use a positive model-process deadline up to one day')
    if len(models) != len(set(models)) or base_model not in runner.algorithm_configs or any(
            model not in runner.algorithm_configs for model in models):
        raise ValueError('Distinct configured models and a configured Oracle are required')
    pending = [model for model in models if model != base_model and not (
        not runner.configs.overwrite and model in runner.results
        and float(runner.results[model].get('final_reward', 0.0) or 0.0) > 0)]
    if not pending:
        return
    configuration = {key: value for key, value in vars(runner.configs).items()
                     if key not in ('backup_mgr', 'base_model', 'save_obj', 'resume_obj', 'can_resume')}
    state = {key: value for key, value in vars(runner).items()
             if key not in ('configs', '_save_lock', '_model_lock', '_model_cache')}
    payload = dict(configuration_class=type(runner.configs), configuration=configuration,
                   runner_class=type(runner), runner=state, base_model=base_model,
                   storage_paths=dict(mode=runner.configs.backup_mgr.mode,
                       quantum_data_paths=runner.configs.backup_mgr.quantum_data_paths),
                   oracle_model=None if runner.configs.base_model is None else (
                       type(runner.configs.base_model), model_state(runner.configs, runner.configs.base_model)))
    payload = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
    context = multiprocessing.get_context('spawn')
    active = {}
    started = time.monotonic()
    runner._process_execution = []
    try:
        while pending or active:
            if time.monotonic() - started > timeout:
                raise TimeoutError('Model process deadline; original persisted states are preserved')
            while pending and len(active) < max_workers:
                name = pending.pop(0)
                parent, child = context.Pipe()
                process = context.Process(target=worker, args=(payload, name, child))
                try:
                    with single_thread_environment():
                        process.start()
                except BaseException:
                    parent.close()
                    child.close()
                    raise
                child.close()
                active[parent] = (name, process)
            for connection in wait(active, timeout=0.1):
                name, process = active[connection]
                try:
                    message = receive(connection)
                except EOFError as error:
                    raise RuntimeError('Model process exited without a result: ' + name) from error
                if message[0] in ('save', 'resume', 'can_resume'):
                    try:
                        send(connection, service_request(runner, message))
                    except BaseException as error:
                        send(connection, ('error', type(error).__name__ + ': ' + str(error)))
                        raise
                    continue
                if message[0] == 'error':
                    raise RuntimeError('Model process failed: ' + name + '\n' + message[2])
                if message[0] != 'result' or message[1] != name or message[4:] != (1, 1):
                    raise ValueError('Model process identity/thread count differs')
                result = message[2]
                if (not isinstance(result, dict) or result.get('error')
                        or result.get('algorithm') != name
                        or result.get('seed') != runner.experiment_seed + runner.algorithm_configs[name]['seed_offset']
                        or result.get('frames_count') != runner.frames_count):
                    raise ValueError('Model process result differs from the original runner contract')
                process.join(timeout=min(30, max(0, timeout - (time.monotonic() - started))))
                if process.exitcode != 0:
                    raise RuntimeError('Model process did not exit successfully: ' + name)
                previous_result = runner.results.get(name)
                previous_winner = runner.winner
                runner.results[name] = deepcopy(result)
                runner.winner = max((key for key in runner.results if key != base_model),
                                    key=lambda key: float(runner.results[key].get('final_reward', 0.0) or 0.0))
                try:
                    saved = runner.save()
                    if saved is False or saved is None:
                        raise OSError('Original aggregate runner save failed')
                except BaseException:
                    if previous_result is None:
                        del runner.results[name]
                    else:
                        runner.results[name] = previous_result
                    runner.winner = previous_winner
                    raise
                runner._process_execution.append(dict(model=name, pid=message[3], numeric_threads=1))
                observe_model(runner, name)
                connection.close()
                del active[connection]
    finally:
        for connection, (name, process) in active.items():
            connection.close()
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()
