"""Fine-tune on role swaps and measure attribution on disjoint compound examples."""

from collections import Counter
from hashlib import sha256
import json

import torch
from train_pair_encoder import BASE, REVISION, ROOT, AutoTokenizer, run

CLASSES=("applicant","other","not_stated")


def main():
    torch.set_num_threads(4)
    paths={k:ROOT/"data"/f"actor_evidence_{k}.jsonl" for k in ("train","dev")}
    splits={}
    for name,path in paths.items():
        rows=[json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
        for r in rows:
            if r["actor"]=="not_stated":
                assert r["quote"] is None and r["start"] is None and r["end"] is None
            else:
                assert r["cv_passage"][r["start"]:r["end"]]==r["quote"]
        splits[name]=[dict(**r,requirement=r["component"],label=r["actor"]) for r in rows]
    train,dev=splits["train"],splits["dev"]
    for field in ("family","component","cv_passage"):
        assert {r[field] for r in train}.isdisjoint(r[field] for r in dev)
    assert all(Counter(r["label"] for r in train if r["component"]==c)==dict.fromkeys(CLASSES,2)
               for c in {r["component"] for r in train})
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    preds=run(train,dev+train,tokenizer,True,"actor-swaps",CLASSES,"applicant")["predictions"]
    report=dict(base=BASE,revision=REVISION,seed=17,epochs=6,classes=CLASSES,
                hashes={k:sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},splits={})
    for name,rows,values in (("dev",dev,preds[:len(dev)]),("train",train,preds[len(dev):])):
        counts=Counter((r["label"],v) for r,v in zip(rows,values,strict=True))
        matrix=[[counts[t,p] for p in CLASSES] for t in CLASSES]
        report["splits"][name]=dict(total=len(rows),confusion_actual_by_predicted=matrix,predictions=values)
        print(name,matrix)
    (ROOT/"reports/actor-swaps.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
