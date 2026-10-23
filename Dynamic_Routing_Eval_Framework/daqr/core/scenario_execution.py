"""Causal scenario lifecycle; strategy RNG is separate from policy RNG.

begin(t): history contains exactly the completed selections [0,t).
Availability is fixed before the current selector. observe(t,route) is called
after feedback/update. No rewards, current action, policy internals or future
selections are passed to a strategy. Initial history is legitimately empty only
at t=0, not a substitute for absent history during a run.
"""
import numpy as np


class ScenarioSession:
    def __init__(self, strategy, rng, frames, routes):
        strategy.validate_execution()
        strategy._validate_inputs(frames, routes)
        self.strategy, self.rng = strategy, rng
        self.frames, self.routes = frames, routes
        self.history = []
        self.state = {}
        self.pending = False
        self.precomputed = (self._validate(strategy.generate(rng,frames,routes), (frames,routes))
                            if strategy.mask_capability == "static" else None)
        if self.precomputed is not None:
            self.precomputed.flags.writeable = False
        self.realized = np.full((frames,routes), -1, dtype=np.int8)
        # Policy buffer contains no fabricated future availability. Causal policies
        # must declare support; -1 is never a valid mask or a completed observation.
        self.policy_mask = self.precomputed if self.precomputed is not None else self.realized.view()
        self.policy_mask.flags.writeable = False

    @staticmethod
    def _validate(value, shape):
        value = np.asarray(value)
        if value.shape != shape or not np.isin(value,[0,1]).all():
            raise ValueError("Availability must be binary and correctly shaped")
        return value.astype(np.int8,copy=True)

    def __len__(self):
        return self.frames

    def begin(self, frame):
        if self.pending or frame != len(self.history) or frame >= self.frames:
            raise ValueError("Scenario frame/history cutoff violation")
        row = (self.precomputed[frame] if self.precomputed is not None else
               self.strategy.availability_at(frame, tuple(self.history), self.state,
                                             self.rng, self.routes, self.frames))
        self.realized[frame] = self._validate(row, (self.routes,))
        self.pending = True
        return self.realized[frame].copy()

    def observe(self, frame, route):
        if not self.pending or frame != len(self.history) or not 0 <= route < self.routes:
            raise ValueError("Scenario observation chronology violation")
        self.history.append(int(route))
        self.pending = False

    def completed_mask(self):
        if self.pending or len(self.history) != self.frames:
            raise ValueError("Incomplete causal trajectory")
        return self.realized.copy()
