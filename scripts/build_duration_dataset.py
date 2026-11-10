"""Export factual provenance and draft annotations, without redistributing posting passages."""
import json
from augment_duration_training import ROOT,checked
from split_duration_candidates import normalized,digest
def main():
    dest=ROOT/"releases/duration-dataset";manifest=json.loads((ROOT/"research/duration-splits-20261110.json").read_text())
    originals={}; urls={}
    for folder,checksum in manifest["snapshots"].items():
        for row in checked(ROOT/"data/raw"/folder/"candidates.jsonl",checksum):
            originals.setdefault(digest(normalized(row["text"])),row);urls[row["source"]]=row
    aux=json.loads((ROOT/"reports/auxiliary-duration-20261110.json").read_text())
    for row in checked(ROOT/"data/raw"/("unclassified-duration-"+aux["collected_utc"])/"candidates.jsonl",aux["sha256"]):urls[row["source"]]=row
    def entry(r,m,kind=None,scope=None):
        assert r["text"][m["start"]:m["end"]]==m["text"]
        k=digest(normalized(r["text"]))
        return dict(id=k+":"+str(m["start"]),passage_sha256=k,employer=urls[r["source"]]["employer"],source_url=r["source"],duration=m["text"],start=m["start"],end=m["end"],kind=kind,scope=scope,annotation_status="assistant_draft" if kind else "unlabeled")
    meta=json.loads((ROOT/"reports/duration-augmentation.json").read_text())
    rows=checked(ROOT/"data/interim/duration-training-augmented.jsonl",meta["sha256"])
    parts={"train":[entry(r,r["mention"],r["kind"],r["scope"]) for r in rows]}
    for s,part in (("validation","dev"),("test","test")):
        parts[s]=[entry(originals[k],m) for k in manifest["splits"][part]["text_sha256"] for m in originals[k]["mentions"]]
    assert len({r["id"] for rs in parts.values() for r in rs})==sum(map(len,parts.values()))
    for s,rs in parts.items():
        for t,other in parts.items():
            if s!=t:assert not {r["employer"] for r in rs}&{r["employer"] for r in other}
        (dest/(s+".jsonl")).write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rs),"utf8")
    print({s:len(rs) for s,rs in parts.items()})
if __name__=="__main__":main()
