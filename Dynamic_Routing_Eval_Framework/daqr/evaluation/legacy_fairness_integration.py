"""Post-run attachment of the existing fairness workflow to native results."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import tempfile

from .fairness_legacy_sidecar import LegacyFairnessSidecarBridge


class FairnessIntegrationError(RuntimeError):
    pass


class LegacyFairnessIntegration:
    claim_boundary = 'Model-level reward and frame-horizon proxies; not request-level service equity or measured delivery latency'

    def generate(self, evaluator, output_dir=None):
        config = evaluator.configs
        bridge = LegacyFairnessSidecarBridge()
        expected = {(str(threat), str(position)) for threat in config.test_scenarios
                    for position in range(1, config.runs + 1)}
        experiments = list(bridge._iter_legacy_experiments(evaluator))
        if {(threat, position) for threat, position, _ in experiments} != expected:
            raise ValueError('Fairness requires every expected threat experiment to be complete')
        roster = set(config.models)
        if not roster:
            raise ValueError('Fairness requires a model roster')
        for _, _, experiment in experiments:
            results = experiment.get('results', {})
            if set(results) != roster:
                raise ValueError('Fairness requires the exact completed model roster')
            for result in results.values():
                if (not isinstance(result, dict) or result.get('error')
                        or result.get('final_reward') is None
                        or not math.isfinite(float(result['final_reward']))):
                    raise ValueError('Fairness cannot include incomplete model results')
        states = bridge.extract_states(evaluator)
        identity = dict(pipeline=getattr(config, 'pipeline_storage', None),
            source_file=str(getattr(evaluator, 'file_name', 'unknown')),
            source_component=str(getattr(evaluator, 'component', 'framework_state')),
            source_output=str(getattr(evaluator, 'save_to_dir', '')),
            allocator=str(config.allocator), scale=config.scale, base_capacity=config.base_capacity,
            runs=config.runs, base_frames=evaluator.base_frames, frame_step=evaluator.frame_step,
            base_seed=getattr(config, 'base_seed', None), seed_offset=getattr(config, 'seed_offset', None),
            testbed_id=getattr(config, 'testbed_id', None), suffix=getattr(config, 'suffix', None),
            attack_intensity=getattr(config, 'attack_intensity', None), scenarios=config.test_scenarios,
            model_seeds=sorted((threat, position, model, payload.get('seed'))
                for threat, position, experiment in experiments for model, payload in experiment['results'].items()),
            states=sorted(states, key=lambda value: (value['env_type'], value['experiment_id'], value['group'])))
        fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, allow_nan=False).encode()).hexdigest()
        destination = str(Path(output_dir).resolve()) if output_dir is not None else 'pipeline-drive'
        previous = getattr(evaluator, 'fairness_receipt', None)
        if previous and previous.get('source_sha256') == fingerprint and previous.get('destination') == destination:
            if output_dir is None or all(Path(value['path']).is_file() and self.digest(Path(value['path'])) == value['sha256']
                                         for value in previous['artifacts'].values()):
                return previous
        name = 'legacy-' + fingerprint
        if output_dir is not None:
            return self._generate(evaluator, bridge, fingerprint, destination, name, Path(output_dir))
        manager = config.backup_mgr
        if getattr(manager, 'in_share_drive', False):
            root = Path(manager.drive_datalake_base) / 'quantum_data_lake'
            return self._generate(evaluator, bridge, fingerprint, destination, name, root)
        if not getattr(manager, 'remote_available', False) or not getattr(manager, 'drive', None):
            raise RuntimeError('Fairness Drive destination is unavailable; no permanent local fallback')
        with tempfile.TemporaryDirectory(prefix='fairness-', dir=manager.dir) as directory:
            return self._generate(evaluator, bridge, fingerprint, destination, name, Path(directory), manager)

    def _generate(self, evaluator, bridge, fingerprint, destination, name, root, manager=None):
        result = bridge.attach_to_legacy_evaluator(evaluator.configs, evaluator, run_name=name,
            datalake_root=root, source='original-framework-fairness-layer')
        artifacts = {}
        for key, value in asdict(result.workflow_result.artifacts).items():
            if key == 'output_dir' or value is None:
                continue
            path = Path(value)
            artifacts[key] = dict(name=path.name, sha256=self.digest(path), path=str(path))
            if manager is not None:
                if hasattr(manager, 'workflow_upload_receipts'):
                    manager.workflow_upload_receipts.pop(path.name, None)
                uploaded = manager._upload_file_to_drive(component='fairness', date_str=name,
                    local_path=str(path), filename=path.name)
                receipt = getattr(manager, 'workflow_upload_receipts', {}).get(path.name)
                if not uploaded or not receipt or receipt.get('md5') != hashlib.md5(path.read_bytes()).hexdigest():
                    raise RuntimeError('Fairness upload verification pending: ' + path.name)
                artifacts[key].pop('path')
                artifacts[key]['drive'] = dict(receipt)
        receipt = dict(state='done', source_sha256=fingerprint, destination=destination,
            outcome_count=len(result.evaluation_result.outcomes), claim_boundary=self.claim_boundary,
            artifacts=artifacts)
        evaluator.fairness_receipt = receipt
        return receipt

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
