"""PyInstaller entrypoint — forwards to the Typer app."""

from doc2latex.cli import app

if __name__ == "__main__":
    app()
