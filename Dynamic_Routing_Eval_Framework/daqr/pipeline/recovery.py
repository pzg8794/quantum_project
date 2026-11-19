"""Owner-approved read-only completion recovery; no evaluator methods or training."""
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import pickle
import sys


def load_compatibility(runtime, manifest_sha256):
    root = Path(runtime).resolve()
    manifest = root.parent / 'runtime-manifest.json'
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest_sha256:
        raise ValueError('Original compatibility source manifest changed')
    hashes = json.loads(raw)
    for name in ('original_legacy_allocator', 'original_legacy_environment'):
        path = root / (name + '.py')
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != hashes[name + '.py']:
            raise ValueError('Original saved-state compatibility source changed')
        if name in sys.modules:
            if Path(sys.modules[name].__file__).resolve() != path:
                raise ValueError('Conflicting saved-state compatibility module')
            continue
        specification = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(specification)
        sys.modules[name] = module
        try:
            specification.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise


def load_projector(path, source_sha256):
    path = Path(path).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != source_sha256:
        raise ValueError('Existing saved-output projection source changed')
    specification = importlib.util.spec_from_file_location('_pipeline_saved_projection', path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module.project_saved_evaluator


def recover_completion(service, reference, projector, *, target_runs=6, maximum_bytes=512 * 1024**2):
    size = reference.get('byte_length')
    if type(size) is not int or not 0 < size <= maximum_bytes:
        raise ValueError('Bounded exact archive byte length required')
    raw = service.files().get_media(fileId=reference['provider_id'], supportsAllDrives=True).execute()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != reference['content_sha256']:
        raise ValueError('Original saved archive bytes differ')
    payload = pickle.loads(raw)
    del raw
    try:
        if not isinstance(payload, dict) or payload.get('runs_id') != target_runs:
            raise ValueError('Recorded archive does not match the requested run target')
        binding = projector(payload, reference)
        config = payload.get('configs')
        values = vars(config) if config is not None and hasattr(config, '__dict__') else {}
        saved = {}
        unrecorded = []
        for name in ('physics_params', 'seed_offset', 'env_type', 'suffix', 'attack_intensity',
                'attack_rate', 'base_seed', 'testbed_id', 'testbed_config'):
            if name not in values:
                unrecorded.append(name)
                continue
            try:
                encoded = json.dumps(values[name], allow_nan=False)
                saved[name] = json.loads(encoded)
            except (TypeError, ValueError):
                unrecorded.append(name)
        return dict(schema='saved-completion-recovery/v1', binding=binding,
            savedScientificSettings=saved, unrecordedScientificSettings=unrecorded,
            runnerPayloadsPresent=any(payload.get(name) for name in ('runner_states', 'runners')),
            modelPayloadsPresent=bool(payload.get('model_states')),
            evaluatorsResumed=0, trainingCalls=0)
    finally:
        del payload
        gc.collect()
