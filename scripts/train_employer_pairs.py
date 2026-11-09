"""Measure transfer after adding 36 employer-informed Turkish training pairs."""

from collections import Counter
import hashlib
import json

import torch
from train_pair_encoder import BASE, REVISION, ROOT, AutoTokenizer, run


def main():
    torch.set_num_threads(4)
    released=ROOT/"releases/match-pilot"
    paths={s:released/(s+".jsonl") for s in ("train","validation","source_validation")}
    paths["added"]=ROOT/"data/match_employer_training.jsonl"
    rows={k:[json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()] for k,p in paths.items()}
    counts=Counter((r["family"],r["label"]) for r in rows["added"])
    assert len(counts)==36 and set(counts.values())=={1}
    training=rows["train"]+rows["added"]
    dev=rows["validation"]+rows["source_validation"]
    for field in ("family","requirement","cv_passage"):
        assert {r[field] for r in training}.isdisjoint(r[field] for r in dev)
    assert {r["employer"] for r in rows["added"]}.isdisjoint(r["source"]["employer"] for r in rows["source_validation"])
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    result=run(training,dev,tokenizer,True,"employer-tr")
    report=dict(base=BASE,revision=REVISION,seed=17,epochs=6,batch_size=6,training_pairs=len(training),
                hashes={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},splits={})
    offset=0
    for split in ("validation","source_validation"):
        examples=rows[split]
        predictions=result["predictions"][offset:offset+len(examples)]
        pairs=[(r["label"],p) for r,p in zip(examples,predictions,strict=True)]
        metrics=dict(total=len(pairs),correct=sum(a==b for a,b in pairs),partial_found=pairs.count(("partial","partial")),
                     false_full=sum(a!="supported" and b=="supported" for a,b in pairs))
        print(split,metrics)
        report["splits"][split]=dict(**metrics,predictions=predictions)
        offset+=len(examples)
    (ROOT/"reports/employer-tr.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
