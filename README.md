<p align="center">
  <img src="assets/logo.svg" alt="doc2latex" width="420">
</p>

<h1 align="center">doc2latex</h1>

<p align="center">
  Fully offline CLI that converts <b>PDF / DOCX / JPEG / PNG</b> documents into
  compilable <b>LaTeX</b>, preserving text, equations, figures, and tables.
</p>

No API calls, no cloud costs, no telemetry. After first-time model weight
downloads (`pix2tex`, Nougat, Marker), everything runs locally.

## Install

```bash
pip install -e .
```

Everything is included by default — OCR (`pytesseract`, `pix2tex`), table
extraction (`pdfplumber`, `camelot-py`), and the academic-PDF backends
(`nougat-ocr`, `marker-pdf`). The first run of `pix2tex` / Nougat / Marker
will download model weights once; after that the tool is fully offline.

> **Python version note:** the heavy ML deps (`pix2tex`, `nougat-ocr`,
> `marker-pdf`, `opencv-python`, `camelot-py[cv]`) pin older transitive
> packages that don't yet ship Python 3.14 wheels. They install automatically
> on **Python 3.10–3.13** and are silently skipped on 3.14. The basic PDF /
> DOCX / pdfplumber-table path runs on 3.14; use a 3.10–3.13 environment for
> equation OCR and the Nougat/Marker backends.

### System dependencies

| Tool | Purpose | macOS | Ubuntu | Windows |
|---|---|---|---|---|
| `tesseract` | OCR for scans / images | `brew install tesseract` | `apt install tesseract-ocr` | [tesseract-ocr.github.io](https://tesseract-ocr.github.io/tessdoc/Installation.html) |
| `ghostscript` | Camelot table extraction | `brew install ghostscript` | `apt install ghostscript` | [ghostscript.com/releases](https://www.ghostscript.com/releases/gsdnld.html) |
| `pdflatex` | Compile the output (for testing) | `brew install --cask mactex` | `apt install texlive-latex-base` | [MiKTeX](https://miktex.org/download) |

## Usage

```bash
doc2latex convert paper.pdf
doc2latex convert paper.pdf --backend nougat --out paper.tex
doc2latex convert report.docx
doc2latex convert scan.jpg --ocr-lang eng+deu
doc2latex convert equation.png --whole-equation
```

### CLI reference

```
doc2latex convert <input> [--out out.tex] [--assets-dir assets]
                          [--backend {basic,nougat,marker}]
                          [--ocr-lang eng] [--dpi 300]
                          [--no-equations] [--no-tables]
                          [--whole-equation] [--verbose]
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Success |
| `2` | Bad input (file not found / unsupported type) |
| `3` | Missing system dependency |
| `4` | Conversion failure |

## Backends

- **basic** *(default)* — Per-block pipeline. PyMuPDF for PDFs, python-docx for
  Word, Tesseract + pix2tex for images. Fast, predictable, good enough for
  most documents.
- **nougat** — Shells out to [Nougat](https://github.com/facebookresearch/nougat).
  Downloads ~1.4 GB of weights on first run. Best for academic PDFs with
  multi-column layouts and dense equations.
- **marker** — Shells out to [marker-pdf](https://github.com/VikParuchuri/marker).
  Faster than Nougat, slightly different layout heuristics.

Both backends run **locally** after first weight download.

## How it works

```
input file → router → reader → [text, equation imgs, figure imgs, tables]
          → converters (per-block) → assembler → output.tex + assets/
```

Each reader emits a stream of normalized `Block` objects (`heading`, `para`,
`equation`, `figure`, `table`, `list`). The assembler renders them through a
Jinja LaTeX template.

Long documents are processed page-by-page (streamed) so memory stays bounded
regardless of page count.

## Troubleshooting

- **`tesseract binary not found on PATH`** — Install Tesseract (see table
  above) or pass `--no-equations` if you don't need OCR.
- **`ghostscript not found`** — Required by Camelot. Install it, or pass
  `--no-tables` to disable table extraction.
- **`pix2tex` first run is slow** — It downloads model weights (~250 MB) to
  `~/.cache/pix2tex`. After that it's offline and fast.
- **`pdflatex` errors on output** — Check that `assets/` is next to the
  `.tex` file; relative paths matter.

## Known limitations

- Handwritten math is not supported.
- Complex two-column journal layouts work much better with `--backend nougat`.
- Merged-cell tables become rectangular grids (cell content is preserved but
  spans are flattened).
- DOCX inline equations are extracted as raw text where possible; for
  reliable rendering, ship embedded equation images and the basic path picks
  them up via pix2tex.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Tests that require `tesseract` or `ghostscript` are skipped automatically when
the binaries aren't available.

## Desktop & mobile installers

The repo ships a Tauri v2 desktop GUI and a Chaquopy-based Android app. GitHub
Actions builds the installers on every push to `main`.

### What gets built

| Platform | Artefact | How |
|---|---|---|
| Windows | `.msi` + `.exe` (NSIS) | Tauri + PyInstaller sidecar |
| macOS (arm64 + x86_64) | `.dmg` | Tauri + PyInstaller sidecar |
| Linux (Ubuntu 22.04) | `.deb` + `.AppImage` | Tauri + PyInstaller sidecar |
| Android | `.apk` (basic engine only) | Gradle + Chaquopy |

The desktop installers bundle a frozen `doc2latex` binary via PyInstaller
(`packaging/doc2latex.spec` + `packaging/build_sidecar.py`) and ship it as a
Tauri sidecar — users never need Python installed.

The Android APK uses **Chaquopy** to embed CPython 3.11 plus the pure-Python
deps that have ARM wheels (`python-docx`, `pymupdf`, `pdfplumber`, `Pillow`).
The mobile build does **not** include `pix2tex`, `opencv`, `nougat-ocr`,
`marker-pdf`, or `camelot` — those don't fit or don't build for Android.
DOCX → LaTeX and text-only PDF → LaTeX work; equation OCR and the Nougat/
Marker backends are desktop-only.

### Local builds

```bash
# Sidecar binary (places it under src-tauri/binaries/)
python packaging/build_sidecar.py

# Run the GUI in dev mode
bun install
bun run tauri dev

# Bundle installers for the host platform
bun run tauri build
```

```bash
# Android (requires Android SDK + JDK 17)
cd android-app
./gradlew :app:assembleRelease
# APK at app/build/outputs/apk/release/
```

### Releasing

`.github/workflows/release.yml` follows the auto-bump pattern from
`TAURI_CICD_PIPELINE_GUIDE.md`:

1. Push to `main`.
2. CI bumps the patch in `tauri.conf.json`, `package.json`,
   `src-tauri/Cargo.toml`, `pyproject.toml`, and
   `android-app/app/build.gradle.kts` (all in one `[skip ci]` commit).
3. Matrix builds Tauri installers on Windows / macOS arm64 / macOS x86_64 /
   Ubuntu 22.04.
4. A parallel job builds the Android APK via Gradle.
5. `tauri-action` and `softprops/action-gh-release` upload everything to the
   same GitHub Release tagged `vX.Y.Z`.

No secrets needed — `GITHUB_TOKEN` is provided automatically. For signed
Android releases, generate a keystore, store the password as a secret, and
replace the "Sign APK" step.

## License

MIT
