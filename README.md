# MRPC Shotmarker Data Explorer

Interactive Streamlit app to parse, visualize and analyze ShotMarker (MRPC) target shooting data.

This repository contains a small Streamlit-based tool to:

- Parse ShotMarker CSV/XLSX exports that contain multiple shooting strings.
- Plot shot impacts on configurable target templates.
- Display shot-by-shot scores, session metadata, and allow downloading target plots.

## Files

- `streamlit_app.py` — Streamlit front-end. Upload one or more ShotMarker files (`.csv` or `.xlsx`) to view each shooting string, a plotted target, and a tabular score summary. Allows downloading the target plot as PNG and toggling raw shot data.
- `shotmarker_parser.py` — Parser that extracts multiple shooting strings from an uploaded file and converts each string into a dict containing metadata and a `pandas.DataFrame` of shot rows. Shot rows include fields such as `time`, `tags`, `id`, `score`, `temp_c`, `x_mm`, `y_mm`, `v_fps`, `yaw_deg`, `pitch_deg`, `quality`, and `xy_err`.
- `plot_target.py` — Plotting helper that draws targets and shot markers using `matplotlib`. It loads `target_specs.json` (sample target templates) and will draw rings, sighters, shot IDs, and optional grid lines.
- `target_specs.json` — Example target specifications (ring diameters, colors, scoring) used by `plot_target.py`. Edit or extend this file to add custom target templates.
- `plot_target.py` returns `(fig, ax)`; `streamlit_app.py` uses the figure to display and provide a downloadable PNG.
- `requirements.txt` — Python dependencies for the project.
- `LICENSE` — Project license (present in the repository root).

## Quick Start

1. Create and activate a Python environment (recommended).

   Powershell (Windows):

   ```powershell
   python -m venv .venv; .\\.venv\\Scripts\\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:

   ```powershell
   streamlit run streamlit_app.py
   ```

4. In the browser UI upload one or more ShotMarker CSV/XLSX files exported from your MRPC ShotMarker device. The app will show each shooting string (metadata + plotted target + score table).

## Usage notes

- The parser `parse_shotmarker_csv` accepts a file-like object (Streamlit's `UploadedFile`) or raw bytes/str and returns a list of strings. Each string is a dict with keys like `date`, `shooter`, `rifle`, `course`, `score`, and `data` (a `pandas.DataFrame`).
- The plotting helper `plot_target_with_scores` expects the dict returned by the parser and reads the `data` DataFrame. It looks for the `target_info` column (populated by the parser in the sample code) to choose a matching target template from `target_specs.json`.
- Shot markers use `x_mm` and `y_mm` coordinates (millimetres) read from the ShotMarker export.
- Sighter shots are detected via the `tags` column and plotted differently.

## Customizing targets

Edit or extend `target_specs.json` to add new target templates. Each template contains:

- `type`: human-friendly name used to match `target_info` values in shot data.
- `rings`: array of rings with `ring` label, `diameter` (mm), `color` (hex), and `points`.
- `grid_size_moa_quarter`: optional numeric used to set grid spacing.

## Developer notes

- If your ShotMarker export has a different format, update `shotmarker_parser.py` to match column indices or separators. The parser currently looks for lines resembling ShotMarker export headers and then parses shot lines with coordinate fields at indices used in the repository's sample files.
- `plot_target.py` automatically sizes the displayed target based on the farthest shot and will draw rings from `target_specs.json` when a matching `target_info` is present. It returns `(fig, ax)` so callers can save or further modify the figure.

## Troubleshooting

- If uploaded files are not parsed correctly, ensure they are encoded in UTF-8 or try opening and re-saving them in a text editor or Excel. The parser tolerates some malformed lines but expects shot coordinate columns.
- If the target rings don't show, verify the `target_info` column in the parsed shot DataFrame contains one of the `type` values from `target_specs.json`.
- If plots look empty, confirm that `x_mm` / `y_mm` values are present and numeric.

## Extending the project

- Add more target templates to `target_specs.json`.
- Add export options (PDF pages with many plots) — `matplotlib.backends.backend_pdf.PdfPages` is already imported in `streamlit_app.py` and can be used for multi-page exports.
- Add unit tests for `shotmarker_parser.parse_shotmarker_csv` and plotting helpers.

## License

See the `LICENSE` file in the repository root for licensing details.

## Contact

For questions or improvements, open an issue or pull request in the repository.

---

Generated README based on project files included in the repository.
