"""Measure passage ranking through the public Space using fictional development data."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://rezanicgil-job-radar-evidence.static.hf.space/"


def main():
    families = defaultdict(list)
    files = ["match_training_v1.jsonl", "match_contrasts_v2.jsonl", "match_challenge_dev.jsonl"]
    for name in files:
        for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            families[row["family"]].append(row)
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge")
        page = browser.new_page()
        page.goto(HOST)
        script = page.request.get(HOST + "app.js")
        assert script.ok
        digest = sha256(script.body()).hexdigest()
        for family, rows in families.items():
            if any(re.search(r"(?<=[.!?])\s+",r["cv_passage"]) for r in rows):
                continue
            assert len(rows)==3 and len({r["requirement"] for r in rows})==1
            labels = {r["cv_passage"]:r["label"] for r in rows}
            rows.sort(key=lambda r:r["cv_passage"])
            for reverse in (False,True):
                ordered = list(reversed(rows)) if reverse else rows
                page.locator("#cv").fill("\n".join(r["cv_passage"] for r in ordered))
                page.locator("#job").fill(rows[0]["requirement"])
                for method in ("terms","semantic"):
                    page.locator("#method").select_option(method)
                    page.locator("#find").click()
                    page.wait_for_function("!document.querySelector('#find').disabled",timeout=180000)
                    article = page.locator("#results article")
                    if article.count()!=1:
                        raise RuntimeError(page.locator("#status").inner_text())
                    passages = article.locator("p").all_inner_texts()
                    ranked = [labels[s.removeprefix("Page 1 · ")] for s in passages if s.startswith("Page 1 · ")]
                    results.append(dict(family=family,reverse=reverse,method=method,ranked=ranked))
        browser.close()
    counts = {}
    for method in ("terms","semantic"):
        runs = [r for r in results if r["method"]==method]
        counts[method]=dict(orders=len(runs),supported_first=sum(r["ranked"][:1]==["supported"] for r in runs),
                            supported_visible=sum("supported" in r["ranked"] for r in runs))
    report = dict(host=HOST,app_js_sha256=digest,source_files=files,counts=counts,results=results)
    target = ROOT / "reports/live-retrieval-dev.json"
    target.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(counts)


if __name__ == "__main__":
    main()
