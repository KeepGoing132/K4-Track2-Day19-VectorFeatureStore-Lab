"""Render submission images from saved notebook outputs and the actual bonus demo.

These are images of execution logs, not screenshots of a browser. They go to
submission/rendered_logs so they cannot overwrite the real UI evidence. No
scores or latencies are invented. Use capture_jupyter.py for actual screenshots.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "submission" / "rendered_logs"


def load_font(size: int):
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "consola.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/System/Library/Fonts/Menlo.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def notebook_output(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    parts = []
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        outputs = cell.get("outputs", [])
        if any(output.get("output_type") == "error" for output in outputs):
            raise RuntimeError(f"{path.name} has failed cells; rerun before rendering")
        text = []
        for output in outputs:
            if output.get("output_type") == "stream" and output.get("name") == "stdout":
                text.append("".join(output["text"]))
            elif "text/plain" in output.get("data", {}):
                text.append("".join(output["data"]["text/plain"]))
        if text:
            lines = re.sub(r"\x1b\[[0-9;]*m", "", "".join(text).strip()).splitlines()
            if len(lines) > 48:
                lines = lines[:24] + ["[... full output preserved in notebook ...]"] + lines[-24:]
            parts.append(f"[Cell {cell.get('execution_count')}]\n" + "\n".join(lines))
    if not parts:
        raise RuntimeError(f"{path.name} has no saved execution outputs")
    return "\n\n".join(parts)


def render_log(title: str, log: str, output_path: Path) -> None:
    font = load_font(16)
    lines = []
    for line in log.splitlines():
        lines.extend(textwrap.wrap(line.expandtabs(4), width=110,
                                   replace_whitespace=False, drop_whitespace=False) or [""])
    padding, line_height, width = 24, 23, 1140
    img = Image.new("RGB", (width, 72 + len(lines) * line_height + padding), (26, 27, 38))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, 48), fill=(36, 40, 59))
    draw.text((padding, 14), title, font=font, fill=(169, 177, 214))
    for index, line in enumerate(lines):
        color = (115, 218, 202) if line.startswith("PASS") else (192, 202, 245)
        draw.text((padding, 64 + index * line_height), line, font=font, fill=color)
    img.save(output_path)
    print(f"Saved {output_path.relative_to(ROOT)} ({len(lines)} lines)")


def main() -> int:
    # Read and validate every notebook before replacing any existing artifact.
    logs = [(p, notebook_output(p)) for p in sorted((ROOT / "notebooks").glob("0[1-4]_*.ipynb"))]
    if len(logs) != 4:
        raise RuntimeError("Expected four executed core notebooks")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    demo = subprocess.run([sys.executable, str(ROOT / "bonus" / "demo.py")],
                          cwd=ROOT, env=env, capture_output=True, text=True,
                          encoding="utf-8", check=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for notebook, log in logs:
        render_log(f"Execution output - {notebook.name}", log, OUT_DIR / f"{notebook.stem}.png")
    render_log("Execution output - bonus/demo.py", demo.stdout, OUT_DIR / "bonus_hybrid_memory_demo.png")
    (OUT_DIR / "bonus_demo.txt").write_text(demo.stdout, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
