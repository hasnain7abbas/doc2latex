"""Build the doc2latex PyInstaller sidecar for the current platform.

Tauri's `bundle.externalBin` expects a binary named
`<base>-<rust-target-triple>[.exe]` placed under `src-tauri/binaries/`. This
script:

  1. Runs PyInstaller against `packaging/doc2latex.spec`.
  2. Detects the current Rust host target triple (via `rustc -vV`, falling back
     to a Python-derived guess).
  3. Copies the produced binary to `src-tauri/binaries/doc2latex-<triple>[.exe]`.

Run it from the repo root:

    python packaging/build_sidecar.py
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "doc2latex.spec"
DIST = ROOT / "dist-sidecar"
BIN_DIR = ROOT / "src-tauri" / "binaries"


def rust_target_triple() -> str:
    """Try `rustc -vV`; fall back to a best-effort triple."""
    try:
        out = subprocess.check_output(
            ["rustc", "-vV"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if line.startswith("host:"):
                return line.split(":", 1)[1].strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    machine = platform.machine().lower()
    system = platform.system().lower()
    arch = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }.get(machine, machine)

    if system == "windows":
        return f"{arch}-pc-windows-msvc"
    if system == "darwin":
        return f"{arch}-apple-darwin"
    if system == "linux":
        return f"{arch}-unknown-linux-gnu"
    raise RuntimeError(f"unsupported platform: {system}/{machine}")


def run_pyinstaller() -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(DIST),
        "--workpath",
        str(ROOT / "build-sidecar"),
        str(SPEC),
    ]
    print("$", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))

    ext = ".exe" if os.name == "nt" else ""
    produced = DIST / f"doc2latex{ext}"
    if not produced.exists():
        raise RuntimeError(f"expected {produced} but it was not produced")
    return produced


def main() -> int:
    triple = rust_target_triple()
    print(f"target triple: {triple}")
    produced = run_pyinstaller()

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    ext = ".exe" if os.name == "nt" else ""
    out_name = f"doc2latex-{triple}{ext}"
    target = BIN_DIR / out_name
    if target.exists():
        target.unlink()
    shutil.copy2(produced, target)
    # Make sure it's executable on POSIX (PyInstaller already does this, but
    # belt and suspenders).
    if os.name != "nt":
        target.chmod(target.stat().st_mode | 0o111)

    print(f"wrote sidecar: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
