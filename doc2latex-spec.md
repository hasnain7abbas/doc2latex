# doc2latex — Offline PDF / DOCX / JPEG → LaTeX Converter

A fully offline CLI that converts PDFs, Word documents, and JPEG images into compilable LaTeX, preserving text, equations, figures, and tables. No API calls, no cloud costs.

This document is the spec. Hand it to Claude Code and have it build the project end-to-end.

---

## 1. Goals & Non-Goals

**Goals**
- Pure offline operation. No network calls at runtime.
- Inputs: `.pdf`, `.docx`, `.jpg` / `.jpeg` / `.png`.
- Output: a single `.tex` file plus an `assets/` folder of extracted figures.
- Handle arbitrarily long documents via page-by-page streaming.
- Preserve: paragraphs, headings, lists, inline + display equations, figures with captions, tables.
- Produce LaTeX that compiles with `pdflatex` out of the box.

**Non-Goals**
- Perfect reproduction of complex multi-column academic layouts (use Nougat path for that).
- Handwriting recognition.
- Real-time conversion.

---

## 2. Architecture

```
doc2latex/
├── pyproject.toml
├── README.md
├── doc2latex/
│   ├── __init__.py
│   ├── cli.py                 # Typer-based CLI entry point
│   ├── pipeline.py            # Orchestrates the full conversion
│   ├── routers.py             # Dispatch by file type
│   ├── readers/
│   │   ├── pdf_reader.py      # PyMuPDF + optional Nougat/Marker backend
│   │   ├── docx_reader.py     # python-docx
│   │   └── image_reader.py    # Tesseract + pix2tex
│   ├── detectors/
│   │   ├── equation.py        # Detect equation regions in page images
│   │   ├── table.py           # Camelot / pdfplumber wrapper
│   │   └── figure.py          # Bounding-box extraction
│   ├── converters/
│   │   ├── text_to_latex.py   # Escape + structural mapping
│   │   ├── eq_to_latex.py     # pix2tex wrapper
│   │   └── table_to_latex.py  # tabular generation
│   ├── assembler.py           # Stitches blocks into a .tex document
│   └── templates/
│       └── base.tex.jinja     # Preamble + document skeleton
└── tests/
    ├── fixtures/              # Sample inputs
    └── test_*.py
```

**Data flow**

```
input file → router → reader → [text, equation imgs, figure imgs, tables]
          → converters (per-block) → assembler → output.tex + assets/
```

Each reader returns a normalized list of `Block` objects:

```python
@dataclass
class Block:
    kind: Literal["heading", "para", "equation", "figure", "table", "list"]
    content: str            # text, LaTeX code, or asset path
    level: int = 0          # heading level
    caption: str | None = None
    bbox: tuple | None = None
    page: int | None = None
```

The assembler iterates blocks in document order and emits LaTeX.

---

## 3. Dependencies

All free, all offline-capable.

| Purpose | Library | Notes |
|---|---|---|
| PDF parsing | `pymupdf` (fitz) | Text, images, bounding boxes |
| PDF tables | `pdfplumber`, `camelot-py[cv]` | Camelot needs Ghostscript |
| Word parsing | `python-docx` | Native paragraph + image extraction |
| OCR | `pytesseract` | Requires Tesseract binary installed |
| Equation OCR | `pix2tex` | First run downloads weights to disk; afterward offline |
| Layout (optional, recommended) | `nougat-ocr` *or* `marker-pdf` | End-to-end academic PDF → markdown/LaTeX |
| Image handling | `Pillow`, `opencv-python` | Cropping, preprocessing |
| CLI | `typer`, `rich` | Progress bars, pretty errors |
| Templating | `jinja2` | LaTeX skeleton |
| Testing | `pytest` | |

System-level: `tesseract-ocr`, `ghostscript`, `poppler-utils` (for some PDF ops).

---

## 4. CLI Surface

```
doc2latex convert <input> [--out out.tex] [--assets-dir assets]
                          [--backend {basic,nougat,marker}]
                          [--ocr-lang eng] [--dpi 300]
                          [--no-equations] [--no-tables]
                          [--verbose]
```

Examples:

```bash
doc2latex convert paper.pdf --backend nougat --out paper.tex
doc2latex convert report.docx
doc2latex convert scan.jpg --ocr-lang eng+deu
```

Exit codes: `0` success, `2` bad input, `3` missing system dep, `4` conversion failure.

---

## 5. Conversion Strategy by Input

### 5.1 PDF (native, text-based)

1. Open with PyMuPDF, iterate pages.
2. For each page, get text blocks with coordinates (`page.get_text("dict")`).
3. Sort blocks by reading order (top-to-bottom, left-to-right, column-aware via x-clustering).
4. Detect equation regions: blocks that are mostly images or contain heavy Unicode math (∑, ∫, √). Rasterize and feed to `pix2tex`.
5. Detect tables via Camelot; replace those bbox regions with table blocks.
6. Extract embedded images; save to `assets/figureN.png`.
7. Look for captions (lines starting with `Figure N:` / `Table N:` near the bbox) and attach.

### 5.2 PDF (scanned / image-only)

Detect by checking if `page.get_text()` returns empty. Fall back to:
1. Rasterize page at 300 DPI.
2. Run Tesseract for text.
3. Run a layout detector (or simple heuristics) to crop equation regions, send to `pix2tex`.

### 5.3 PDF (Nougat / Marker backend)

When `--backend nougat` or `--backend marker` is set, bypass the per-block pipeline and shell out to the model. Parse its markdown/MMD output and convert markdown → LaTeX with a simple translator (headings, lists, `$...$`, `$$...$$`, image refs). Both models run locally after first weight download.

### 5.4 DOCX

1. Open with `python-docx`.
2. Iterate `document.paragraphs` and `document.tables` in order.
3. Map styles → LaTeX:
   - `Heading 1..6` → `\section`, `\subsection`, ...
   - `List Bullet` → `itemize`, `List Number` → `enumerate`
   - Bold/italic runs → `\textbf{}` / `\textit{}`
4. Equations: Word stores them as OMML XML inside the paragraph. Either:
   - Convert OMML → MathML → LaTeX using a bundled XSLT (`omml2mml.xsl` from MS, then `mml2tex` via `pandoc` *if* allowed). The pure-offline route is to extract the OMML element, render it to PNG using `docx2pdf` is not offline; instead pass the OMML through `oommlx` or render via `latexml`.
   - Pragmatic fallback: extract embedded equation images directly from `word/media/` in the .docx ZIP and run `pix2tex`.
5. Embedded images are in the .docx zip under `word/media/`; copy to `assets/`.

### 5.5 JPEG / PNG

1. Run Tesseract on the full image for text.
2. Run a lightweight equation/figure detector:
   - Simple heuristic: high-density math glyph areas → `pix2tex`.
   - Or skip detection: if the user passes `--whole-equation`, treat the entire image as one equation.
3. Emit a single `figure` or `equation` block.

---

## 6. LaTeX Assembly

`templates/base.tex.jinja`:

```latex
\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath, amssymb, amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{geometry}
\geometry{margin=1in}

\title{ {{- title -}} }
\author{ {{- author -}} }

\begin{document}
\maketitle
{% for block in blocks %}
{{ block.render() }}
{% endfor %}
\end{document}
```

Per-block rendering:

- **heading** → `\section{...}` / `\subsection{...}` based on `level`
- **para** → escaped text (escape `& % $ # _ { } ~ ^ \`)
- **equation** (display) → `\begin{equation}\n<latex>\n\end{equation}`
- **equation** (inline) → `$<latex>$`
- **figure** →
  ```latex
  \begin{figure}[h]
    \centering
    \includegraphics[width=0.8\linewidth]{assets/figureN.png}
    \caption{...}
  \end{figure}
  ```
- **table** → `tabular` env with `booktabs` rules
- **list** → `itemize` / `enumerate`

---

## 7. Hard Parts — How to Tackle Them

| Problem | Approach |
|---|---|
| Multi-column reading order | Cluster blocks by x-midpoint into columns, sort each column top-down, concatenate left-to-right. |
| Equation region detection (no vision model) | Heuristic: lines with >30% non-ASCII math glyphs, or PDF image objects under 200px tall. Optional: ship Nougat backend for hard docs. |
| Equation rendering quality | Pre-process the crop: grayscale, threshold, pad whitespace. `pix2tex` is much better on clean inputs. |
| Tables without borders | Camelot's `stream` mode; tune `edge_tol`. Always render `--debug` overlays during dev. |
| Captions | Regex `^(Figure|Table)\s+\d+[.:]` on text blocks within 50px below a figure/table bbox. |
| OCR errors on equations | Never pass equation crops to Tesseract — route them to `pix2tex` only. |
| Long documents | Stream page-by-page; flush blocks to disk in append mode if memory matters. |

---

## 8. Testing

- `tests/fixtures/` holds 3 sample inputs: a native PDF, a scanned PDF, a DOCX with an equation, a JPEG of an equation.
- Each test asserts the output `.tex` compiles with `pdflatex -interaction=nonstopmode -halt-on-error`.
- Golden-file tests on emitted LaTeX (allowing minor whitespace diffs).
- Run `pytest -q` in CI; install Tesseract + Ghostscript in the GitHub Actions image.

---

## 9. Build Order (suggested for Claude Code)

1. Scaffold project layout, `pyproject.toml`, basic Typer CLI that just echoes the input path.
2. Implement `Block` dataclass + `assembler.py` + Jinja template; verify it emits a valid empty doc.
3. Implement DOCX reader (simplest path: text + headings + images). Get one fixture compiling.
4. Implement native-PDF reader with PyMuPDF, no equations yet.
5. Add `pix2tex` integration and equation routing.
6. Add table extraction via Camelot.
7. Add JPEG path (Tesseract + pix2tex).
8. Add `--backend nougat` shell-out.
9. Polish: progress bar with `rich`, error messages, README with install instructions.

---

## 10. README Essentials

The generated README should cover:
- System deps install commands for macOS, Ubuntu, Windows.
- First-run note: `pix2tex` and Nougat download model weights once (~1.4 GB for Nougat); after that everything is offline.
- Troubleshooting: missing `tesseract`, missing `gs`, `pdflatex` not found.
- Known limitations: handwritten math, complex two-column journals without Nougat, merged-cell tables.

---

## 11. Stretch Goals

- `doc2latex watch <dir>` — auto-convert any file dropped into a folder.
- `--diff` mode that re-runs only changed pages by hashing them.
- Plugin hook so users can add a custom block-type handler.
- Web UI via `gradio` (still fully local).

---

Hand this file to Claude Code with: *"Read `doc2latex-spec.md` and build the project. Start with step 1 of the build order, and after each step run the tests."*
