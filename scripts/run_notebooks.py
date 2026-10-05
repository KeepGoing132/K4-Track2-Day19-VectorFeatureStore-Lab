"""Execute Jupytext sources and preserve real outputs, including failures."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import jupytext
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="*", type=Path,
                        help="Jupytext .py sources; defaults to all eight notebooks")
    parser.add_argument("--timeout", type=int, default=900, help="Timeout per cell in seconds")
    args = parser.parse_args()
    sources = args.notebooks or sorted((ROOT / "notebooks").glob("[0-9]*.py"))
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    failures = []
    for source in sources:
        source = source.resolve()
        target = source.with_suffix(".ipynb")
        notebook = jupytext.read(source)
        notebook.metadata.setdefault("jupytext", {})["formats"] = "ipynb,py:percent"
        notebook.metadata["kernelspec"] = {
            "display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3",
        }
        print(f"Running {source.name}...", flush=True)
        try:
            NotebookClient(
                notebook, timeout=args.timeout, kernel_name="python3",
                resources={"metadata": {"path": str(source.parent)}},
            ).execute()
        except Exception as exc:
            failures.append(source.name)
            print(f"FAIL {source.name}: {exc}", flush=True)
        else:
            print(f"PASS {source.name}", flush=True)
        finally:
            # Keep paired metadata in sync so Jupytext's contents manager can
            # open the executed notebook without an outdated-source error.
            jupytext.write(notebook, source, fmt="py:percent")
            nbformat.write(notebook, target)
    print(f"Executed {len(sources)} notebooks; failures: {len(failures)}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
