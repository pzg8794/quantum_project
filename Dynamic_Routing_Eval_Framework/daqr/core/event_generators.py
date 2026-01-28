# daqr/core/event_generators.py

import time
from collections import deque

class EventDrivenRetryQueue:
    """Queue-based retry mechanism for managing failed entanglement attempts."""
    def __init__(self, retry_delay: float = 0.1, max_retries: int = 3, testbed: str = "paper12"):
        self.retry_queue = deque()
        self.retry_delay = retry_delay
        self.max_retries = max_retries

    def register_failure(self, path_id, context, attempt_id=0):
        """Registers a failed attempt for future retry."""
        if attempt_id < self.max_retries:
            retry_time = time.time() + self.retry_delay
            self.retry_queue.append({
                'path_id': path_id,
                'context': context,
                'attempt_id': attempt_id + 1,
                'retry_time': retry_time
            })

    def get_ready_retries(self):
        """Returns all retries ready for execution now."""
        now = time.time()
        ready = []
        still_pending = deque()

        while self.retry_queue:
            event = self.retry_queue.popleft()
            if event['retry_time'] <= now:
                ready.append(event)
            else:
                still_pending.append(event)
        
        self.retry_queue = still_pending
        return ready

    def has_pending(self):
        return len(self.retry_queue) > 0


def compute_retry_fidelity_with_threshold(base_fidelity, threshold=0.7, max_attempts=3, decay_rate=0.95):
    """
    Paper12 retry logic: retry up to N times if fidelity drops below threshold τ.
    
    Args:
        base_fidelity: Initial fidelity value (0-1)
        threshold: Minimum acceptable fidelity (τ)
        max_attempts: Maximum retry attempts (N)
        decay_rate: Fidelity decay per retry (Paper12: ~0.95)
    
    Returns:
        tuple: (final_fidelity, retry_count, success)
    """
    current_fidelity = base_fidelity
    retry_count = 0
    
    while current_fidelity < threshold and retry_count < max_attempts:
        retry_count += 1
        # Paper12: each retry has slight fidelity penalty
        current_fidelity = min(1.0, base_fidelity * (decay_rate ** retry_count))
        
        # Re-attempt with exponential backoff penalty
        if current_fidelity >= threshold:
            break
    
    success = current_fidelity >= threshold
    return current_fidelity, retry_count, success
