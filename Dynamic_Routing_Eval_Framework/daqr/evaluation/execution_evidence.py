"""Typed injection seam for execution-time evidence capture.

Campaign implementations live outside the generic evaluator.  The evaluator
only consumes this interface and never imports a campaign package.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from daqr.core.scenario_execution import ScenarioSession


@dataclass
class ExecutionEvidenceAttempt:
    """Validated per-policy attempt supplied by an execution evidence plugin."""

    policy_seed: int
    threat_seed: int | None
    static_availability: np.ndarray | None
    scenario_session: ScenarioSession | None
    event_sink: object
    directory: Path
    _complete: Callable[[dict], dict]
    _fail: Callable[[BaseException], dict]

    def __post_init__(self):
        if type(self.policy_seed) is not int or self.policy_seed < 0:
            raise ValueError("Execution evidence requires a nonnegative policy seed")
        if self.static_availability is None and self.scenario_session is None:
            raise ValueError("Execution evidence requires static availability or a causal session")
        if self.static_availability is not None and self.scenario_session is not None:
            raise ValueError("Execution evidence cannot be both static and causal")
        if self.static_availability is not None:
            value = np.asarray(self.static_availability)
            if value.ndim != 2 or not np.isin(value, [0, 1]).all():
                raise ValueError("Static availability must be a binary frame-by-route matrix")
            self.static_availability = value.astype(np.int8, copy=True)
            self.static_availability.flags.writeable = False
        for name in ("preselection", "decision", "outcome", "update"):
            if not callable(getattr(self.event_sink, name, None)):
                raise TypeError(f"Execution event sink is missing {name}")
        if not callable(self._complete) or not callable(self._fail):
            raise TypeError("Execution evidence attempt requires terminal callbacks")

    @property
    def attack_pattern(self):
        return (
            self.scenario_session.policy_mask
            if self.scenario_session is not None
            else self.static_availability
        )

    def complete(self, result):
        return self._complete(result)

    def fail(self, error):
        return self._fail(error)


class ExecutionEvidencePlugin(ABC):
    """Reusable evaluator plugin; concrete evidence contracts remain external."""

    @abstractmethod
    def register_block(self, block, configuration):
        """Register the strict configuration used to construct one block."""

    @abstractmethod
    def open_attempt(self, runtime_config, policy, threat, block, frames):
        """Return one immutable attempt carrying seeds, availability, and recorder."""

    @abstractmethod
    def finalize(self, runtime_config):
        """Validate and publish the configured matrix completion receipt."""


def validate_execution_evidence_plugin(plugin):
    if plugin is None:
        return None
    if not isinstance(plugin, ExecutionEvidencePlugin):
        raise TypeError("Injected execution evidence must implement ExecutionEvidencePlugin")
    return plugin
