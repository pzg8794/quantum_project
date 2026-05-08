"""Code-render ICNP graph artifacts for the validation hub.

Validation here is intentionally source-code based. The helper discovers graph
scripts in the requested QuantumFaultTolerant directories, executes each script,
intercepts Plotly/Matplotlib save calls, removes plot titles before rendering,
and records the code/data/render contract for reviewer feedback.

Important: this module does not crop source images. Every displayed image is
rendered from code during the notebook run.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import inspect
import io
import linecache
import os
import re
import runpy
import shutil
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from IPython.display import Image, Markdown, display


GA_WORK_ROOT = Path("/Users/pitergarcia/DataScience/Semester4/GA-Work")
PAPER_REPO = GA_WORK_ROOT / "GA Papers/QuantumFaultTolerant"
FRAMEWORK_REPO = GA_WORK_ROOT / "hybrid_variable_framework/Dynamic_Routing_Eval_Framework"
RENDER_DIR = FRAMEWORK_REPO / "notebooks/generated/icnp_validation_code_rendered"
PANEL_CODE_DIR = FRAMEWORK_REPO / "notebooks/generated/icnp_validation_panel_code"
VALID_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf", ".eps"}

SOURCE_DIRS = [
    PAPER_REPO / "tools/icnp-exported-assets-2",
    PAPER_REPO / "figures",
]


@dataclass
class RenderRecord:
    review_id: str
    title: str
    source_script: Path
    declared_output: str
    display_path: Path
    renderer: str
    record_type: str
    data_contract: str
    render_contract: str
    trace_or_axes_count: int | None = None
    parent_review_id: str | None = None
    panel_code_path: Path | None = None
    status: str = "code-rendered"


@dataclass
class ScriptRunResult:
    source_script: Path
    stdout: str
    stderr: str
    error: str | None
    records: list[RenderRecord]


@dataclass
class PlotlyPanelShadow:
    figure_key: int
    row: int
    col: int
    label: str
    title: str
    fig: Any
    call_sites: list[str]
    trace_count: int = 0


@dataclass
class MplPanelShadow:
    figure_key: int
    label: str
    title: str
    fig: Any
    ax: Any
    call_sites: list[str]
    call_count: int = 0


def natural_key(path: Path) -> list[object]:
    try:
        text = str(path.relative_to(PAPER_REPO))
    except ValueError:
        text = str(path)
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def source_label(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(PAPER_REPO))
    except ValueError:
        try:
            return str(path.relative_to(FRAMEWORK_REPO))
        except ValueError:
            return str(path)


def safe_slug(*parts: object) -> str:
    raw = "__".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")[:120]
    return f"{slug}_{digest}"


def panel_label_from_index(index: int) -> str:
    return chr(ord("A") + index - 1) if 1 <= index <= 26 else f"Panel {index}"


def flatten_axes(obj: Any) -> list[Any]:
    if obj is None:
        return []
    if isinstance(obj, (list, tuple)):
        out: list[Any] = []
        for item in obj:
            out.extend(flatten_axes(item))
        return out
    if hasattr(obj, "flat"):
        return [item for item in obj.flat]
    return [obj]


def clean_panel_title(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", str(text), flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
    text = re.sub(r"^[A-I][.)]\s*", "", text)
    return re.sub(r"\s+", " ", text)


def map_mpl_shadow_kwargs(kwargs: dict[str, Any], source_ax: Any, shadow_ax: Any) -> dict[str, Any]:
    mapped = dict(kwargs)
    if mapped.get("transform") == source_ax.transAxes:
        mapped["transform"] = shadow_ax.transAxes
    elif mapped.get("transform") == source_ax.transData:
        mapped["transform"] = shadow_ax.transData
    return mapped


def is_title_like_mpl_text(source_ax: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> bool:
    if len(args) < 3:
        return False
    x, y, text = args[0], args[1], str(args[2])
    transform = kwargs.get("transform")
    uses_axes_coords = transform == source_ax.transAxes
    if not uses_axes_coords:
        return False
    try:
        x_value = float(x)
        y_value = float(y)
    except (TypeError, ValueError):
        return False
    if re.fullmatch(r"[A-I]", text.strip()) and (x_value < 0.02 or y_value >= 0.95):
        return True
    return y_value >= 1.0 and len(text.strip()) <= 120


def format_callsite(script: Path | None) -> str:
    if script is None:
        return "unknown source call"
    script_resolved = script.resolve()
    for frame_info in inspect.stack()[2:]:
        try:
            frame_path = Path(frame_info.filename).resolve()
        except OSError:
            continue
        if frame_path == script_resolved:
            code_line = linecache.getline(frame_info.filename, frame_info.lineno).strip()
            return f"{source_label(script)}:{frame_info.lineno}: {code_line}"
    return f"{source_label(script)}: source call site unavailable"


def write_panel_code_manifest(
    *,
    source_script: Path,
    review_id: str,
    title: str,
    renderer: str,
    record_type: str,
    call_sites: list[str],
) -> Path:
    PANEL_CODE_DIR.mkdir(parents=True, exist_ok=True)
    path = PANEL_CODE_DIR / f"{safe_slug(review_id, source_label(source_script), title)}.py"
    calls = "\n".join(f"    {call_site!r}," for call_site in dict.fromkeys(call_sites))
    path.write_text(
        '"""Panel-specific validation manifest.\n\n'
        "This is not an image-crop recipe. The validation image for this panel\n"
        "is produced by executing the source script and mirroring the panel's own\n"
        "source plotting calls onto a clean standalone figure while the script runs.\n"
        "Titles/subtitles captured from the source are intentionally supplied by\n"
        "Markdown in the notebook, not embedded in the rendered image.\n"
        '"""\n\n'
        f"SOURCE_SCRIPT = {str(source_script)!r}\n"
        f"REVIEW_ID = {review_id!r}\n"
        f"PANEL_TITLE_FOR_MARKDOWN = {title!r}\n"
        f"RENDERER = {renderer!r}\n"
        f"RECORD_TYPE = {record_type!r}\n"
        "SOURCE_PLOTTING_CALLS = [\n"
        f"{calls}\n"
        "]\n",
        encoding="utf-8",
    )
    return path


def discover_graph_scripts() -> list[Path]:
    pattern = re.compile(r"\.(?:write_image|savefig)\s*\(")
    scripts: list[Path] = []
    for root in SOURCE_DIRS:
        if not root.exists():
            continue
        for script in root.rglob("*.py"):
            if "__pycache__" in script.parts:
                continue
            text = script.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                scripts.append(script)
    return sorted(set(scripts), key=natural_key)


def declared_outputs(script: Path) -> list[str]:
    text = script.read_text(encoding="utf-8", errors="ignore")
    outputs = re.findall(r"\.(?:write_image|savefig)\s*\(\s*(?:r)?['\"]([^'\"]+)['\"]", text)
    return list(dict.fromkeys(outputs))


def infer_title_from_output(output: str, fallback: str) -> str:
    stem = Path(str(output)).stem
    stem = re.sub(r"_\d+$", "", stem)
    title = stem.replace("_", " ").replace("-", " ").strip()
    title = re.sub(r"\bG(\d+)\b", r"G\1", title, flags=re.I)
    return title.title() if title else fallback.replace("_", " ").title()


def strip_plotly_titles(fig: Any) -> Any:
    """Return a Plotly figure copy with figure/subplot titles removed."""
    import plotly.graph_objects as go

    clean = go.Figure(fig)
    clean.update_layout(title=None)

    # Plotly subplot titles are stored as paper-coordinate annotations. Preserve
    # data annotations while removing title-like paper annotations.
    annotations = []
    for annotation in list(clean.layout.annotations or []):
        xref = getattr(annotation, "xref", None)
        yref = getattr(annotation, "yref", None)
        text = str(getattr(annotation, "text", "") or "")
        title_like = xref == "paper" and yref == "paper" and not getattr(annotation, "showarrow", False)
        title_like = title_like and (
            bool(re.match(r"^[A-I][.)]\\s", text))
            or "panel" in text.lower()
            or getattr(annotation, "y", 0) >= 0.92
            or text.startswith("G")
        )
        if not title_like:
            annotations.append(annotation)
    clean.update_layout(annotations=annotations)
    return clean


def plotly_axis_name(trace_axis: str | None, prefix: str) -> str:
    axis = trace_axis or prefix
    if axis == prefix:
        return f"{prefix}axis"
    return f"{prefix}axis{axis[len(prefix):]}"


def get_layout_axis(fig: Any, trace_axis: str | None, prefix: str) -> dict[str, Any]:
    axis_name = plotly_axis_name(trace_axis, prefix)
    axis = getattr(fig.layout, axis_name, None)
    if axis is None:
        return {}
    out = axis.to_plotly_json()
    out.pop("domain", None)
    out.pop("anchor", None)
    return out


def render_plotly_subplots(
    collector: "CodeRenderCollector",
    fig: Any,
    source_script: Path,
    declared_output: str,
    parent_id: str,
    title_base: str,
) -> list[RenderRecord]:
    import plotly.graph_objects as go

    axis_pairs: list[tuple[str, str]] = []
    for trace in fig.data:
        pair = (getattr(trace, "xaxis", None) or "x", getattr(trace, "yaxis", None) or "y")
        if pair not in axis_pairs:
            axis_pairs.append(pair)
    if len(axis_pairs) <= 1:
        return []

    records: list[RenderRecord] = []
    for panel_index, (xaxis_id, yaxis_id) in enumerate(axis_pairs, start=1):
        panel_label = chr(ord("A") + panel_index - 1)
        panel = go.Figure()
        for trace in fig.data:
            if (getattr(trace, "xaxis", None) or "x", getattr(trace, "yaxis", None) or "y") != (xaxis_id, yaxis_id):
                continue
            trace_json = trace.to_plotly_json()
            trace_json.pop("xaxis", None)
            trace_json.pop("yaxis", None)
            panel.add_trace(trace_json)

        panel.update_layout(
            template=getattr(fig.layout, "template", None),
            showlegend=bool(getattr(fig.layout, "showlegend", True)),
            width=getattr(fig.layout, "width", None) or 900,
            height=max(500, int((getattr(fig.layout, "height", None) or 700) * 0.75)),
            margin=dict(l=70, r=40, t=30, b=70),
            xaxis=get_layout_axis(fig, xaxis_id, "x"),
            yaxis=get_layout_axis(fig, yaxis_id, "y"),
        )
        panel = strip_plotly_titles(panel)

        display_path = collector.next_output_path(source_script, f"{declared_output}_panel_{panel_label}", "plotly_panel")
        collector.original_plotly_write_image(panel, str(display_path))
        records.append(
            RenderRecord(
                review_id=collector.next_review_id(),
                title=f"{title_base} — Panel {panel_label}",
                source_script=source_script,
                declared_output=declared_output,
                display_path=display_path,
                renderer="plotly",
                record_type="individual subplot re-rendered from Plotly trace data",
                data_contract=f"Panel {panel_label} was rebuilt from the Plotly Figure traces assigned to axes {xaxis_id}/{yaxis_id}.",
                render_contract="Generated as a new Plotly Figure from source-script traces; layout title/subplot title annotations removed before export.",
                trace_or_axes_count=sum(
                    1
                    for trace in fig.data
                    if (getattr(trace, "xaxis", None) or "x", getattr(trace, "yaxis", None) or "y") == (xaxis_id, yaxis_id)
                ),
                parent_review_id=parent_id,
            )
        )
    return records


def strip_mpl_titles(fig: Any) -> None:
    if getattr(fig, "_suptitle", None) is not None:
        fig._suptitle.set_text("")
    for ax in fig.axes:
        ax.set_title("", loc="left")
        ax.set_title("", loc="center")
        ax.set_title("", loc="right")


def copy_mpl_axis_from_code(ax: Any, display_path: Path, savefig_func: Any) -> None:
    """Replay a Matplotlib Axes into a new figure from artist data, not pixels."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.collections import PathCollection, PolyCollection

    fig2, ax2 = plt.subplots(figsize=(8.5, 5.4))

    for image in ax.images:
        clim = image.get_clim()
        ax2.imshow(
            image.get_array(),
            cmap=image.get_cmap(),
            vmin=clim[0],
            vmax=clim[1],
            aspect=image.get_aspect() if hasattr(image, "get_aspect") else "auto",
            origin=image.origin,
        )

    for patch in ax.patches:
        if isinstance(patch, mpatches.Rectangle):
            rect = mpatches.Rectangle(
                patch.get_xy(),
                patch.get_width(),
                patch.get_height(),
                angle=patch.angle,
                facecolor=patch.get_facecolor(),
                edgecolor=patch.get_edgecolor(),
                linewidth=patch.get_linewidth(),
                alpha=patch.get_alpha(),
            )
            ax2.add_patch(rect)
        elif isinstance(patch, mpatches.PathPatch):
            clone = mpatches.PathPatch(
                copy.deepcopy(patch.get_path()),
                facecolor=patch.get_facecolor(),
                edgecolor=patch.get_edgecolor(),
                linewidth=patch.get_linewidth(),
                alpha=patch.get_alpha(),
            )
            clone.set_transform(ax2.transData)
            ax2.add_patch(clone)

    for line in ax.lines:
        xdata = line.get_xdata(orig=False)
        ydata = line.get_ydata(orig=False)
        if len(xdata) == 0 or len(ydata) == 0:
            continue
        ax2.plot(
            xdata,
            ydata,
            color=line.get_color(),
            linestyle=line.get_linestyle(),
            linewidth=line.get_linewidth(),
            marker=line.get_marker(),
            markersize=line.get_markersize(),
            alpha=line.get_alpha(),
            label=line.get_label() if not str(line.get_label()).startswith("_") else None,
        )

    for collection in ax.collections:
        if isinstance(collection, PathCollection):
            offsets = collection.get_offsets()
            if len(offsets):
                facecolors = collection.get_facecolors()
                edgecolors = collection.get_edgecolors()
                sizes = collection.get_sizes()
                ax2.scatter(
                    offsets[:, 0],
                    offsets[:, 1],
                    s=sizes if len(sizes) else None,
                    c=facecolors if len(facecolors) else None,
                    edgecolors=edgecolors if len(edgecolors) else None,
                    alpha=collection.get_alpha(),
                )
        elif isinstance(collection, PolyCollection):
            for path, facecolor in zip(collection.get_paths(), collection.get_facecolors()):
                clone = mpatches.PathPatch(
                    copy.deepcopy(path),
                    facecolor=facecolor,
                    edgecolor=collection.get_edgecolors()[0] if len(collection.get_edgecolors()) else "none",
                    alpha=collection.get_alpha(),
                )
                clone.set_transform(ax2.transData)
                ax2.add_patch(clone)

    for text in ax.texts:
        value = text.get_text()
        if not value:
            continue
        transform = ax2.transAxes if text.get_transform() == ax.transAxes else ax2.transData
        ax2.text(
            *text.get_position(),
            value,
            fontsize=text.get_fontsize(),
            color=text.get_color(),
            ha=text.get_ha(),
            va=text.get_va(),
            rotation=text.get_rotation(),
            transform=transform,
        )

    ax2.set_xlabel(ax.get_xlabel())
    ax2.set_ylabel(ax.get_ylabel())
    ax2.set_xlim(ax.get_xlim())
    ax2.set_ylim(ax.get_ylim())
    ax2.set_xscale(ax.get_xscale())
    ax2.set_yscale(ax.get_yscale())
    ax2.set_xticks(ax.get_xticks())
    ax2.set_yticks(ax.get_yticks())
    if ax.get_xticklabels():
        ax2.set_xticklabels([tick.get_text() for tick in ax.get_xticklabels()], rotation=0)
    if ax.get_yticklabels():
        ax2.set_yticklabels([tick.get_text() for tick in ax.get_yticklabels()])
    if ax.get_legend() is not None:
        handles, labels = ax2.get_legend_handles_labels()
        if labels:
            ax2.legend(handles, labels, frameon=True)
    ax2.grid(ax.xaxis._major_tick_kw.get("gridOn", False) or ax.yaxis._major_tick_kw.get("gridOn", False), alpha=0.25)
    fig2.tight_layout()
    savefig_func(fig2, str(display_path), dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig2)


class CodeRenderCollector:
    def __init__(self, render_dir: Path):
        self.render_dir = render_dir
        self.records: list[RenderRecord] = []
        self.current_script: Path | None = None
        self._review_counter = 0
        self._output_counter = 0
        self.original_plotly_write_image = None
        self.original_plotly_add_trace = None
        self.original_plotly_update_xaxes = None
        self.original_plotly_update_yaxes = None
        self.original_plotly_update_layout = None
        self.original_plotly_make_subplots = None
        self.original_mpl_savefig = None
        self.original_mpl_add_subplot = None
        self.original_plt_subplots = None
        self.original_mpl_colorbar = None
        self.original_mpl_axis_methods: dict[str, Any] = {}
        self.original_mpl_artist_methods: dict[tuple[Any, str], Any] = {}
        self.plotly_subplot_meta: dict[int, dict[str, Any]] = {}
        self.plotly_panel_shadows: dict[tuple[int, int, int], PlotlyPanelShadow] = {}
        self.mpl_axis_shadows: dict[int, MplPanelShadow] = {}
        self.mpl_figure_shadows: dict[int, list[MplPanelShadow]] = {}
        self.mpl_mappable_shadows: dict[int, Any] = {}
        self.mpl_artist_shadows: dict[int, Any] = {}
        self._plotly_mirror_depth = 0
        self._mpl_mirror_depth = 0

    def next_review_id(self) -> str:
        self._review_counter += 1
        return f"ICNP-CODE-{self._review_counter:03d}"

    def next_output_path(self, source_script: Path, declared_output: str, renderer: str) -> Path:
        self._output_counter += 1
        suffix = Path(str(declared_output)).suffix or ".png"
        if suffix.lower() not in VALID_IMAGE_SUFFIXES:
            suffix = ".png"
        slug = safe_slug(source_label(source_script), declared_output, renderer, self._output_counter)
        path = self.render_dir / f"{slug}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def reset_script_render_state(self) -> None:
        self.plotly_subplot_meta.clear()
        self.plotly_panel_shadows.clear()
        self.mpl_axis_shadows.clear()
        self.mpl_figure_shadows.clear()
        self.mpl_mappable_shadows.clear()
        self.mpl_artist_shadows.clear()

    @staticmethod
    def mirror_declared_output(rendered_path: Path, declared_output: str) -> None:
        """Write the script's declared output in the temp cwd for later script code."""
        target = Path(str(declared_output))
        if target.is_absolute():
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rendered_path, target)

    @contextlib.contextmanager
    def suspend_plotly_mirror(self):
        self._plotly_mirror_depth += 1
        try:
            yield
        finally:
            self._plotly_mirror_depth -= 1

    @contextlib.contextmanager
    def suspend_mpl_mirror(self):
        self._mpl_mirror_depth += 1
        try:
            yield
        finally:
            self._mpl_mirror_depth -= 1

    def plotly_make_subplots(self, *args: Any, **kwargs: Any) -> Any:
        fig = self.original_plotly_make_subplots(*args, **kwargs)
        rows = int(kwargs.get("rows", args[0] if args else 1) or 1)
        cols = int(kwargs.get("cols", args[1] if len(args) > 1 else 1) or 1)
        titles = list(kwargs.get("subplot_titles") or [])
        self.plotly_subplot_meta[id(fig)] = {"rows": rows, "cols": cols, "titles": titles}
        return fig

    def get_plotly_panel_shadow(self, fig: Any, row: int, col: int) -> PlotlyPanelShadow:
        import plotly.graph_objects as go

        figure_key = id(fig)
        key = (figure_key, row, col)
        if key in self.plotly_panel_shadows:
            return self.plotly_panel_shadows[key]
        meta = self.plotly_subplot_meta.get(figure_key, {})
        cols = int(meta.get("cols", 1))
        panel_index = (row - 1) * cols + col
        label = panel_label_from_index(panel_index)
        titles = meta.get("titles") or []
        title = clean_panel_title(titles[panel_index - 1]) if panel_index - 1 < len(titles) else f"Panel {label}"
        panel = go.Figure()
        panel.update_layout(template=getattr(fig.layout, "template", None))
        shadow = PlotlyPanelShadow(
            figure_key=figure_key,
            row=row,
            col=col,
            label=label,
            title=title or f"Panel {label}",
            fig=panel,
            call_sites=[],
        )
        self.plotly_panel_shadows[key] = shadow
        return shadow

    def plotly_add_trace(self, fig: Any, trace: Any, *args: Any, **kwargs: Any) -> Any:
        result = self.original_plotly_add_trace(fig, trace, *args, **kwargs)
        if self._plotly_mirror_depth or id(fig) not in self.plotly_subplot_meta:
            return result
        row = kwargs.get("row")
        col = kwargs.get("col")
        if row is None and args:
            row = args[0]
        if col is None and len(args) > 1:
            col = args[1]
        if row is None or col is None:
            return result

        shadow = self.get_plotly_panel_shadow(fig, int(row), int(col))
        trace_payload = trace.to_plotly_json() if hasattr(trace, "to_plotly_json") else copy.deepcopy(trace)
        with self.suspend_plotly_mirror():
            self.original_plotly_add_trace(shadow.fig, trace_payload)
        shadow.trace_count += 1
        shadow.call_sites.append(format_callsite(self.current_script))
        return result

    def plotly_update_axis(self, axis_name: str, fig: Any, *args: Any, **kwargs: Any) -> Any:
        original = self.original_plotly_update_xaxes if axis_name == "x" else self.original_plotly_update_yaxes
        result = original(fig, *args, **kwargs)
        if self._plotly_mirror_depth or id(fig) not in self.plotly_subplot_meta:
            return result

        row = kwargs.get("row")
        col = kwargs.get("col")
        panel_kwargs = dict(kwargs)
        panel_kwargs.pop("row", None)
        panel_kwargs.pop("col", None)
        targets = []
        if row is not None and col is not None:
            targets = [self.get_plotly_panel_shadow(fig, int(row), int(col))]
        else:
            targets = [shadow for key, shadow in self.plotly_panel_shadows.items() if key[0] == id(fig)]

        with self.suspend_plotly_mirror():
            for shadow in targets:
                original(shadow.fig, *args, **panel_kwargs)
                shadow.call_sites.append(format_callsite(self.current_script))
        return result

    def plotly_update_layout(self, fig: Any, *args: Any, **kwargs: Any) -> Any:
        result = self.original_plotly_update_layout(fig, *args, **kwargs)
        if self._plotly_mirror_depth or id(fig) not in self.plotly_subplot_meta:
            return result
        panel_kwargs = dict(kwargs)
        panel_kwargs.pop("title", None)
        panel_kwargs.pop("annotations", None)
        panel_kwargs.pop("grid", None)
        panel_kwargs.pop("height", None)
        panel_kwargs.pop("width", None)
        if not panel_kwargs and not args:
            return result
        with self.suspend_plotly_mirror():
            for key, shadow in self.plotly_panel_shadows.items():
                if key[0] == id(fig):
                    self.original_plotly_update_layout(shadow.fig, *args, **panel_kwargs)
                    shadow.call_sites.append(format_callsite(self.current_script))
        return result

    def render_plotly_panel_shadows(self, fig: Any, declared: str, parent_id: str, title_base: str) -> list[RenderRecord]:
        assert self.current_script is not None
        shadows = [
            shadow
            for key, shadow in sorted(self.plotly_panel_shadows.items(), key=lambda item: (item[1].row, item[1].col))
            if key[0] == id(fig) and shadow.trace_count
        ]
        records: list[RenderRecord] = []
        for shadow in shadows:
            panel = strip_plotly_titles(shadow.fig)
            panel.update_layout(width=950, height=560, margin=dict(l=70, r=40, t=30, b=70))
            display_path = self.next_output_path(self.current_script, f"{declared}_panel_{shadow.label}", "plotly_source_panel")
            with self.suspend_plotly_mirror():
                self.original_plotly_write_image(panel, str(display_path))
            review_id = self.next_review_id()
            title = f"{title_base} — Panel {shadow.label}: {shadow.title}"
            record_type = "individual panel rendered by mirroring source Plotly subplot calls"
            panel_code_path = write_panel_code_manifest(
                source_script=self.current_script,
                review_id=review_id,
                title=title,
                renderer="plotly",
                record_type=record_type,
                call_sites=shadow.call_sites,
            )
            records.append(
                RenderRecord(
                    review_id=review_id,
                    title=title,
                    source_script=self.current_script,
                    declared_output=declared,
                    display_path=display_path,
                    renderer="plotly",
                    record_type=record_type,
                    data_contract=f"Panel {shadow.label} was rendered from the source add_trace/update_axis calls for subplot row {shadow.row}, col {shadow.col}.",
                    render_contract="During source-script execution, each subplot call was mirrored onto a clean standalone Plotly Figure; subplot title text is captured for Markdown and removed from the image.",
                    trace_or_axes_count=shadow.trace_count,
                    parent_review_id=parent_id,
                    panel_code_path=panel_code_path,
                )
            )
        return records

    def create_mpl_shadow_for_axis(self, ax: Any) -> None:
        import matplotlib.pyplot as plt

        if self._mpl_mirror_depth or getattr(ax.figure, "_codex_shadow_figure", False):
            return
        figure_key = id(ax.figure)
        shadows = self.mpl_figure_shadows.setdefault(figure_key, [])
        label = panel_label_from_index(len(shadows) + 1)
        with self.suspend_mpl_mirror():
            panel_fig, panel_ax = self.original_plt_subplots(figsize=(8.8, 5.4))
        panel_fig._codex_shadow_figure = True
        panel_ax._codex_shadow_axis = True
        shadow = MplPanelShadow(
            figure_key=figure_key,
            label=label,
            title=f"Panel {label}",
            fig=panel_fig,
            ax=panel_ax,
            call_sites=[],
        )
        self.mpl_axis_shadows[id(ax)] = shadow
        shadows.append(shadow)

    def mpl_add_subplot(self, fig: Any, *args: Any, **kwargs: Any) -> Any:
        ax = self.original_mpl_add_subplot(fig, *args, **kwargs)
        if self.current_script is not None:
            self.create_mpl_shadow_for_axis(ax)
        return ax

    def plt_subplots(self, *args: Any, **kwargs: Any) -> Any:
        fig, axes = self.original_plt_subplots(*args, **kwargs)
        if self.current_script is not None:
            for ax in flatten_axes(axes):
                self.create_mpl_shadow_for_axis(ax)
        return fig, axes

    def mpl_axis_call(self, method_name: str, ax: Any, *args: Any, **kwargs: Any) -> Any:
        original = self.original_mpl_axis_methods[method_name]
        result = original(ax, *args, **kwargs)
        if self._mpl_mirror_depth or getattr(ax, "_codex_shadow_axis", False):
            return result

        shadow = self.mpl_axis_shadows.get(id(ax))
        if shadow is None:
            return result

        callsite = format_callsite(self.current_script)
        if method_name == "set_title":
            title = args[0] if args else kwargs.get("label", "")
            cleaned = clean_panel_title(str(title))
            if cleaned:
                shadow.title = cleaned
            shadow.call_sites.append(callsite)
            return result

        if method_name == "text" and is_title_like_mpl_text(ax, args, kwargs):
            title_text = clean_panel_title(str(args[2]))
            if title_text and not re.fullmatch(r"[A-I]", title_text):
                shadow.title = title_text
            shadow.call_sites.append(callsite)
            return result

        shadow_kwargs = map_mpl_shadow_kwargs(dict(kwargs), ax, shadow.ax)
        with self.suspend_mpl_mirror():
            try:
                if method_name == "legend" and (args or kwargs):
                    shadow_result = getattr(shadow.ax, method_name)()
                else:
                    shadow_result = getattr(shadow.ax, method_name)(*args, **shadow_kwargs)
                self.map_mpl_result(result, shadow_result)
                if method_name in {"imshow", "scatter"}:
                    self.mpl_mappable_shadows[id(result)] = shadow_result
                shadow.call_count += 1
                shadow.call_sites.append(callsite)
            except Exception as exc:
                shadow.call_sites.append(f"{callsite}  # mirror warning: {exc.__class__.__name__}: {exc}")
        return result

    def map_mpl_result(self, original: Any, shadow: Any) -> None:
        if original is None or shadow is None:
            return
        if isinstance(original, dict) and isinstance(shadow, dict):
            for key, original_value in original.items():
                if key in shadow:
                    self.map_mpl_result(original_value, shadow[key])
            return
        if isinstance(original, (list, tuple)) and isinstance(shadow, (list, tuple)):
            for original_item, shadow_item in zip(original, shadow):
                self.map_mpl_result(original_item, shadow_item)
            return
        if hasattr(original, "patches") and hasattr(shadow, "patches"):
            for original_item, shadow_item in zip(original.patches, shadow.patches):
                self.map_mpl_result(original_item, shadow_item)
        if hasattr(original, "lines") and hasattr(shadow, "lines"):
            for original_item, shadow_item in zip(original.lines, shadow.lines):
                self.map_mpl_result(original_item, shadow_item)
        if hasattr(original, "set_figure") and hasattr(shadow, "set_figure"):
            self.mpl_artist_shadows[id(original)] = shadow

    def mpl_artist_call(self, cls: Any, method_name: str, artist: Any, *args: Any, **kwargs: Any) -> Any:
        original = self.original_mpl_artist_methods[(cls, method_name)]
        result = original(artist, *args, **kwargs)
        if self._mpl_mirror_depth:
            return result
        shadow = self.mpl_artist_shadows.get(id(artist))
        if shadow is None:
            return result
        with self.suspend_mpl_mirror():
            try:
                getattr(shadow, method_name)(*args, **kwargs)
            except Exception:
                pass
        return result

    def mpl_colorbar(self, fig: Any, mappable: Any, *args: Any, **kwargs: Any) -> Any:
        with self.suspend_mpl_mirror():
            result = self.original_mpl_colorbar(fig, mappable, *args, **kwargs)
        if self._mpl_mirror_depth or id(mappable) not in self.mpl_mappable_shadows:
            return result
        shadow_mappable = self.mpl_mappable_shadows[id(mappable)]
        source_ax = kwargs.get("ax")
        shadow = self.mpl_axis_shadows.get(id(source_ax)) if source_ax is not None else None
        shadow_fig = shadow.fig if shadow is not None else shadow_mappable.axes.figure
        shadow_kwargs = dict(kwargs)
        if shadow is not None:
            shadow_kwargs["ax"] = shadow.ax
        with self.suspend_mpl_mirror():
            try:
                self.original_mpl_colorbar(shadow_fig, shadow_mappable, *args, **shadow_kwargs)
                if shadow is not None:
                    shadow.call_sites.append(format_callsite(self.current_script))
            except Exception:
                pass
        return result

    def render_mpl_panel_shadows(self, fig: Any, declared: str, parent_id: str, title_base: str) -> list[RenderRecord]:
        assert self.current_script is not None
        shadows = [
            shadow
            for shadow in self.mpl_figure_shadows.get(id(fig), [])
            if shadow.call_count and (shadow.ax.has_data() or shadow.ax.get_xlabel() or shadow.ax.get_ylabel())
        ]
        if len(shadows) <= 1:
            return []
        records: list[RenderRecord] = []
        for shadow in shadows:
            strip_mpl_titles(shadow.fig)
            shadow.fig.tight_layout()
            display_path = self.next_output_path(self.current_script, f"{declared}_panel_{shadow.label}", "matplotlib_source_panel")
            with self.suspend_mpl_mirror():
                self.original_mpl_savefig(shadow.fig, str(display_path), dpi=180, bbox_inches="tight", facecolor="white")
            review_id = self.next_review_id()
            title = f"{title_base} — Panel {shadow.label}: {shadow.title}"
            record_type = "individual panel rendered by mirroring source Matplotlib axis calls"
            panel_code_path = write_panel_code_manifest(
                source_script=self.current_script,
                review_id=review_id,
                title=title,
                renderer="matplotlib",
                record_type=record_type,
                call_sites=shadow.call_sites,
            )
            records.append(
                RenderRecord(
                    review_id=review_id,
                    title=title,
                    source_script=self.current_script,
                    declared_output=declared,
                    display_path=display_path,
                    renderer="matplotlib",
                    record_type=record_type,
                    data_contract=f"Panel {shadow.label} was rendered while the source script executed the plotting calls for that specific Axes.",
                    render_contract="The panel received the source Matplotlib/Seaborn plotting calls on a clean standalone Figure; panel title text is captured for Markdown and not embedded.",
                    trace_or_axes_count=1,
                    parent_review_id=parent_id,
                    panel_code_path=panel_code_path,
                )
            )
        return records

    def plotly_write_image(self, fig: Any, file: Any, *args: Any, **kwargs: Any) -> None:
        assert self.current_script is not None
        declared = str(file)
        title_base = infer_title_from_output(declared, self.current_script.stem)
        review_id = self.next_review_id()
        panel_records = self.render_plotly_panel_shadows(fig, declared, review_id, title_base)
        self.records.extend(panel_records)
        display_path = self.next_output_path(self.current_script, declared, "plotly")
        clean = strip_plotly_titles(fig)
        with self.suspend_plotly_mirror():
            self.original_plotly_write_image(clean, str(display_path), *args, **kwargs)
        self.mirror_declared_output(display_path, declared)
        self.records.append(
            RenderRecord(
                review_id=review_id,
                title=title_base,
                source_script=self.current_script,
                declared_output=declared,
                display_path=display_path,
                renderer="plotly",
                record_type="full graph rendered from source Plotly code",
                data_contract=f"Executed `{source_label(self.current_script)}`; Plotly Figure contains {len(fig.data)} trace(s).",
                render_contract="Intercepted Figure.write_image, removed layout title/title-like subplot annotations, then exported the code-generated figure.",
                trace_or_axes_count=len(fig.data),
            )
        )

    def mpl_savefig(self, fig: Any, fname: Any, *args: Any, **kwargs: Any) -> None:
        assert self.current_script is not None
        declared = str(fname)
        title_base = infer_title_from_output(declared, self.current_script.stem)
        display_axes = [
            ax
            for ax in fig.axes
            if ax.has_data() and (ax.get_xlabel() or ax.get_ylabel() or ax.get_title() or len(ax.lines) or len(ax.patches) or len(ax.collections) or len(ax.images))
        ]

        review_id = self.next_review_id()
        panel_records = self.render_mpl_panel_shadows(fig, declared, review_id, title_base)
        self.records.extend(panel_records)
        display_path = self.next_output_path(self.current_script, declared, "matplotlib")
        strip_mpl_titles(fig)
        kwargs = dict(kwargs)
        kwargs.setdefault("bbox_inches", "tight")
        kwargs.setdefault("facecolor", "white")
        with self.suspend_mpl_mirror():
            self.original_mpl_savefig(fig, str(display_path), *args, **kwargs)
        self.mirror_declared_output(display_path, declared)
        self.records.append(
            RenderRecord(
                review_id=review_id,
                title=f"{title_base} — grouped/full figure" if len(display_axes) > 1 else title_base,
                source_script=self.current_script,
                declared_output=declared,
                display_path=display_path,
                renderer="matplotlib",
                record_type="full graph rendered from source Matplotlib code",
                data_contract=f"Executed `{source_label(self.current_script)}`; Matplotlib Figure contains {len(display_axes)} data-bearing axes.",
                render_contract="Intercepted Figure.savefig, removed suptitle/axes titles, then exported the code-generated figure.",
                trace_or_axes_count=len(display_axes),
            )
        )

    @contextlib.contextmanager
    def patched_renderers(self):
        import matplotlib.axes
        import matplotlib.collections
        import matplotlib.figure
        import matplotlib.lines
        import matplotlib.patches
        import matplotlib.pyplot as plt
        import matplotlib.text
        import plotly.basedatatypes
        import plotly.graph_objects as go
        import plotly.subplots

        self.original_plotly_write_image = plotly.basedatatypes.BaseFigure.write_image
        self.original_plotly_add_trace = plotly.basedatatypes.BaseFigure.add_trace
        self.original_plotly_update_xaxes = go.Figure.update_xaxes
        self.original_plotly_update_yaxes = go.Figure.update_yaxes
        self.original_plotly_update_layout = plotly.basedatatypes.BaseFigure.update_layout
        self.original_plotly_make_subplots = plotly.subplots.make_subplots
        self.original_mpl_savefig = matplotlib.figure.Figure.savefig
        self.original_mpl_add_subplot = matplotlib.figure.Figure.add_subplot
        self.original_plt_subplots = plt.subplots
        self.original_mpl_colorbar = matplotlib.figure.Figure.colorbar
        mpl_axis_methods = [
            "plot", "semilogy", "scatter", "bar", "barh", "boxplot", "imshow",
            "violinplot", "hlines", "vlines", "axhline", "axvline",
            "fill_between", "fill_betweenx", "text", "annotate",
            "set_title", "set_xlabel", "set_ylabel", "set_xlim", "set_ylim",
            "set_xscale", "set_yscale", "set_xticks", "set_yticks",
            "set_xticklabels", "set_yticklabels", "set_facecolor", "legend",
            "grid",
        ]
        self.original_mpl_axis_methods = {
            name: getattr(matplotlib.axes.Axes, name)
            for name in mpl_axis_methods
            if hasattr(matplotlib.axes.Axes, name)
        }
        artist_methods = [
            (matplotlib.patches.Patch, ["set_facecolor", "set_edgecolor", "set_alpha", "set_linewidth", "set_linestyle", "set_color"]),
            (matplotlib.lines.Line2D, ["set_color", "set_alpha", "set_linewidth", "set_linestyle", "set_marker", "set_markersize"]),
            (matplotlib.collections.Collection, ["set_facecolor", "set_edgecolor", "set_alpha", "set_linewidth", "set_linestyle", "set_color"]),
            (matplotlib.text.Text, ["set_color", "set_alpha", "set_fontsize", "set_fontweight", "set_weight", "set_rotation"]),
        ]
        self.original_mpl_artist_methods = {}
        for cls, names in artist_methods:
            for name in names:
                if hasattr(cls, name):
                    self.original_mpl_artist_methods[(cls, name)] = getattr(cls, name)

        def _plotly_write(fig, file, *args, **kwargs):
            return self.plotly_write_image(fig, file, *args, **kwargs)

        def _plotly_add_trace(fig, trace, *args, **kwargs):
            return self.plotly_add_trace(fig, trace, *args, **kwargs)

        def _plotly_update_xaxes(fig, *args, **kwargs):
            return self.plotly_update_axis("x", fig, *args, **kwargs)

        def _plotly_update_yaxes(fig, *args, **kwargs):
            return self.plotly_update_axis("y", fig, *args, **kwargs)

        def _plotly_update_layout(fig, *args, **kwargs):
            return self.plotly_update_layout(fig, *args, **kwargs)

        def _make_subplots(*args, **kwargs):
            return self.plotly_make_subplots(*args, **kwargs)

        def _mpl_save(fig, fname, *args, **kwargs):
            return self.mpl_savefig(fig, fname, *args, **kwargs)

        def _mpl_add_subplot(fig, *args, **kwargs):
            return self.mpl_add_subplot(fig, *args, **kwargs)

        def _plt_subplots(*args, **kwargs):
            return self.plt_subplots(*args, **kwargs)

        def _mpl_colorbar(fig, mappable, *args, **kwargs):
            return self.mpl_colorbar(fig, mappable, *args, **kwargs)

        def _make_artist_wrapper(cls: Any, method_name: str):
            def _artist_wrapper(artist, *args, **kwargs):
                return self.mpl_artist_call(cls, method_name, artist, *args, **kwargs)
            return _artist_wrapper

        plotly.basedatatypes.BaseFigure.write_image = _plotly_write
        plotly.basedatatypes.BaseFigure.add_trace = _plotly_add_trace
        go.Figure.update_xaxes = _plotly_update_xaxes
        go.Figure.update_yaxes = _plotly_update_yaxes
        plotly.basedatatypes.BaseFigure.update_layout = _plotly_update_layout
        plotly.subplots.make_subplots = _make_subplots
        matplotlib.figure.Figure.savefig = _mpl_save
        matplotlib.figure.Figure.add_subplot = _mpl_add_subplot
        matplotlib.figure.Figure.colorbar = _mpl_colorbar
        plt.subplots = _plt_subplots
        for name in self.original_mpl_axis_methods:
            def _make_axis_wrapper(method_name: str):
                def _axis_wrapper(ax, *args, **kwargs):
                    return self.mpl_axis_call(method_name, ax, *args, **kwargs)
                return _axis_wrapper

            setattr(matplotlib.axes.Axes, name, _make_axis_wrapper(name))
        for (cls, name) in self.original_mpl_artist_methods:
            setattr(cls, name, _make_artist_wrapper(cls, name))
        try:
            yield
        finally:
            plotly.basedatatypes.BaseFigure.write_image = self.original_plotly_write_image
            plotly.basedatatypes.BaseFigure.add_trace = self.original_plotly_add_trace
            go.Figure.update_xaxes = self.original_plotly_update_xaxes
            go.Figure.update_yaxes = self.original_plotly_update_yaxes
            plotly.basedatatypes.BaseFigure.update_layout = self.original_plotly_update_layout
            plotly.subplots.make_subplots = self.original_plotly_make_subplots
            matplotlib.figure.Figure.savefig = self.original_mpl_savefig
            matplotlib.figure.Figure.add_subplot = self.original_mpl_add_subplot
            matplotlib.figure.Figure.colorbar = self.original_mpl_colorbar
            plt.subplots = self.original_plt_subplots
            for name, original in self.original_mpl_axis_methods.items():
                setattr(matplotlib.axes.Axes, name, original)
            for (cls, name), original in self.original_mpl_artist_methods.items():
                setattr(cls, name, original)
            plt.close("all")


def run_script(script: Path, collector: CodeRenderCollector) -> ScriptRunResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    before = len(collector.records)
    error: str | None = None

    with tempfile.TemporaryDirectory(prefix="icnp_code_render_") as temp_dir:
        old_cwd = Path.cwd()
        collector.current_script = script
        collector.reset_script_render_state()
        try:
            os.chdir(temp_dir)
            Path("output/icnp_graphs").mkdir(parents=True, exist_ok=True)
            Path("icnp_graphs").mkdir(parents=True, exist_ok=True)
            with collector.patched_renderers():
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    runpy.run_path(str(script), run_name="__main__")
        except Exception:
            error = traceback.format_exc(limit=8)
        finally:
            collector.current_script = None
            os.chdir(old_cwd)

    return ScriptRunResult(
        source_script=script,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
        error=error,
        records=collector.records[before:],
    )


def build_code_rendered_records(force: bool = True) -> tuple[list[RenderRecord], pd.DataFrame]:
    if force and RENDER_DIR.exists():
        shutil.rmtree(RENDER_DIR)
    if force and PANEL_CODE_DIR.exists():
        shutil.rmtree(PANEL_CODE_DIR)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    PANEL_CODE_DIR.mkdir(parents=True, exist_ok=True)

    collector = CodeRenderCollector(RENDER_DIR)
    run_rows: list[dict[str, Any]] = []

    for script in discover_graph_scripts():
        result = run_script(script, collector)
        if result.error:
            status = "failed"
        elif result.records:
            status = "rendered"
        else:
            status = "no rendered exports"
        run_rows.append(
            {
                "source_script": source_label(script),
                "declared_outputs": ", ".join(declared_outputs(script)),
                "rendered_records": len(result.records),
                "status": status,
                "error": result.error or "",
                "stdout_tail": "\n".join(result.stdout.strip().splitlines()[-4:]),
            }
        )

    return collector.records, pd.DataFrame(run_rows)


def validation_markdown(record: RenderRecord) -> Markdown:
    parent = record.parent_review_id or "not grouped"
    panel_code = f"`{source_label(record.panel_code_path)}`" if record.panel_code_path else "not applicable"
    return Markdown(
        f"### {record.review_id} — {record.title}\n"
        f"| Field | Validation record |\n"
        f"|---|---|\n"
        f"| Source script | `{source_label(record.source_script)}` |\n"
        f"| Panel-specific code manifest | {panel_code} |\n"
        f"| Declared output in code | `{record.declared_output}` |\n"
        f"| Display artifact | `{source_label(record.display_path)}` |\n"
        f"| Renderer | {record.renderer} |\n"
        f"| Record type | {record.record_type} |\n"
        f"| Parent record | {parent} |\n"
        f"| Input dataset / source | {record.data_contract} |\n"
        f"| How values are generated | The source script was executed; the plotted values are the arrays/dataframes/traces produced by that script during execution. |\n"
        f"| Output represents | Team-facing validation render for checking data-story, visual encoding, axis/legend choices, and paper-claim alignment. |\n"
        f"| Manuscript claim supported | To be confirmed by reviewers against the corresponding RQ/table/figure claim. |\n"
        f"| Interpretation | Review whether the code-generated visual signal supports the intended result narrative without relying on a static exported picture. |\n"
        f"| Evidence status | {record.status}; {record.trace_or_axes_count if record.trace_or_axes_count is not None else 'unknown'} trace/axis unit(s). |\n"
        f"| Title handling | Plot titles were removed before rendering. The title above is Markdown and is not part of the image. |\n"
        f"| Render contract | {record.render_contract} |"
    )


def render_icnp_graph_validation_hub(image_width: int = 760, force: bool = True) -> pd.DataFrame:
    records, run_ledger = build_code_rendered_records(force=force)
    if not records:
        raise RuntimeError("No code-rendered graph records were created. Check the script run ledger.")

    ledger = pd.DataFrame(
        [
            {
                "review_id": record.review_id,
                "title": record.title,
                "renderer": record.renderer,
                "record_type": record.record_type,
                "source_script": source_label(record.source_script),
                "declared_output": record.declared_output,
                "display_artifact": source_label(record.display_path),
                "panel_code_manifest": source_label(record.panel_code_path),
                "parent_review_id": record.parent_review_id or "",
            }
            for record in records
        ]
    )

    display(
        Markdown(
            "## ICNP Full Graph Validation Review Queue\n\n"
            "This section is code-rendered. It discovers Python graph scripts in the requested ICNP directories, executes them, intercepts each Plotly/Matplotlib export, removes titles before rendering, and displays regenerated artifacts for team review. Multi-panel figures are split by mirroring each panel's own source plotting calls onto standalone figures, then showing the grouped figure for context. No source image cropping is used."
        )
    )
    display(
        Markdown(
            f"**Graph-producing scripts discovered:** {len(run_ledger)}. "
            f"**Code-rendered review records:** {len(records)}. "
            f"**Rendered assets:** `{RENDER_DIR}`. "
            f"**Panel code manifests:** `{PANEL_CODE_DIR}`."
        )
    )
    display(Markdown("### Script Run Ledger"))
    display(run_ledger)
    display(Markdown("### Rendered Graph Review Ledger"))
    display(ledger)

    for record in records:
        display(validation_markdown(record))
        display(Image(filename=str(record.display_path), width=image_width))

    return ledger
