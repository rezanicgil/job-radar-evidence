"""Probe retrieval when four CV passages differ only beyond a shared long prefix."""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
CASES=[
    ("Debug SQL queries with PostgreSQL execution plans.","I diagnosed slow PostgreSQL queries by examining execution plans."),
    ("Deploy Docker containers on Cloud Run.","I deployed Docker containers on Cloud Run."),
    ("Develop Android screens with Jetpack Compose.","Android ekranlarını Jetpack Compose ile geliştirdim."),
    ("Train a random forest classifier.","Sınıflandırma için rastgele orman modelini eğittim."),
]


def check(url,verify_excerpts=False):
    prefix=("The project involved weekly meetings with colleagues across different departments and offices, "*20)
    lines=[prefix+ending for _,ending in CASES]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel="chrome")
        page=browser.new_page()
        page.goto(url)
        page.locator("#cv").fill("\n".join(lines))
        page.locator("#job").fill("\n".join(q for q,_ in CASES))
        page.locator("#method").select_option("research")
        page.locator("#find").click()
        expect(page.locator("#find")).to_be_enabled(timeout=180000)
        cards=page.locator("#results article")
        expect(cards).to_have_count(len(CASES))
        ranks=[]
        for i,card in enumerate(cards.all()):
            suggestions=card.locator(":scope > p").all_inner_texts()
            rank=next((n for n,s in enumerate(suggestions,1) if s=="Page 1 · "+lines[i]),None)
            if verify_excerpts:
                assert rank==1
                excerpt=card.locator(":scope > small").first.inner_text().removeprefix("Highest-scoring excerpt · ")
                assert excerpt in lines[i] and CASES[i][1] in excerpt
            ranks.append(rank)
        browser.close()
    return ranks


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--verify-excerpts",action="store_true")
    args=parser.parse_args()
    print(json.dumps(check(args.url,args.verify_excerpts)))
