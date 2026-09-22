"""Capture the screenshots in docs/screenshots with Playwright.

Run with `make screenshots`. It builds a throwaway SQLite database with the demo data, starts the
dev server against it on a spare port, signs in as each demo account and saves each page at
desktop size (light and dark) and at phone size. Nothing touches your own db.sqlite3.
"""

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"
PASSWORD = "apelevate-demo"


def manage(*args, env):
    subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=ROOT,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def wait_for_server(url, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)  # noqa: S310 (local dev server)
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"server at {url} didn't start")


def sign_in(page, email):
    page.context.clear_cookies()
    page.goto(f"{BASE}/accounts/login/")
    page.fill("#id_username", email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{BASE}/dashboard/")


def shoot(page, name, path, *, full_page=True, before=None):
    page.goto(f"{BASE}{path}")
    if before:
        before(page)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=OUT / f"{name}.png", full_page=full_page)
    print(f"  {name}.png")


def first_link(page, selector):
    return page.locator(selector).first.get_attribute("href")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="apelevate-shots-"))
    env = {
        **os.environ,
        "DJANGO_DEBUG": "1",
        "DATABASE_URL": f"sqlite:///{tmp / 'db.sqlite3'}",
        "DJANGO_PRIVATE_MEDIA_ROOT": str(tmp / "private"),
        "PAYMENTS_BACKEND": "fake",
        "DJANGO_LOG_LEVEL": "WARNING",
    }
    manage("migrate", "--noinput", env=env)
    manage("seed_curriculum", env=env)
    manage("seed_demo", env=env)
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server(BASE)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for scheme in ("light", "dark"):
                suffix = "" if scheme == "light" else "-dark"
                ctx = browser.new_context(
                    viewport={"width": 1280, "height": 860},
                    color_scheme=scheme,
                    device_scale_factor=2,
                )
                page = ctx.new_page()
                print(f"desktop, {scheme}")
                shoot(page, f"home{suffix}", "/", full_page=False)
                if scheme == "dark":
                    ctx.close()
                    continue
                shoot(page, "subject", "/subjects/ap-chemistry/")
                shoot(page, "classes", "/classes/")
                shoot(page, "login", "/accounts/login/", full_page=False)

                sign_in(page, "student@apelevate.test")
                shoot(page, "student-dashboard", "/dashboard/")
                page.goto(f"{BASE}/classes/mine/")
                enrolled = first_link(page, "table a[href^='/classes/']")
                shoot(page, "class-enrolled", enrolled)
                page.goto(f"{BASE}/dashboard/")
                open_class = first_link(page, ".class-card a")
                shoot(page, "class-detail", open_class)
                shoot(page, "my-classes", "/classes/mine/")
                shoot(page, "buy-tokens", "/tokens/")
                shoot(page, "apply", "/accounts/apply/")

                sign_in(page, "mentor@apelevate.test")
                shoot(page, "mentor-portal", "/teach/")
                shoot(page, "mentor-analytics", "/teach/analytics/")
                shoot(
                    page,
                    "schedule-class",
                    "/teach/classes/new/",
                    full_page=False,
                    before=lambda pg: (
                        pg.select_option("#id_subject", label="AP Chemistry"),
                        pg.wait_for_selector("#subtopic-options input[type=checkbox]"),
                        pg.check("#subtopic-options input[type=checkbox] >> nth=5"),
                        pg.check("#subtopic-options input[type=checkbox] >> nth=6"),
                    ),
                )

                sign_in(page, "admin@apelevate.test")
                shoot(page, "review-list", "/accounts/review/")
                page.goto(f"{BASE}/accounts/review/")
                shoot(page, "review-detail", first_link(page, "table a.btn"))
                ctx.close()

            print("phone, light")
            ctx = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
            )
            page = ctx.new_page()
            shoot(page, "phone-home", "/", full_page=False)
            sign_in(page, "student@apelevate.test")
            page.goto(f"{BASE}/dashboard/")
            shoot(page, "phone-class", first_link(page, ".class-card a"), full_page=False)
            shoot(page, "phone-my-classes", "/classes/mine/", full_page=False)
            sign_in(page, "mentor@apelevate.test")
            shoot(page, "phone-mentor-portal", "/teach/", full_page=False)
            ctx.close()
            browser.close()
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
