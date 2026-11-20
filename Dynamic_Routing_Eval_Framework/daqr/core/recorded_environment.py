"""Primary environment with a supplied, immutable strategy realization."""
import numpy as np
from daqr.core.network_environment import QuantumEnvironment


class RecordedQuantumEnvironment(QuantumEnvironment):
    def __init__(self, *, availability, **kwargs):
        super().__init__(**kwargs)
        mask=np.asarray(availability)
        if mask.shape!=(self.frame_length,self.num_paths) or not np.isin(mask,[0,1]).all():
            raise ValueError("Recorded strategy realization does not match environment")
        self._recorded_availability=mask.copy()
        self._recorded_availability.setflags(write=False)

    def generate_attack_pattern(self):
        return self._recorded_availability
