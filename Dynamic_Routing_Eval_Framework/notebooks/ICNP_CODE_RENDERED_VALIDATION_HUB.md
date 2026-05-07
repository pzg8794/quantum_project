# ICNP Code-Rendered Validation Hub

This validation section is intentionally code-first. It does not crop, slice, or reuse exported figure images as the source of validation.

## Rendering Contract

- The notebook discovers graph-producing Python scripts under the requested `QuantumFaultTolerant` figure/tool directories.
- Each script is executed in an isolated temporary working directory.
- Plotly `write_image` and Matplotlib `savefig` calls are intercepted so the validation artifacts are generated during source execution.
- Plot titles, subplot titles, and subtitle-like panel headings are removed from the rendered image. The same text is captured for the Markdown validation heading so reviewers can control image size independently of titles.
- Multi-panel figures are handled by mirroring each panel's own source plotting calls into a clean standalone figure while the source script runs.
- The grouped/full figure is still rendered after the individual panels so reviewers can validate panel context.

## What Counts as a Panel Render

An individual panel render must come from the source script's plotting calls for that panel. The helper mirrors calls such as Plotly `add_trace(..., row=..., col=...)` and Matplotlib axis calls such as `ax.plot`, `ax.scatter`, `ax.imshow`, `ax.boxplot`, `ax.text`, and later artist styling calls.

The helper does not create individual panels by cropping an exported image.

## Validation Artifacts

- Rendered review images are regenerated in `notebooks/generated/icnp_validation_code_rendered/`.
- Panel-specific source-call manifests are regenerated in `notebooks/generated/icnp_validation_panel_code/`.
- The notebook displays a script run ledger so scripts that fail, or scripts that run without exporting a graph, stay visible to reviewers.

## Rerun

From the validation notebook, run the ICNP validation cell:

```python
icnp_full_graph_review_ledger = icnp_review.render_icnp_graph_validation_hub(image_width=760)
```

This regenerates the code-rendered review queue and panel manifests.
