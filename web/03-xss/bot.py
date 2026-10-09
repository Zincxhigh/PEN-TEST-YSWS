"""Admin bot: visits the reported URL with the admin session cookie set."""
import os
import sys
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:5000")
SECRET = os.environ.get("ADMIN_SECRET", "dev-secret")


def main():
    url = sys.argv[1]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context()
        ctx.add_cookies([{
            "name": "session", "value": SECRET,
            "url": APP_URL, "httpOnly": False,
        }])
        page = ctx.new_page()
        try:
            page.goto(url, timeout=15000)
            page.wait_for_timeout(4000)
        finally:
            browser.close()


main()
