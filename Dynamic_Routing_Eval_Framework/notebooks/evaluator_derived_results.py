"""Read completed-result checkpoints without hydrating original runner objects."""
import gzip
import importlib
import io
import pickle


NUMPY_GLOBALS = {
    'numpy': {'ndarray', 'dtype'},
    'numpy.core.multiarray': {'_reconstruct', 'scalar'},
    'numpy._core.multiarray': {'_reconstruct', 'scalar'},
    'numpy.core.numeric': {'_frombuffer'},
    'numpy._core.numeric': {'_frombuffer'},
}


class ResultUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if name in NUMPY_GLOBALS.get(module, ()):
            return getattr(importlib.import_module(module), name)
        raise pickle.UnpicklingError(f'Unexpected result type: {module}.{name}')

    def persistent_load(self, identity):
        raise pickle.UnpicklingError('Unexpected external result reference')


def read_completed_result(pinned, key, *, pipeline, set_id, threat, position, frames, models):
    reference = pinned.experiments[key].get('recoveredState')
    if not reference or reference.get('kind') != 'completed-results-only':
        raise ValueError('Expected a completed-result checkpoint')
    if reference['path'] != f'experiments/{key}/evaluator-derived-runner.pkl.gz':
        raise ValueError('Completed-result checkpoint path differs')
    data = pinned.read(key, 'recoveredState')
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        result = ResultUnpickler(stream).load()
        if stream.read(1):
            raise ValueError('Trailing completed-result checkpoint data')
    if (result['schema'], result['pipeline'], result['setId'], result['threat'],
            result['id'], result['frames_count'], result['is_complete']) != (
            'evaluator-derived-runner-results/v1', pipeline, set_id, threat, position, frames, True):
        raise ValueError('Completed-result checkpoint identity differs')
    if set(result['results']) != set(models) or any(
            item.get('frames_count') != frames or item.get('error') for item in result['results'].values()):
        raise ValueError('Completed-result checkpoint model payload differs')
    return dict(results=result['results'], winner=result['winner'], exp_id=position,
                **({'attack_category': result['attack_category']} if 'attack_category' in result else {}))
