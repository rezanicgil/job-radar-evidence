"""Exercise evidence selection, coverage, export and invalidation in the staged Space."""

import argparse
from hashlib import sha256
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urljoin, urlsplit, parse_qs

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
    page.locator("#jobDetails summary").click()
    page.locator("#jobEmployer").fill("Example Company")
    page.locator("#jobTitle").fill("Embedded Engineer")
    page.locator("#jobUrl").fill("javascript:alert(1)")
    report.click()
    expect(page.locator("#jobUrl")).to_be_focused()
    expect(page.locator("#jobUrlError")).to_contain_text("HTTPS")
    page.locator("#jobUrl").fill("https://example.org/jobs/embedded")
    with page.expect_download() as event:
        report.click()
    exported=event.value.path().read_text(encoding="utf-8")
    assert "1 of 2 required conditions" in exported and "Page 1" in exported
    assert "Example Company · Embedded Engineer" in exported and "https://example.org/jobs/embedded" in exported
    assert "Conditions to revisit" in exported and "Document the duration" in exported
    assert "Requirement still to demonstrate: 36 months" in exported
    assert "Highlighted wording: 30 ay" in exported and "motor kontrol yazılımı geliştirdim" in exported
    data_button=page.get_by_role("button",name="Download review (.json)")
    with page.expect_download() as event:
        data_button.click()
    data=json.loads(event.value.path().read_text(encoding="utf-8"))
    assert data["format"]=="job-radar-review-v1"
    assert data["job"]["source"]=="manual" and data["job"]["employer"]=="Example Company"
    assert data["coverage"]==dict(required=2,supported=1,partial=1,unverified=0,excluded=0,percentage=50)
    row=data["conditions"][0]
    assert row["next_edit"]==row["note"] and row["next_edit"] in exported
    assert row["missing"]=="36 months" and row["quotes"][0]["excerpt"]=="30 ay"
    assert row["quotes"][0]["page"]==1 and row["quotes"][0]["passage"] in exported
    assert data["cv"]["sha256"]==sha256(page.locator("#cv").input_value().encode()).hexdigest()
    cards.first.locator(".assessment").select_option("skip")
    expect(page.locator("#status")).to_contain_text("100% coverage")
    expect(page.locator("#status")).to_contain_text("1 of 1 required")
    with page.expect_download() as event:
        data_button.click()
    second=json.loads(event.value.path().read_text(encoding="utf-8"))
    comparison=page.context.browser.new_page(viewport={"width":390,"height":820})
    comparison.goto(urljoin(origin,"compare.html"))
    def select_report(field,name,report):
        comparison.locator(field).set_input_files(dict(name=name,mimeType="application/json",
                                                       buffer=json.dumps(report).encode()))
    select_report("#first","first.json",data)
    select_report("#second","second.json",second)
    expect(comparison.locator("#message")).to_contain_text("same CV input")
    expect(comparison.locator(".metric")).to_have_text(["50% coverage","100% coverage"])
    expect(comparison.get_by_role("link",name="Open source posting").first).to_have_attribute("href","https://example.org/jobs/embedded")
    comparison.get_by_text("Conditions to revisit (1)").click()
    expect(comparison.locator("article li")).to_contain_text("36 months")
    alignment=comparison.locator(".alignment").first
    expect(alignment).to_contain_text("2 conditions with matching wording · 1 assessed differently")
    alignment.get_by_text("Different assessments (1)").click()
    changed=alignment.locator("details[open]")
    expect(changed).to_contain_text("First review · Partially supported")
    expect(changed).to_contain_text("Second review · Excluded")
    expect(changed.locator("blockquote")).to_have_text("30 ay")
    expect(changed).to_contain_text("Search rank 1")
    rewritten=[dict(r,condition="Develop a C++ device driver") if i==0 else r for i,r in enumerate(second["conditions"])]
    select_report("#second","another-role.json",dict(second,conditions=rewritten))
    expect(alignment).to_contain_text("1 condition with matching wording · 0 assessed differently")
    expect(alignment).to_contain_text("Only in the first review (1)")
    expect(alignment).to_contain_text("Only in the second review (1)")
    related=comparison.locator(".technologies")
    related.get_by_text("C++",exact=True).click()
    expect(related).to_contain_text("Develop a C++ device driver")
    assert comparison.evaluate("document.documentElement.scrollWidth <= innerWidth")
    select_report("#second","another-cv.json",dict(second,cv=dict(second["cv"],sha256="0"*64)))
    expect(comparison.locator("#message")).to_contain_text("different CV inputs")
    select_report("#second","invalid.json",dict(second,coverage=data["coverage"]))
    expect(comparison.locator("#message")).to_contain_text("differs from its condition decisions")
    expect(comparison.locator(".metric")).to_have_count(0)
    comparison.close()
    page.locator("#cv").fill("A different applicant.")
    expect(cards).to_have_count(0)
    expect(report).to_be_hidden()
    expect(data_button).to_be_hidden()
    expect(page.locator("#status")).not_to_contain_text("coverage")
    page.locator("#job").fill("• C++ and Python\n1. C++  and Python\nC++ and Python")
    page.locator("#find").click()
    expect(page.locator("#conditionPreview")).to_contain_text("1 required")
    expect(cards).to_have_count(1)
    expect(cards.first.locator("h3")).to_have_text("C++ and Python")
    page.get_by_text("Find conditions in a job posting").click()
    page.locator("#postingLanguage").select_option("tr")
    page.locator("#posting").fill("İş Tanımı\nMobil uygulamalar geliştiriyoruz.\n\u200bNe arıyoruz?\nFlutter ile uygulama geliştirdin.\nHangi ek beceriler öne çıkmanıza yardımcı olacak?\nGPS servislerini kullandın.\nNeler sunuyoruz?\nÖzel sağlık sigortası.")
    page.locator("#suggest").click()
    suggested=page.locator("#candidates input")
    expect(suggested).to_have_count(2)
    expect(suggested.first).to_have_value("Flutter ile uygulama geliştirdin.")
    expect(suggested.first).to_have_attribute("data-preference","false")
    expect(suggested.last).to_have_value("GPS servislerini kullandın.")
    expect(suggested.last).to_have_attribute("data-preference","true")
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
    expect(page.locator("#conditionPreview")).to_contain_text("2 required · 1 optional")
    expect(cards).to_have_count(3)
    expect(cards.last.locator(".assessment")).to_have_value("skip")
    expect(cards.last).to_contain_text("Optional condition")
    for card in cards.all()[:2]:
        card.locator(".assessment").select_option("unverified")
    expect(page.locator("#status")).to_contain_text("0 of 2 required")
    expect(page.locator("#status")).to_contain_text("1 excluded")
    opt=cards.last
    opt.locator(".assessment").select_option("optional-partial")
    expect(page.locator("#status")).to_contain_text("0 of 2 required")
    expect(data_button).to_be_hidden()
    browse=opt.get_by_text("Browse ",exact=False)
    if browse.count(): browse.first.click()
    opt.locator(".evidence").first.check()
    opt.locator(".gap-note").fill("Add a concrete example of the optional skill.")
    expect(page.locator("#status")).to_contain_text("1 optional assessment recorded separately")
    with page.expect_download() as event:
        data_button.click()
    optional_export=json.loads(event.value.path().read_text(encoding="utf-8"))
    assert optional_export["coverage"]["required"]==2 and optional_export["coverage"]["percentage"]==0
    row=optional_export["conditions"][-1]
    assert row["label"]=="skip" and not row["quotes"]
    assert row["preference_review"]["label"]=="partial" and len(row["preference_review"]["quotes"])==1
    with page.expect_download() as event:
        report.click()
    txt=event.value.path().read_text(encoding="utf-8")
    assert "Optional assessment: partial" in txt and row["preference_review"]["quotes"][0]["passage"] in txt
    opt.locator(".assessment").select_option("skip")
    expect(page.locator("#status")).not_to_contain_text("optional assessment recorded")
    page.locator("#job").fill("")
    page.locator("#postingLanguage").select_option("en")
    page.locator("#posting").fill("About your experience\nShip an iOS feature.\nNice to have\nUse a profiler.\nWhy you should join Example Company\nReceive an annual training budget.")
    page.locator("#suggest").click()
    proposed=page.locator("#candidates input")
    expect(proposed).to_have_count(2)
    expect(proposed.first).to_have_value("Ship an iOS feature.")
    expect(proposed.last).to_have_attribute("data-preference","true")
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
    page.locator("#postingLanguage").select_option("tr")
    page.locator("#posting").fill("Deneyimli bir geliştirici arıyoruz.\nAranan\u00a0Nitelikler: Java bilgisi.\nTercihen Docker deneyimi.\nYan haklar:\nEğitim bütçesi.")
    page.locator("#suggest").click()
    expect(suggestions).to_have_count(2)
    expect(suggestions.first).to_have_value("Java bilgisi.")
    expect(suggestions.last).to_have_attribute("data-preference","true")
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
    page.locator("#cv").fill("Nearly four years building production APIs.")
    page.locator("#job").fill("Flutter geliştirme deneyimi (2+ yıl)")
    page.locator("#find").click()
    expect(cards.first).to_contain_text("The condition mentions 24 months.")
    expect(cards.first.locator(".assessment")).to_have_value("")
    grouped=Path(__file__).resolve().parents[1]/"releases/match-pilot/technology_connectives.jsonl"
    cases={r["family"]:r for line in grouped.read_text(encoding="utf-8").splitlines() if (r:=json.loads(line))}
    ambiguous=["Use Kafka and RabbitMQ or a managed alternative.","Experience with Java, Kotlin or another language."]
    conditions=[row[key] for row in cases.values() for key in ("all","any")]+ambiguous
    page.locator("#job").fill("\n".join(conditions))
    page.locator("#find").click()
    expect(cards).to_have_count(len(conditions))
    for i,_ in enumerate(cases):
        expect(cards.nth(i*2)).to_contain_text("Combined technologies")
        expect(cards.nth(i*2+1)).to_contain_text("Alternative technologies")
        expect(cards.nth(i*2+1).locator(".assessment")).to_have_value("")
    for i in range(len(conditions)-len(ambiguous),len(conditions)):
        expect(cards.nth(i)).not_to_contain_text("look for evidence covering each")
        expect(cards.nth(i)).not_to_contain_text("Alternative technologies")
    passages=[f"Diagnostics project {i} produced a distinct result." for i in range(1,13)]
    page.locator("#cv").fill("\n".join(passages))
    page.locator("#job").fill("Diagnostics")
    page.locator("#find").click()
    card=cards.first
    card.get_by_text("Inspect and select CV evidence").click()
    card.get_by_text("Browse 9 other CV passages").click()
    evidence=card.locator(".evidence[data-rank='12']")
    evidence.check()
    expect(card.locator(".assessment")).to_have_value("")
    expect(page.locator("#status")).to_contain_text("0% reviewed")
    card.locator(".assessment").select_option("supported")
    expect(evidence).to_be_checked()
    with page.expect_download() as event:
        data_button.click()
    result=json.loads(event.value.path().read_text(encoding="utf-8"))
    quote=result["conditions"][0]["quotes"][0]
    assert quote["search_rank"]==12 and quote["passage"]==passages[-1]
    page.get_by_text("Preview passage search feedback").click()
    draft=page.get_by_role("link",name="Open GitHub feedback form")
    query=parse_qs(urlsplit(draft.get_attribute("href")).query)
    assert set(query)=={"template","summary"} and query["template"]==["passage_search.yml"]
    summary=query["summary"][0]
    assert "Best selected passage ranked 4 or lower: 1" in summary
    assert all(value not in summary for value in [passages[-1],"Diagnostics",result["cv"]["sha256"]])
    assert summary==page.locator("details pre").inner_text()
    with page.expect_download() as event:
        report.click()
    assert "Search rank: 12" in event.value.path().read_text(encoding="utf-8")
    card.locator(".evidence[data-rank='1']").check()
    updated=parse_qs(urlsplit(draft.get_attribute("href")).query)["summary"][0]
    assert "Conditions with selected evidence: 1" in updated and "Best selected passage ranked 1–3: 1" in updated
    assert "Best selected passage ranked 4 or lower: 0" in updated
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
    page.get_by_text("Preview passage search feedback").click()
    assert "Only unranked passages selected: 1" in page.locator("details pre").inner_text()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#area").select_option("")
    snapshot=page.request.get(urljoin(origin,"market.json")).json()
    records=[r for r in snapshot["postings"] if r["status"]=="readable"]
    if records and all(r.get("description_sha256") for r in records):
        distinct=len({(r["employer"],r["description_sha256"]) for r in records})
        expect(page.locator("#scope")).to_contain_text(f"{distinct} distinct descriptions")
    alternatives=sum(r.get("location_scope")=="listed_alternative" for r in records)
    if alternatives:
        expect(page.locator("#scope")).to_contain_text(f"{alternatives} postings explicitly list Türkiye")
    if records and all(r.get("description_sha256") for r in records):
        page.locator("#area").select_option("Mobile (general/cross-platform)")
        subset=[r for r in records if "Mobile (general/cross-platform)" in r["areas"]]
        if subset:
            page.locator("#basis").select_option("descriptions")
            page.locator("#skillSearch").fill("Flutter")
            unique=lambda rows: len({(r["employer"],r["description_sha256"]) for r in rows})
            mentioning=[r for r in subset if "Flutter" in r["skills"]]
            expect(page.locator("#counts summary")).to_contain_text(f"{unique(mentioning)}/{unique(subset)} distinct descriptions")
            with page.expect_download() as event:
                page.locator("#marketExport").click()
            exported=event.value.path().read_text(encoding="utf-8")
            assert "Role: Mobile (general/cross-platform)" in exported and "Technology filter: Flutter" in exported
            assert f"({unique(mentioning)}/{unique(subset)})" in exported
            assert all(r["url"] in exported for r in mentioning)
            assert all(r["url"] not in exported for r in subset if r not in mentioning)
            page.locator("#mentionScope").select_option("preferences")
            expect(page.locator("#basis")).to_have_value("postings")
            page.locator("#mentionScope").select_option("all")
        page.locator("#area").select_option("")
    users=[r for r in records if "React Native" in r["skills"]]
    page.locator("#skillSearch").fill("React Native")
    chart=page.locator("#counts details")
    expect(chart).to_have_count(1)
    expect(chart.locator("summary")).to_contain_text(f"{len(users)}/{len(records)} postings")
    employers={r["employer"] for r in records}
    expect(chart.locator("summary")).to_contain_text(f"{len({r['employer'] for r in users})}/{len(employers)} employers")
    chart.locator("summary").click()
    expect(chart.locator("li a")).to_have_count(len(users))
    contributors={r["employer"] for r in users}
    if len(contributors)==1:
        employer=contributors.pop()
        expect(chart.locator("summary")).to_contain_text("All mentions from "+employer)
        outside=sum(r["employer"]!=employer for r in records)
        expect(chart).to_contain_text(f"0% (0/{outside} postings)" if outside else "no postings remain")
    page.locator("#mentionScope").select_option("preferences")
    mobile=next((p for p in records if p["url"].endswith("744000109926925")),None)
    if mobile and mobile.get("sections") is not None:
        page.locator("#area").select_option("Mobile (general/cross-platform)")
        page.locator("#skillSearch").fill("Git")
        chart=page.locator("#counts details").filter(has=page.get_by_text("Git",exact=True)).first
        chart.locator("summary").click()
        expect(chart.get_by_role("link",name=mobile["title"],exact=True)).to_be_visible()
        page.locator("#mentionScope").select_option("qualifications")
        chart.locator("summary").click()
        expect(chart.get_by_role("link",name=mobile["title"],exact=True)).to_have_count(0)
        page.locator("#mentionScope").select_option("preferences")
        page.locator("#area").select_option("")
    preference_rows=[p for p in records if any(s["kind"]=="preferences" for s in p.get("sections") or [])]
    expect(page.locator("#skillCount")).to_contain_text(f"{len(preference_rows)} of {len(records)} readable postings")
    if preference_rows:
        sample=next((name for p in preference_rows for s in p["sections"] if s["kind"]=="preferences" for name in s["skills"]),None)
        if sample:
            page.locator("#skillSearch").fill(sample)
            matched=[p for p in preference_rows if any(s["kind"]=="preferences" and sample in s["skills"] for s in p["sections"])]
            row=page.locator("#counts details").filter(has=page.get_by_text(sample,exact=True)).first
            expect(row.locator("summary")).to_contain_text(f"{len(matched)}/{len(preference_rows)} postings")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#mentionScope").select_option("all")
    page.locator("#skillSearch").fill("Python")
    python_chart=page.locator("#counts details").filter(has=page.get_by_text("Python",exact=True))
    python_chart.locator("summary").click()
    listing=python_chart.locator("li").filter(has_text="Smart Start Data Analytics & Digitalization Engineer")
    review_urls={r["source_url"] for r in snapshot["reviews"]}
    if "https://jobs.smartrecruiters.com/BoschGroup/744000159887118" in review_urls:
        expect(listing).to_have_count(1)
        cv=page.locator("#cv").input_value()
        listing.get_by_role("button",name="Review these conditions with my CV").click()
        listing.get_by_role("button",name="Replace conditions").click()
        expect(page.locator("#cv")).to_have_value(cv)
        expect(page.locator("#conditionPreview")).to_contain_text("2 required · 1 optional")
        assert page.locator("#job").input_value().splitlines()==[
            "Familiarity with Power BI or Tableau for data visualization and reporting",
            "Basic knowledge of Python, SQL, and data modeling",
            "Familiarity with Agentic AI concepts or applications is an asset"]
        page.locator("#find").click()
        expect(cards).to_have_count(3)
        expect(cards.last.locator(".assessment")).to_have_value("skip")
    examples=page.locator("#verified article").filter(has_text="Digital Image Processing Engineer")
    if "https://jobs.smartrecruiters.com/BoschGroup/744000152330664" in review_urls:
        expect(examples).to_have_count(1)
        expect(examples).to_contain_text("Other programming languages can qualify")
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
