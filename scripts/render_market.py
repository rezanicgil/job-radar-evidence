"""Render an offline, source-linked chart from a dated board inventory."""

import json
from html import escape
from pathlib import Path
from market_inventory import PATTERNS, ROOT


def source_link(url, title):
    if not url.startswith("https://"):
        return escape(title)
    return f'<a href="{escape(url,quote=True)}">{escape(title)}</a>'


def main(inventory=None):
    inventory = inventory or max((ROOT/"reports").glob("inventory-*T*.json"))
    folder = inventory.parent
    data = json.loads(inventory.read_text(encoding="utf-8"))
    jobs = data["jobs"]
    areas = {area:[p for p in jobs if area in p["areas"]] for area in PATTERNS}
    maximum = max((len(group) for group in areas.values()),default=1) or 1
    rows = []
    for area, group in sorted(areas.items(),key=lambda x:-len(x[1])):
        employers = len({p["employer"] for p in group})
        links = "".join(f'<li>{source_link(p["url"], p["employer"]+" · "+p["title"])}</li>' for p in group)
        rows.append(f'<details><summary><span>{escape(area)}</span><meter min="0" max="{maximum}" value="{len(group)}"></meter>'
                    f'<b>{len(group)}</b><b>{employers}</b></summary>'
                    + (f'<ul>{links}</ul>' if links else '<p>No title matches in this snapshot.</p>') + '</details>')
    date = data["collected_at"][:10]
    reviewed = [json.loads(s) for s in (ROOT / "data/reviewed_employer_postings.jsonl").read_text(encoding="utf-8").splitlines()]
    separate = "".join(f'<li>{source_link(r["source_url"], r["employer"]+" · "+r["title"])} · observed {escape(r["observed_on"])}</li>'
                       for r in reviewed if r["observed_on"] <= date)
    active = sum(s["status"] == "ok" for s in data["sources"])
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Türkiye software jobs | Role coverage</title><style>
body{{max-width:60rem;margin:3rem auto;padding:0 1rem;font:1rem/1.55 system-ui;color:#192d37;background:#fbfaf6}}
h1{{line-height:1.12;font-size:clamp(2rem,6vw,3.7rem)}}summary,.head{{display:grid;grid-template-columns:2fr 1fr 4rem 5rem;gap:.5rem;align-items:center}}
summary{{padding:.6rem 0;cursor:pointer;border-top:1px solid #ccd4d1}}meter{{width:100%;accent-color:#007363}}b,.head span:last-child{{text-align:right}}.head{{font-size:.85rem}}a{{color:#006353}}
@media(max-width:520px){{summary,.head{{grid-template-columns:1fr 2.5rem 2.5rem 4rem;font-size:.83rem}}}}
</style><main><h1>Türkiye software jobs</h1><h2>Role coverage by job title</h2>
<p>{date} · {active}/{len(data["sources"])} boards responded · {len(jobs)} Türkiye-location listings · {sum(bool(p["areas"]) for p in jobs)} with role tags.</p>
<p>Open a row to inspect the postings. A listing may appear in multiple areas. Bar length represents postings in this source panel.</p>
<div class="head"><strong>Role family</strong><span></span><span>Jobs</span><span>Employers</span></div>
{"".join(rows)}<h2>Separately observed employer openings</h2><ul>{separate}</ul>
<p>These direct observations are outside the board counts above. Zero matches may indicate missing sources or insufficient title detail.</p>
<p>{source_link("", "")}<a href="{escape(inventory.name)}">Snapshot data</a></p></main></html>'''
    target = folder / f"market-coverage-{inventory.stem.removeprefix('inventory-')}.html"
    target.write_text(html,encoding="utf-8")
    print(target)
    return target


if __name__ == "__main__":
    main()
