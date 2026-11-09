"""Check Turkish suggestion labels against two employers' published qualification lists."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CASES=[
    ("NovaTech","https://novatechdanismanlik.com/kariyer/yazilim-gelistirici-net",
     "Bilgisayar Mühendisliği, Yazılım","İletişime Geçin",6),
    ("GİB","https://teknoloji.gib.gov.tr/Kidemli_Net_Gelistirici.html",
     "Yazılım, yazılım tasarımı","Çalışma yeri",15),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app",type=Path,default=ROOT/"releases/static-space/app.js")
    parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    report=dict(app_sha256=hashlib.sha256(args.app.read_bytes()).hexdigest(),cases=[])
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel="msedge")
        source=browser.new_page(java_script_enabled=False)
        source.route("**/*",lambda route:route.abort())
        demo=browser.new_page()
        host="https://rezanicgil-job-radar-evidence.static.hf.space/"
        demo.route(host,lambda r:r.fulfill(path=ROOT/"releases/static-space/index.html",content_type="text/html"))
        demo.route("**/app.js",lambda r:r.fulfill(path=args.app,content_type="application/javascript"))
        demo.goto(host)
        demo.get_by_text("Find conditions in a job posting").click()
        demo.locator("#postingLanguage").select_option("tr")
        for employer,url,start,end,count in CASES:
            with urlopen(url,timeout=20) as response:
                source.set_content(response.read().decode("utf-8"),wait_until="domcontentloaded")
            text=source.locator("body").inner_text()
            posting=text[text.index("\nAranan Nitelikler\n"):]
            expected=[s.strip() for s in posting[posting.index(start):posting.index(end)].splitlines() if s.strip()]
            if len(expected)!=count:
                raise ValueError(f"{employer}: reference page changed; review its qualification list.")
            demo.locator("#posting").fill(posting)
            demo.locator("#suggest").click()
            labels=demo.locator("#candidates input").evaluate_all("(xs)=>xs.map(x=>[x.value,x.dataset.preference])")
            found=dict(labels)
            correct=sum(found.get(s)==str(s.startswith("Tercihen")).lower() for s in expected)
            report["cases"].append(dict(employer=employer,url=url,posting_sha256=hashlib.sha256(posting.encode()).hexdigest(),
                                        expected=count,preferences=sum(s.startswith("Tercihen") for s in expected),
                                        correctly_typed=correct,missed=len(set(expected)-found.keys()),
                                        extra=len(found.keys()-set(expected))))
        browser.close()
    result=json.dumps(report,ensure_ascii=False,indent=2)
    print(result)
    if args.report:
        args.report.write_text(result+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
