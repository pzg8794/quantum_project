"""Compose the existing Spectrum runtime with explicitly selected pipeline storage."""
from datetime import datetime
import importlib
import math
from pathlib import Path
import sys

from .options import PipelineOptions


def load_spectrum_runtime(source_root):
    source_root = Path(source_root).expanduser().resolve(strict=True)
    scientific_modules = ('daqr.config.experiment_config',
        'daqr.core.network_environment', 'daqr.evaluation.allocator_runner',
        'daqr.evaluation.experiment_runner')
    if any(name in sys.modules for name in scientific_modules):
        raise RuntimeError('Open this Spectrum notebook in a fresh kernel; no module reloads are safe here')
    from daqr.config.local_backup_manager import LocalBackupManager
    storage_module = sys.modules[LocalBackupManager.__module__]
    sys.path.insert(0, str(source_root))
    importlib.invalidate_caches()
    runtime = importlib.import_module('daqr.campaigns.spectrum_three')
    for name in (*scientific_modules, 'daqr.campaigns.spectrum_three'):
        module = importlib.import_module(name)
        if not Path(module.__file__).resolve().is_relative_to(source_root):
            raise RuntimeError('Wrong Spectrum module origin: ' + name)
    return runtime, LocalBackupManager, {
        'spectrum': str(Path(runtime.__file__).resolve()),
        'storage': str(Path(storage_module.__file__).resolve()),
    }


def validate_requested_stages(options, preparation_adapter=None):
    if not isinstance(options, PipelineOptions):
        raise TypeError('PipelineOptions is required')
    if options.prepare_data and not options.fairness:
        raise ValueError('The existing preparation contract requires fairness sidecars')
    if options.prepare_data and not (options.prep_cohort_set or options.prep_allocator_set):
        raise ValueError('Select prep_cohort_set and/or prep_allocator_set')
    if options.prepare_data and preparation_adapter is None:
        raise RuntimeError('Canonical preparation adapter with verified source/member references is required')
    if preparation_adapter is not None:
        for name in ('prepare_cohort', 'prepare_allocator'):
            if not callable(getattr(preparation_adapter, name, None)):
                raise TypeError('Preparation adapter must implement ' + name)


def run_spectrum_pipeline(pipeline, runtime, manager, *, output_root,
        topology_levels=(2, 3), scales=(1, 1.5, 2), replays=('T', 'Tb'),
        allocators=('Default', 'Random', 'Dynamic', 'ThompsonSampling'),
        run_count=1, base_frames=2, frame_step=0, preparation_adapter=None,
        artifact_publisher=None):
    options = pipeline.options
    validate_requested_stages(options, preparation_adapter)
    if not callable(artifact_publisher):
        raise RuntimeError('A verified native-state/evidence Drive publisher is required before execution')
    binding = pipeline.storage_binding
    if not binding or getattr(manager, 'pipeline_storage', None) != binding:
        raise ValueError('Manager must belong to this registered pipeline Drive')
    if not getattr(manager, 'remote_available', False) or not getattr(manager, 'drive', None):
        raise RuntimeError('Pipeline Drive is unavailable; no local fallback')
    plan = tuple((allocator, level, replay, scale) for allocator in allocators
        for level in topology_levels for replay in replays for scale in scales)
    if not plan or len(set(plan)) != len(plan):
        raise ValueError('Select a nonempty, unique Spectrum scope')
    runtime.validate_horizons(base_frames, frame_step)
    for _, level, replay, scale in plan:
        runtime.route_count(level)
        if replay not in ('T', 'Tb') or not math.isfinite(scale) or scale <= 0:
            raise ValueError('Invalid Spectrum replay/capacity scope')
        for block in runtime.block_ids(run_count):
            horizon = base_frames if replay == 'Tb' else base_frames + frame_step * block
            if not float(horizon * scale).is_integer():
                raise ValueError('Native replay capacity must be an integer; scale 1.5 needs an even horizon')
    root = Path(output_root).expanduser().resolve()
    if root.exists():
        raise FileExistsError('Choose a fresh temporary execution directory')
    receipts = []
    for allocator in allocators:
        allocator_receipts = []
        for selected, level, replay, scale in plan:
            if selected != allocator:
                continue
            cohort = f'm{level}:S{scale:g}{replay}'
            directory = root / allocator / cohort.replace(':', '-')
            stages = {}
            def postprocess(evaluator):
                evaluator.configs.pipeline_options = options.to_dict()
                if options.fairness:
                    from daqr.evaluation.legacy_fairness_integration import LegacyFairnessIntegration
                    stages['fairness'] = LegacyFairnessIntegration().generate(evaluator)
            native_receipt = runtime.run_cell(directory, scale_m=level,
                replay=replay, capacity_scale=scale, run_count=run_count,
                allocator_type=allocator, base_frames=base_frames,
                frame_step=frame_step, backup_manager=manager,
                on_evaluator_complete=postprocess)
            publication = artifact_publisher(pipeline=pipeline, cohort=cohort,
                allocator=allocator, output_root=directory,
                state_root=Path(manager.dir), fairness=stages.get('fairness'), manager=manager)
            if not isinstance(publication, dict) or publication.get('verified') is not True:
                raise RuntimeError('Drive artifact publication is not verified; preserve temporary staging')
            if options.prep_cohort_set:
                stages['prepared'] = preparation_adapter.prepare_cohort(
                    pipeline=pipeline, cohort=cohort, allocator=allocator,
                    source_references=publication, fairness=stages.get('fairness'), manager=manager)
                if not isinstance(stages['prepared'], dict) or stages['prepared'].get('analysis_ready') is not True:
                    raise RuntimeError('Cohort preparation is not analysis-ready')
            receipt = dict(pipeline=pipeline.pipeline_key, cohort=cohort,
                allocator=allocator, native_receipt=str(native_receipt), stages=stages,
                publication=publication,
                completed_at=datetime.now().astimezone().isoformat())
            receipts.append(receipt)
            allocator_receipts.append(receipt)
            print(pipeline.pipeline_key, allocator, cohort, 'completed')
        if options.prep_allocator_set:
            prepared = preparation_adapter.prepare_allocator(pipeline=pipeline,
                allocator=allocator, cohorts=allocator_receipts, manager=manager)
            if not isinstance(prepared, dict) or prepared.get('analysis_ready') is not True:
                raise RuntimeError('Allocator preparation is not analysis-ready')
            for receipt in allocator_receipts:
                receipt['allocator_prepared'] = prepared
    return receipts
