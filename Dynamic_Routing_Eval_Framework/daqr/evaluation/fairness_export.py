from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from daqr.evaluation.fairness_report import FairnessReport


@dataclass(frozen=True)
class FairnessExportBundle:
    markdown: str
    csv: str


class FairnessMarkdownExporter:
    """Exporter for human-readable fairness markdown summaries."""

    def export(self, report: FairnessReport) -> str:
        lines: list[str] = []
        lines.append(f"# Fairness Report: {report.run_spec_name}")
        lines.append("")
        lines.append(f"- Schema: `{report.schema_version}`")
        lines.append(f"- Environment: `{report.environment_family}`")
        lines.append(f"- Adapter: `{report.adapter_name}`")
        lines.append(f"- Outcomes: `{report.outcome_count}`")
        lines.append("")
        lines.append("## Metric Summary")
        lines.append("")
        lines.append("| Metric | Parity Gap | Overall Mean | Min Group | Max Group | Disparity Ratio |")
        lines.append("|---|---:|---:|---|---|---:|")
        for metric in report.metrics:
            lines.append(
                "| {metric} | {parity_gap} | {overall_mean} | {min_group} | {max_group} | {disparity_ratio} |".format(
                    metric=metric.get("metric", ""),
                    parity_gap=self._fmt(metric.get("parity_gap")),
                    overall_mean=self._fmt(metric.get("overall_mean")),
                    min_group=metric.get("min_group") or "",
                    max_group=metric.get("max_group") or "",
                    disparity_ratio=self._fmt(metric.get("disparity_ratio")),
                )
            )
        lines.append("")
        lines.append("## Record Count")
        lines.append("")
        lines.append(f"`{len(report.records)}` flattened report records")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _fmt(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)


class FairnessCSVExporter:
    """Exporter for tabular fairness records."""

    fieldnames = (
        "metric",
        "group",
        "mean",
        "count",
        "overall_mean",
        "min_group",
        "min_group_mean",
        "max_group",
        "max_group_mean",
        "parity_gap",
        "disparity_ratio",
    )

    def export(self, report: FairnessReport) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=self.fieldnames)
        writer.writeheader()
        for record in report.records:
            row = {field: record.get(field) for field in self.fieldnames}
            writer.writerow(row)
        return buffer.getvalue()


class FairnessExportService:
    """Owned export facade for stable fairness report outputs."""

    def __init__(self) -> None:
        self.markdown_exporter = FairnessMarkdownExporter()
        self.csv_exporter = FairnessCSVExporter()

    def export(self, report: FairnessReport) -> FairnessExportBundle:
        return FairnessExportBundle(
            markdown=self.markdown_exporter.export(report),
            csv=self.csv_exporter.export(report),
        )
