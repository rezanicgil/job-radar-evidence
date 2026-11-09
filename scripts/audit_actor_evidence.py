"""Break down prior component predictions by who performed the required action."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    data=ROOT/"data/actor_evidence_dev.jsonl"
    spans=[json.loads(line) for line in data.read_text(encoding="utf-8").splitlines()]
    keys=[(r["cv_passage"],r["component"]) for r in spans]
    if len(set(keys))!=len(spans):
        raise ValueError("Duplicate component annotation")
    annotations=dict(zip(keys,spans,strict=True))
    for row in spans:
        text,start,end=row["cv_passage"],row["start"],row["end"]
        if row["actor"]=="not_stated":
            assert start is None and end is None and row["quote"] is None
        else:
            assert row["actor"] in {"applicant","other"} and 0<=start<end<=len(text)
            assert text[start:end]==row["quote"]
    compound=ROOT/"data/compound_evidence_dev.jsonl"
    cases=[json.loads(s) for s in compound.read_text(encoding="utf-8").splitlines()]
    reference=json.loads((ROOT/"reports/compound-evidence.json").read_text(encoding="utf-8"))
    assert reference["dataset_sha256"]==sha256(compound.read_bytes()).hexdigest()
    assert set(keys)=={(r["cv_passage"],c) for r in cases for c in r["components"]}
    models={}
    for model,result in reference["results"].items():
        counts={actor:Counter() for actor in ("applicant","other","not_stated")}
        for row,pred in zip(cases,result["cases"],strict=True):
            assert pred["family"]==row["family"]
            for component,label in zip(row["components"],pred["parts"],strict=True):
                actor=annotations[(row["cv_passage"],component)]["actor"]
                counts[actor][label]+=1
        models[model]=counts
    report=dict(annotations_sha256=sha256(data.read_bytes()).hexdigest(),component_predictions_by_actor=models)
    (ROOT/"reports/actor-evidence.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(models))


if __name__=="__main__":
    main()
