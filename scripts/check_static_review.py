"""Exercise evidence selection, coverage, export and invalidation in the staged Space."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


def check(page, origin):
    page.goto(origin)
    page.locator("#example").click()
    cards=page.locator("#results article")
    expect(cards).to_have_count(2)
    cards.first.locator(".assessment").select_option("partial")
    cards.last.locator(".assessment").select_option("supported")
    expect(page.locator("#status")).to_contain_text("0% reviewed")
    for card in cards.all():
        card.locator(".evidence").first.check()
    expect(page.locator("#status")).to_contain_text("50% coverage")
    expect(page.locator("#status")).to_contain_text("Partially supported · 1/2 (50%)")
    cards.first.locator(".gap-note").fill("Document the duration of the control software project.")
    expect(page.locator("#status")).to_contain_text("Document the duration")
    report=page.get_by_role("button",name="Download review (.txt)")
    gap=cards.first.locator(".job-gap")
    gap.fill("40 months")
    expect(report).to_be_hidden()
    gap.fill("36 months")
    expect(page.locator("#status li")).to_contain_text("36 months")
    editor=cards.first.locator(".quote-editor")
    editor.locator("summary").click()
    editor.locator(".excerpt").fill("a phrase absent from the passage")
    expect(report).to_be_hidden()
    editor.locator(".excerpt").fill("30 ay")
    expect(report).to_be_visible()
    with page.expect_download() as event:
        report.click()
    exported=event.value.path().read_text(encoding="utf-8")
    assert "1 of 2 required conditions" in exported and "Page 1" in exported
    assert "Conditions to revisit" in exported and "Document the duration" in exported
    assert "Requirement still to demonstrate: 36 months" in exported
    assert "Highlighted wording: 30 ay" in exported and "motor kontrol yazılımı geliştirdim" in exported
    cards.first.locator(".assessment").select_option("skip")
    expect(page.locator("#status")).to_contain_text("100% coverage")
    expect(page.locator("#status")).to_contain_text("1 of 1 required")
    page.locator("#cv").fill("A different applicant.")
    expect(cards).to_have_count(0)
    expect(report).to_be_hidden()
    expect(page.locator("#status")).not_to_contain_text("coverage")
    page.locator("#job").fill("• C++ and Python\n1. C++  and Python\nC++ and Python")
    page.locator("#find").click()
    expect(cards).to_have_count(1)
    expect(cards.first.locator("h3")).to_have_text("C++ and Python")
    page.get_by_text("Find conditions in a job posting").click()
    page.locator("#postingLanguage").select_option("tr")
    page.locator("#posting").fill("Aranan Nitelikler:\nPython ile geliştirme deneyimi.\nTercihen Kotlin bilgisi.\nYan haklar:\nYemek kartı.")
    page.locator("#suggest").click()
    expect(page.locator("#candidates input")).to_have_count(2)
    page.locator("#candidates input[data-preference=true]").check()
    page.locator("#append").click()
    page.locator("#find").click()
    expect(page.locator("#results article").last.locator(".assessment")).to_have_value("skip")
    page.locator("#area").select_option("Android")
    direct=page.locator("#direct article").filter(has_text="Stilus IT Solutions")
    direct.get_by_role("button",name="Review these conditions with my CV").click()
    direct.get_by_role("button",name="Replace conditions").click()
    page.locator("#find").click()
    expect(cards).to_have_count(3)
    expect(cards.last.locator(".assessment")).to_have_value("skip")
    expect(cards.last).to_contain_text("Employer preference")
    for card in cards.all()[:2]:
        card.locator(".assessment").select_option("unverified")
    expect(page.locator("#status")).to_contain_text("0 of 2 required")
    expect(page.locator("#status")).to_contain_text("1 excluded")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",type=Path)
    parser.add_argument("--channel",help="Optional installed Chromium channel")
    args=parser.parse_args()
    handler=partial(SimpleHTTPRequestHandler,directory=str(args.stage.resolve()))
    with ThreadingHTTPServer(("127.0.0.1",0),handler) as server:
        thread=Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel=args.channel)
                page=browser.new_page(viewport={"width":390,"height":820})
                check(page,f"http://127.0.0.1:{server.server_port}/")
                browser.close()
        finally:
            server.shutdown()
            thread.join()
    print("Static review checks passed")


if __name__=="__main__":
    main()
