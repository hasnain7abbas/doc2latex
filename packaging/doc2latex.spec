# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the doc2latex CLI sidecar.

Produces a single-file executable that Tauri ships as `bundle.externalBin`.

We intentionally avoid bundling the heavyweight ML deps here (pix2tex, nougat,
marker, opencv, camelot) — those bloat the binary by ~500 MB and have native
weights that PyInstaller can't always find. The basic / OCR-text / table paths
work without them. Users who want the heavy backends can install the Python
package separately and run `doc2latex` from a venv.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hiddenimports = []
hiddenimports += collect_submodules("doc2latex")
hiddenimports += collect_submodules("docx")
hiddenimports += collect_submodules("PIL")
hiddenimports += collect_submodules("fitz")
hiddenimports += collect_submodules("pdfplumber")
hiddenimports += collect_submodules("pytesseract")

datas = []
datas += collect_data_files("doc2latex", includes=["templates/*.jinja"])
datas += collect_data_files("docx", includes=["templates/*"])

a = Analysis(
    ["entrypoint.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Drop heavy optional deps — see module docstring.
        "torch",
        "torchvision",
        "transformers",
        "pix2tex",
        "nougat",
        "marker",
        "cv2",
        "camelot",
        "matplotlib",
        "scipy",
        "sklearn",
        "tensorflow",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="doc2latex",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
