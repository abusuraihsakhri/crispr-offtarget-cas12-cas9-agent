"""End-to-end smoke test for the static Pyodide application."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        page.on("pageerror", lambda error: errors.append(str(error)))

        page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#runtime-status')?.textContent === 'Python ready'",
            timeout=120_000,
        )

        assert page.locator("#run-button").is_enabled()
        page.locator("#run-button").click()
        page.wait_for_function(
            "() => document.querySelector('#message')?.classList.contains('success')",
            timeout=30_000,
        )

        assert page.locator("#candidate-count").text_content() == "2"
        assert page.locator("#tier-value").text_content() not in {None, "—"}
        assert page.locator("#score-value").text_content() not in {None, "—"}

        with page.expect_download(timeout=30_000) as download_info:
            page.locator("#download-button").click()
        download = download_info.value
        path = Path(download.path())
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["guide_id"] == "GUIDE-001"
        assert len(payload["evaluated_off_target_sites"]) == 2

        browser.close()

    if errors:
        raise AssertionError("Browser page errors: " + " | ".join(errors))


if __name__ == "__main__":
    main()
