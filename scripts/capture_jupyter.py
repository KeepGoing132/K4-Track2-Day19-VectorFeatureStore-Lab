"""Capture real JupyterLab UI with Playwright; requires a running local server.

Install the optional capture tool with:
    uv pip install --python .venv/Scripts/python.exe playwright
Start JupyterLab at the repository root, then run this script in the same venv.
The default browser is the existing Microsoft Edge installation.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from jupyter_server.serverapp import list_running_servers
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORT = {"width": 1600, "height": 1100}
CAPTURES = {
    "01_embeddings_index": [
        ("01_embeddings_index.png", "Indexed: 1000 vectors"),
        ("01_paraphrase_top5.png", "Query (paraphrase):"),
    ],
    "02_hybrid_search_rrf": [
        ("02_hybrid_search_rrf.png", "Precision@10 (avg over"),
    ],
    "03_search_api_benchmark": [
        ("03_search_api_benchmark.png", "P99(wall)"),
        ("03_api_response.png", "latency_ms:"),
    ],
    "04_feast_feature_store": [
        ("04_feast_feature_store.png", "Single lookup:"),
        ("04_feast_apply.png", "Applying changes for project"),
        ("04_feast_apply_completed.png", "No changes to infrastructure"),
        ("04_feast_materialize.png", "Materializing 3 feature views from"),
    ],
    "05_filtered_search": [
        ("05_filtered_search.png", "post_ms"),
    ],
    "06_agent_retrieval": [
        ("06_agent_retrieval.png", "Δ recall vs single-shot:"),
    ],
    "07_semantic_cache": [
        ("07_semantic_cache.png", "NGUY HIỂM"),
        ("07_cache_tenant_isolation.png", "namespaced=False"),
    ],
    "08_feature_engineering": [
        ("08_feature_engineering.png", "target-naive"),
        ("08_point_in_time_join.png", "training rows"),
        ("08_on_demand_features.png", "user=u_000"),
    ],
}


async def capture(browser_name: str) -> int:
    servers = [s for s in list_running_servers() if Path(s["root_dir"]).resolve() == ROOT]
    if not servers:
        raise RuntimeError("Start JupyterLab from the repository root before capturing")
    server = servers[-1]
    stage = ROOT / ".venv" / "gui-screenshots"
    stage.mkdir(parents=True, exist_ok=True)
    manifest = {"method": "Playwright page.screenshot of real JupyterLab UI",
                "browser": browser_name, "viewport": VIEWPORT, "images": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel=browser_name, headless=True)
        for number, (stem, targets) in enumerate(CAPTURES.items(), 1):
            context = await browser.new_context(viewport=VIEWPORT)
            page = await context.new_page()
            path = f"notebooks/{stem}.ipynb"
            workspace = f"screenshots-{number}"
            await page.goto(server["url"] + f"lab/workspaces/{workspace}/tree/{path}?token=" + server["token"])
            outputs = page.locator(".jp-Notebook .jp-OutputArea-output pre")
            await outputs.first.wait_for(state="visible", timeout=60000)
            await page.locator(".jp-DirListing-item").first.wait_for(state="visible", timeout=15000)
            # Only change the live view. Cells are never executed or edited.
            await page.get_by_role("menuitem", name="View", exact=True).click()
            await page.get_by_role("menuitem", name="Collapse All Code", exact=True).click()
            # Dismiss the news toast without choosing a notification preference.
            close_toast = page.locator(".jp-Notification-Toast-Close")
            if await close_toast.count():
                await close_toast.first.evaluate("button => button.click()")
            for filename, anchor in targets:
                output = outputs.filter(has_text=anchor).first
                await output.wait_for(state="visible", timeout=30000)
                text = await output.text_content() or ""
                assert anchor in text, (stem, anchor)
                await output.evaluate("""(e, anchor) => {
                    e.scrollIntoView({block: 'start'});
                    let container = e.parentElement;
                    while (container && !(container.scrollHeight > container.clientHeight &&
                           /(auto|scroll)/.test(getComputedStyle(container).overflowY))) {
                        container = container.parentElement;
                    }
                    const position = e.textContent.indexOf(anchor);
                    const walker = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
                    let node, offset = 0;
                    while ((node = walker.nextNode())) {
                        if (offset + node.length > position) {
                            const range = document.createRange();
                            range.setStart(node, position - offset);
                            range.setEnd(node, Math.min(node.length, position - offset + 1));
                            if (container) container.scrollTop += range.getBoundingClientRect().top -
                                container.getBoundingClientRect().top - 140;
                            break;
                        }
                        offset += node.length;
                    }
                }""", anchor)
                if await close_toast.count() and await close_toast.first.is_visible():
                    await close_toast.first.evaluate("button => button.click()")
                await page.screenshot(path=str(stage / filename))
                manifest["images"].append({
                    "file": filename, "source": path, "anchor": anchor,
                    "source_sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                })
                print(f"Captured {filename}", flush=True)
            await page.get_by_role("menuitem", name="View", exact=True).click()
            await page.get_by_role("menuitem", name="Expand All Code", exact=True).click()
            await context.close()
        # Bonus evidence is the actual saved demo log in Jupyter's text editor.
        context = await browser.new_context(viewport=VIEWPORT)
        page = await context.new_page()
        path = "submission/bonus_demo.txt"
        await page.goto(server["url"] + f"lab/workspaces/screenshots-bonus/tree/{path}?token=" + server["token"])
        editor = page.locator(".jp-FileEditor .cm-content")
        await editor.wait_for(state="visible", timeout=60000)
        await page.locator(".jp-DirListing-item").first.wait_for(state="visible", timeout=15000)
        for filename, at_end in [("bonus_hybrid_memory_demo.png", False), ("bonus_demo_completed.png", True)]:
            await editor.click()
            await page.keyboard.press("Control+End" if at_end else "Control+Home")
            close_toast = page.locator(".jp-Notification-Toast-Close")
            if await close_toast.count() and await close_toast.first.is_visible():
                await close_toast.first.evaluate("button => button.click()")
            await page.screenshot(path=str(stage / filename))
            manifest["images"].append({"file": filename, "source": path,
                "source_sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()})
            print(f"Captured {filename}", flush=True)
        await context.close()
        await browser.close()

    # Publish the complete verified set only after every capture succeeds.
    output = ROOT / "submission" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    for entry in manifest["images"]:
        shutil.copy2(stage / entry["file"], output / entry["file"])
    manifest["captured_at_utc"] = datetime.now(timezone.utc).isoformat()
    (output / "capture_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(manifest['images'])} real UI screenshots to {output}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", default="msedge", choices=["msedge", "chrome"])
    args = parser.parse_args()
    return asyncio.run(capture(args.browser))


if __name__ == "__main__":
    raise SystemExit(main())
