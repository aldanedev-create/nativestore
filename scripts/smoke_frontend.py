"""Exercise real Angular/HTMX/Alpine interactions under NativeStore's CSP."""

import argparse
import os
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

from nativestore.assets import Assets
from nativestore.loader import load_app
from nativestore.server import Server

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path)
parser.add_argument("--ui", choices=("angular", "htmx-alpine"), required=True)
args = parser.parse_args()
if args.ui == "htmx-alpine":
    Assets(args.project).add("lucide")
    page = args.project / "templates/pages/Index.html"
    page.write_text(page.read_text().replace("<h1>", '<i data-lucide="house"></i><h1>', 1))
with load_app(args.project.resolve()) as app, Server(app) as server:
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as playwright:
            options = {"headless": True}
            executable = os.environ.get("NATIVESTORE_BROWSER_EXECUTABLE")
            if executable:
                options.update(
                    executable_path=executable,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process",
                        "--use-gl=angle",
                        "--use-angle=swiftshader",
                        "--disable-software-rasterizer",
                        "--no-zygote",
                    ],
                )
            browser = playwright.chromium.launch(**options)
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(server.bootstrap_url)
            if args.ui == "angular":
                page.locator("#angular-name").fill("Ada")
                page.get_by_role("button", name="Say hello").click()
                page.get_by_text("Hello, Ada!", exact=True).wait_for()
                page.locator("#angular-name").fill("")
                page.get_by_role("button", name="Say hello").click()
                page.get_by_text("Enter a name between 1 and 80 characters.", exact=True).wait_for()
            else:
                page.get_by_role("button", name="Greeting form").click()
                page.locator("#name").first.fill("Ada")
                page.get_by_role("button", name="Say hello").click()
                page.get_by_text("Hello, Ada!", exact=True).wait_for()
                assert page.locator("svg.lucide").count() > 0
                page.locator("#name").first.fill("")
                page.locator("form").evaluate("form => form.noValidate = true")
                page.get_by_role("button", name="Say hello").click()
                page.get_by_text("This field is required.", exact=True).wait_for()
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        worker.join(timeout=5)
print(f"Real {args.ui} frontend interactions passed.")
