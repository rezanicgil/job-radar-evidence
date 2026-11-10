"""Append auxiliary duration drafts only after held-out isolation and training deduplication."""
from collections import Counter
from difflib import SequenceMatcher
from hashlib import sha256
import json
from audit_duration_split_similarity import tokens
from split_duration_candidates import ROOT, read, normalized, digest

def checked(path,h):
    assert sha256(path.read_bytes()).hexdigest()==h
    return read(path)

def near(a,b):
    return a==b or (min(len(a),len(b))>=5 and max(SequenceMatcher(None,x,y,autojunk=False).ratio() for x,y in ((a,b),(b,a)))>=0.85)

def main():
    splits=json.loads((ROOT/"research/duration-splits-20261110.json").read_text())
    held=[splits["splits"][s] for s in ("dev","test")]
    employers={normalized(e) for group in held for e in group["employers"]}
    ids={h for group in held for h in group["text_sha256"]}
    raw=[r for folder,h in splits["snapshots"].items() for r in checked(ROOT/"data/raw"/folder/"candidates.jsonl",h)]
    protected=[r for r in raw if digest(normalized(r["text"])) in ids]
    urls={r["source"] for r in protected}
    templates={tokens(r["text"]) for r in protected}
    auxmeta=json.loads((ROOT/"reports/auxiliary-duration-20261110.json").read_text())
    aux=checked(ROOT/"data/raw"/("unclassified-duration-"+auxmeta["collected_utc"])/"candidates.jsonl",auxmeta["sha256"])
    by_key={(r["source"],digest(r["text"])):r for r in aux}
    base=checked(ROOT/"data/interim/duration-training-drafts.jsonl",json.loads((ROOT/"reports/duration-training-drafts.json").read_text())["sha256"])
    old_templates={tokens(r["text"]) for r in base}
    decisions=[]; merged=base.copy()
    for ann in read(ROOT/"research/auxiliary-duration-contexts-20261110.jsonl"):
        r=by_key[ann["source"],ann["text_sha256"]];m=ann["mention"]
        assert m in r["mentions"] and ann["employer"]==r["employer"]
        t=tokens(r["text"]); key=digest(normalized(r["text"]))+":"+str(m["start"])
        reasons=[]
        if normalized(r["employer"]) in employers: reasons.append("held-out employer")
        if r["source"] in urls: reasons.append("held-out posting")
        if any(near(t,h) for h in templates): reasons.append("held-out wording")
        if any(near(t,h) for h in old_templates): reasons.append("similar existing training passage")
        if any(row["id"]==key for row in merged): reasons.append("duplicate mention")
        if not reasons:
            merged.append(dict(id=key,text=r["text"],mention=m,kind=ann["kind"],scope=ann["scope"],compensation_context=False,source=r["source"],status=ann["status"]))
        decisions.append(dict(id=key,reasons=reasons))
    dest=ROOT/"data/interim/duration-training-augmented.jsonl"
    dest.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in merged),"utf8")
    report=dict(base=len(base),added=len(merged)-len(base),total=len(merged),counts=Counter(r["kind"] for r in merged),decisions=decisions,human_verified=0,sha256=sha256(dest.read_bytes()).hexdigest())
    (ROOT/"reports/duration-augmentation.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(report["added"],report["counts"],Counter(reason for d in decisions for reason in d["reasons"]))

if __name__=="__main__": main()
