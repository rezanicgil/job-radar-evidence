"""Check the public browser implementation with the same 30 passages as the pooled trial."""

from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
HOST="https://rezanicgil-job-radar-evidence.static.hf.space/"


def main():
    source=ROOT/"data/match_source_dev.jsonl"
    rows=[json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    rows.sort(key=lambda row:sha256(row["cv_passage"].encode()).digest())
    targets=[row for row in rows if row["label"]=="supported"]
    report=dict(host=HOST,source_sha256=sha256(source.read_bytes()).hexdigest(),results={})
    with sync_playwright() as p:
        browser=p.chromium.launch(channel="msedge")
        page=browser.new_page()
        page.goto(HOST)
        app=page.request.get(HOST+"app.js")
        assert app.ok
        report["app_sha256"]=sha256(app.body()).hexdigest()
        page.locator("#cv").fill("\n".join(r["cv_passage"] for r in rows))
        page.locator("#job").fill("\n".join(r["requirement"] for r in targets))
        requests=[]
        page.on("request",lambda req:requests.append((req.method,req.url,req.post_data)))
        for method in ("terms","semantic","research"):
            requests.clear()
            page.locator("#method").select_option(method)
            page.locator("#find").click()
            page.wait_for_function("!document.querySelector('#find').disabled",timeout=180000)
            cards=page.locator("#results article")
            if cards.count()!=len(targets):raise ValueError(page.locator("#status").inner_text())
            ranks={}
            with_mentions={}
            for card,row in zip(cards.all(),targets,strict=True):
                texts=[s.removeprefix("Page 1 · ") for s in card.locator(":scope > p").all_inner_texts() if s.startswith("Page 1 · ")]
                ranks[row["family"]]=next((i for i,s in enumerate(texts,1) if s in row["cv_passage"]),None)
                mentions=card.locator(":scope > small, .technology-mentions small").all_text_contents()
                excerpts=[s.split(" · ",1)[1] for s in mentions if " · " in s]
                with_mentions[row["family"]]=any(s in row["cv_passage"] for s in texts+excerpts)
            report["results"][method]=dict(first=list(ranks.values()).count(1),visible=sum(r is not None for r in ranks.values()),
                                           reachable_with_named_mentions=sum(with_mentions.values()),ranks=ranks,
                                           target_in_ranked_or_named_mentions=with_mentions)
            outgoing=[(verb,url,body) for verb,url,body in requests if url.startswith(("https://","http://"))]
            inputs=[r["cv_passage"] for r in rows]+[r["requirement"] for r in targets]
            assert all(verb in ("GET","HEAD") and body is None and
                       not any(text in unquote(url) for text in inputs) for verb,url,body in outgoing)
            report["results"][method]["resource_hosts"]=sorted({urlsplit(url).hostname for _,url,_ in outgoing})
            print(method,report["results"][method])
        browser.close()
    (ROOT/"reports/live-pooled-retrieval.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
