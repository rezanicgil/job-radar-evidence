"""Verify the reviewer-confirmed coverage in a running local demo using Edge."""

from playwright.sync_api import expect, sync_playwright


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto("http://127.0.0.1:7860")
        page.get_by_role("button", name="Find evidence").click()
        choices = page.locator("select")
        expect(choices).to_have_count(2)
        coverage = page.locator("#coverage")
        choices.nth(0).select_option("s")
        expect(coverage).to_contain_text("awaiting review")
        choices.nth(1).select_option("skip")
        expect(coverage).to_have_text("Reviewer-confirmed coverage: 1/1 (100%).")
        choices.nth(1).select_option("u")
        expect(coverage).to_have_text("Reviewer-confirmed coverage: 1/2 (50%).")
        choices.nth(0).select_option("skip")
        choices.nth(1).select_option("skip")
        expect(coverage).to_have_text("No required conditions selected.")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()
    print("Browser coverage checks passed.")


if __name__ == "__main__":
    main()
