from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from daqr.config.outcome_record import OutcomeRecord
from daqr.config.run_spec import RunSpec


@dataclass(frozen=True)
class FairnessEvent:
    event_id: str
    event_type: str
    timestamp_utc: str
    run_spec_name: str
    environment_family: str
    group: str | None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FairnessEventLogger:
    """Owned event logger for fairness-relevant decisions and outcomes."""

    events: list[FairnessEvent] = field(default_factory=list)
    _counter: int = 0

    def log_outcome(self, run_spec: RunSpec, outcome: OutcomeRecord) -> FairnessEvent:
        payload = {
            "success": outcome.success,
            "latency": outcome.latency,
            "reward": outcome.reward,
            "protected_attributes": outcome.protected_attributes,
            "context": outcome.context,
            "testbed_id": outcome.testbed_id,
        }
        event = self._build_event(
            event_type="outcome_observed",
            run_spec=run_spec,
            group=outcome.group,
            payload=payload,
        )
        self.events.append(event)
        return event

    def log_decision(
        self,
        run_spec: RunSpec,
        *,
        group: str | None,
        decision: str,
        payload: Mapping[str, Any] | None = None,
    ) -> FairnessEvent:
        merged_payload = {"decision": decision}
        if payload:
            merged_payload.update(dict(payload))
        event = self._build_event(
            event_type="decision_made",
            run_spec=run_spec,
            group=group,
            payload=merged_payload,
        )
        self.events.append(event)
        return event

    def export_jsonl(self, output_path: str | Path) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(json.dumps(event.to_dict(), sort_keys=True))
                handle.write("\n")
        return str(path)

    def _build_event(
        self,
        *,
        event_type: str,
        run_spec: RunSpec,
        group: str | None,
        payload: Mapping[str, Any],
    ) -> FairnessEvent:
        self._counter += 1
        return FairnessEvent(
            event_id=f"fairness-event-{self._counter:05d}",
            event_type=event_type,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            run_spec_name=run_spec.name,
            environment_family=run_spec.environment_family,
            group=group,
            payload=dict(payload),
        )
