"""Exercise evidence selection, coverage, export and invalidation in the staged Space."""

import argparse
from hashlib import sha256
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urljoin

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
    data_button=page.get_by_role("button",name="Download review (.json)")
    with page.expect_download() as event:
        data_button.click()
    data=json.loads(event.value.path().read_text(encoding="utf-8"))
    assert data["format"]=="job-radar-review-v1"
    assert data["coverage"]==dict(required=2,supported=1,partial=1,unverified=0,excluded=0,percentage=50)
    row=data["conditions"][0]
    assert row["missing"]=="36 months" and row["quotes"][0]["excerpt"]=="30 ay"
    assert row["quotes"][0]["page"]==1 and row["quotes"][0]["passage"] in exported
    assert data["cv"]["sha256"]==sha256(page.locator("#cv").input_value().encode()).hexdigest()
    cards.first.locator(".assessment").select_option("skip")
    expect(page.locator("#status")).to_contain_text("100% coverage")
    expect(page.locator("#status")).to_contain_text("1 of 1 required")
    page.locator("#cv").fill("A different applicant.")
    expect(cards).to_have_count(0)
    expect(report).to_be_hidden()
    expect(data_button).to_be_hidden()
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
    expect(cards.last).to_contain_text("Optional condition")
    for card in cards.all()[:2]:
        card.locator(".assessment").select_option("unverified")
    expect(page.locator("#status")).to_contain_text("0 of 2 required")
    expect(page.locator("#status")).to_contain_text("1 excluded")
    page.locator("#job").fill("")
    page.locator("#postingLanguage").select_option("en")
    page.locator("#posting").fill("Minimum qualifications: Know Java.\nNice to have:\nPublish an Android app.\nBenefits:\nTraining in Kotlin.")
    page.locator("#suggest").click()
    suggestions=page.locator("#candidates input")
    expect(suggestions).to_have_count(2)
    expect(suggestions.first).to_have_attribute("data-preference","false")
    expect(suggestions.last).to_have_attribute("data-preference","true")
    for suggestion in suggestions.all():
        suggestion.check()
    page.locator("#append").click()
    page.locator("#find").click()
    expect(cards.last.locator(".assessment")).to_have_value("skip")
    cards.first.locator(".assessment").select_option("unverified")
    expect(page.locator("#status")).to_contain_text("0 of 1 required")
    manual=page.get_by_text("Add wording directly from the posting")
    manual.click()
    source=page.locator("#posting")
    source.fill("Release checklist ownership\nCultural / international awareness.")
    source.evaluate("(field)=>field.setSelectionRange(0,0)")
    page.locator("#manualRequired").click()
    expect(page.locator("#conditionMessage")).to_contain_text("Highlight a condition")
    source.evaluate("(field)=>field.setSelectionRange(field.value.indexOf('Cultural'),field.value.length)")
    page.locator("#manualOptional").click()
    expect(page.locator("#job")).to_have_value("Know Java.\nPublish an Android app.\nCultural / international awareness.")
    page.locator("#find").click()
    expect(cards.last.locator(".assessment")).to_have_value("skip")
    page.locator("#manualOptional").click()
    expect(cards).to_have_count(3)
    page.locator("#manualRequired").click()
    expect(cards).to_have_count(0)
    page.locator("#find").click()
    expect(cards).to_have_count(3)
    expect(cards.last.locator(".assessment")).to_have_value("")
    dataset=Path(__file__).resolve().parents[1]/"releases/match-pilot/posting_modality.jsonl"
    for line in dataset.read_text(encoding="utf-8").splitlines():
        case=json.loads(line)
        page.locator("#postingLanguage").select_option(case["language"])
        page.locator("#posting").fill(case["posting"])
        page.locator("#suggest").click()
        expect(suggestions).to_have_count(len(case["required"])+len(case["preferred"]))
        for key,flag in [("required","false"),("preferred","true")]:
            items=page.locator(f'#candidates input[data-preference="{flag}"]')
            assert items.evaluate_all("(items)=>items.map(i=>i.value)")==case[key], case["posting"]
    page.locator("#cv").fill("Tahmin için rastgele orman kullandım.")
    page.locator("#job").fill("Train a random forest classifier.")
    page.locator("#find").click()
    expect(cards.first.get_by_role("link",name="random forest / rastgele orman")).to_have_attribute(
        "href","https://www.wikidata.org/wiki/Q245748")
    expect(cards.first.locator(".assessment")).to_have_value("")
    page.locator("#cv").fill("My documentation describes a binary search tree.")
    page.locator("#job").fill("İkili arama ağacı kullanarak arama geliştirmek.")
    page.locator("#find").click()
    expect(cards.first.get_by_role("link",name="binary search tree / İkili arama ağacı")).to_be_visible()
    page.locator("#cv").fill("Veritabanı sorgularını iyileştirdim.\nMobil uygulama geliştirdim.")
    page.locator("#job").fill("Improve database query performance")
    page.locator("#find").click()
    cards.first.locator(".assessment").select_option("partial")
    cards.first.get_by_text("Browse 2 other CV passages").click()
    search=cards.first.get_by_role("searchbox")
    search.fill("veritabani sorgu")
    expect(cards.first.locator(".evidence:visible")).to_have_count(1)
    cards.first.locator(".evidence:visible").check()
    search.fill("absent")
    expect(cards.first.locator(".evidence:visible:checked")).to_have_count(1)
    expect(page.locator("#status")).to_contain_text("0% coverage")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    case_id="source-pilot-android-1"
    page.goto(urljoin(origin,"annotate.html?case="+case_id))
    expect(page.locator("#caseLink")).to_have_attribute("href",page.url)
    expect(page.locator("#export")).to_be_disabled()
    page.locator("input[value=supported]").check()
    passage=page.locator("#passage").inner_text()
    page.locator("#quote").fill(passage)
    page.locator("#save").click()
    with page.expect_download() as event:
        page.get_by_role("button",name="Download 1 saved decision").click()
    row=json.loads(event.value.path().read_text(encoding="utf-8"))
    assert event.value.suggested_filename=="job-radar-review-1-of-12.jsonl"
    assert row["id"]==case_id and row["evidence"]==passage
    packet=Path(__file__).resolve().parents[1]/"research/source_grounded_candidates.jsonl"
    assert row["packet_sha256"]==sha256(packet.read_bytes()).hexdigest()


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
