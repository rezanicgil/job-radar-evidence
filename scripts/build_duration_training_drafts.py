"""Materialize private duration training examples using assistant draft labels (not human gold)."""
import json
from hashlib import sha256
from collections import Counter
from split_duration_candidates import ROOT, digest, normalized, read

# Additional inspected training-only passages; identifiers resolve against verified snapshots.
SCOPES={
 "2d7f2cd1e8":"data-related role","d05f9f744f":"unspecified","ad25b86e81":"unspecified","5e0ee33348":"unspecified",
 "a14c80e3d1":"backend development","be37f718aa":"full-stack enterprise engineering","8844b0e342":"data or software engineering",
 "3c1c1d7167":"infrastructure, platform, reliability or related engineering","c6ba426505":"software, infrastructure, database or related engineering",
 "f490b2fcca":"data or software engineering","bb2e1cf1a0":"backend or full-stack engineering","f838a176cb":"security, software or infrastructure engineering",
 "c13056c8cc":"security, network, platform or infrastructure engineering","379303955b":"software or infrastructure engineering",
 "15bd17bebc":"professional software engineering","c03d48388e":"full-stack software engineering","876d74a7af":"game analytics",
 "33b8fc6e44":"C# and Unity","b79f873df2":"mobile game QA","e3a0be2fc7":"Unity"}
COMPENSATION=set("b083286a35 5ee01c6c77 90797aafe8 70ff2ec09d 471bfc52fe 2095d4efea 92467f8f65".split())

def main():
    manifest=json.loads((ROOT/"research/duration-splits-20261110.json").read_text())
    audit=json.loads((ROOT/"reports/duration-split-similarity.json").read_text())
    eligible=set(audit["eligible_training_ids"])
    assert eligible<=set(manifest["splits"]["train"]["text_sha256"])
    assert eligible.isdisjoint(audit["exclude_from_training"])
    labels={}
    for name in ["duration-scope-draft-20261110.jsonl","duration-multi-scope-20261110.jsonl"]:
        for r in read(ROOT/"research"/name):
            h=r.get("text_sha256",r.get("passage_sha256"))
            key=(h,r["mention"]["start"] if "mention" in r else None)
            kind={"minimum_experience":"prior_experience"}.get(r["kind"],r["kind"])
            labels[key]=(kind,r["scope"])
    passages={}
    for name,checksum in manifest["snapshots"].items():
        p=ROOT/"data/raw"/name/"candidates.jsonl"
        assert sha256(p.read_bytes()).hexdigest()==checksum
        for r in read(p):
            k=digest(normalized(r["text"]))
            if k in eligible:passages.setdefault(k,r)
    assert passages.keys()==eligible and len({k[:10] for k in eligible})==len(eligible)
    out=[]
    for k,r in sorted(passages.items()):
        h=digest(r["text"])
        for m in r["mentions"]:
            label=labels.get((h,m["start"])) or labels.get((h,None))
            if label:kind,scope=label
            elif k[:10] in COMPENSATION:kind,scope="prior_experience","experience level associated with the advertised compensation band"
            else:kind,scope="prior_experience",SCOPES[k[:10]]
            out.append(dict(id=k+":"+str(m["start"]),text=r["text"],mention=m,kind=kind,scope=scope,
                            compensation_context=k[:10] in COMPENSATION,source=r["source"],status="assistant_draft"))
    dest=ROOT/"data/interim/duration-training-drafts.jsonl"
    dest.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in out),"utf8")
    report=dict(passages=len(passages),mentions=len(out),kind_counts=Counter(r["kind"] for r in out),
                compensation_context=sum(r["compensation_context"] for r in out),human_verified=0,sha256=sha256(dest.read_bytes()).hexdigest())
    (ROOT/"reports/duration-training-drafts.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(report)

if __name__=="__main__":main()
