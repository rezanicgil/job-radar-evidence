"""Verify the public Space and the public market dataset against one local snapshot."""
import argparse,json
from urllib.request import urlopen
from urllib.parse import quote
from publish_market_dataset import section_rows

def verify(snapshot,space_revision,dataset_revision):
    with urlopen("https://rezanicgil-job-radar-evidence.static.hf.space/market.json?rev="+quote(space_revision),timeout=30) as f:
        live=json.load(f)
    assert live["collected_at"]==snapshot["collected_at"]
    date=live["observation_date"]
    def dataset_rows(group):
        url=f"https://huggingface.co/datasets/rezanicgil/turkiye-software-job-market/resolve/{dataset_revision}/{group}/{date}.jsonl"
        with urlopen(url,timeout=30) as f:return [json.loads(line) for line in f if line.strip()]
    published=dataset_rows("postings")
    measured={p["url"]:p for p in published if p["description_status"]!="not_selected"}
    for rows in (snapshot["postings"],live["postings"]):
        assert len(rows)==len(measured) and {r["url"] for r in rows}==measured.keys()
        for r in rows:
            p=measured[r["url"]]
            assert (r["status"],r.get("skills"),r.get("sections"))==(p["description_status"],p["technologies"],p["sections"])
    assert dataset_rows("sections")==list(section_rows({"date":date,"vocabulary":live["vocabulary"]},published))
    print("Verified posting measurements and all qualification/preference denominators:",date,len(measured))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("snapshot","space_revision","dataset_revision"):parser.add_argument(key)
    a=parser.parse_args()
    with open(a.snapshot,encoding="utf8") as f:verify(json.load(f),a.space_revision,a.dataset_revision)
