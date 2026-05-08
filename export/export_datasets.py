import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(Path(__file__).resolve().parent / ".env")

URL = os.getenv("EASY_DATASET_URL", "http://192.168.34.65:1717")
OUTPUT_DIR = Path(__file__).resolve().parent


def export_datasets(project_id: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(f"{URL}/projects/{project_id}/datasets", timeout=30000)
        page.wait_for_load_state("networkidle")

        # Click Export button to open dialog
        page.locator('button:has-text("Export")').click()
        page.locator(".MuiDialog-root").wait_for()

        # Select JSONL file format
        page.locator('input[value="jsonl"]').click()

        # Select Custom Format
        page.locator('input[value="custom"]').click()
        page.wait_for_timeout(500)

        # Check "Include Labels"
        labels_cb = page.locator('label:has-text("Include Labels") input[type="checkbox"]')
        if not labels_cb.is_checked():
            labels_cb.check(force=True)

        # Check "Include Text Chunk"
        chunk_cb = page.locator('label:has-text("Include Text Chunk") input[type="checkbox"]')
        if not chunk_cb.is_checked():
            chunk_cb.check(force=True)

        # Ensure "Include Chain of Thought" is checked
        cot_cb = page.locator('label:has-text("Include Chain of Thought") input[type="checkbox"]')
        if not cot_cb.is_checked():
            cot_cb.check(force=True)
        # Click Confirm Export and wait for download
        with page.expect_download(timeout=60000) as download_info:
            page.locator('button:has-text("Confirm Export")').click()

        download = download_info.value
        save_path = OUTPUT_DIR / download.suggested_filename
        download.save_as(str(save_path))
        print(f"Exported to: {save_path}")

        browser.close()

    return str(save_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export datasets from Easy Dataset")
    parser.add_argument("project_id", help="Project ID to export datasets from")
    args = parser.parse_args()
    export_datasets(args.project_id)
