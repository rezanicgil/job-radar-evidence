"""Collect bilingual labels for algorithm and data structure items from Wikidata."""

import json
from pathlib import Path
import re

import requests

ROOT = Path(__file__).resolve().parents[1]
# Concepts reviewed for use in software CV passage retrieval.
REVIEWED = set("""Q134164 Q1417920 Q1550629 Q1557243 Q166066 Q1937058 Q22079944
Q230848 Q2345824 Q245748 Q300159 Q3539534 Q4040283 Q470813 Q506496 Q623818
Q631518 Q757267 Q812530 Q821007 Q846780 Q94702 Q14746 Q8548""".split())
QUERY = """
SELECT DISTINCT ?item ?en ?tr WHERE {
  VALUES ?type { wd:Q8366 wd:Q175263 }
  ?item wdt:P31 ?type ; rdfs:label ?en, ?tr .
  FILTER(LANG(?en)="en" && LANG(?tr)="tr")
}
ORDER BY ?item
"""


def main():
    response = requests.get("https://query.wikidata.org/sparql",
                            params={"query": QUERY, "format": "json"},
                            headers={"User-Agent":"JobRadar/1.0 (+https://github.com/rezanicgil/job-radar-evidence)"},
                            timeout=90)
    response.raise_for_status()
    rows = []
    for binding in response.json()["results"]["bindings"]:
        item=binding["item"]["value"].rsplit("/",1)[1]
        if item not in REVIEWED:
            continue
        en, tr = (binding[key]["value"].strip() for key in ("en","tr"))
        if en.casefold()==tr.casefold() or min(len(re.findall(r"\w+", label)) for label in (en,tr))<2:
            continue
        rows.append(dict(id=item,en=en,tr=tr))
    if {r["id"] for r in rows}!=REVIEWED or len(rows)!=len(REVIEWED):
        raise ValueError("Review unexpected changes to concept availability before updating the dictionary")
    path = ROOT/"releases/static-space/bilingual-concepts.json"
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(len(rows),"bilingual concepts")


if __name__=="__main__":
    main()
