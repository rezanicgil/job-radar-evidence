"""Compare translations with equal-step repetition on matched training cases."""

from collections import Counter, defaultdict
from hashlib import sha256
import json

import torch
from check_language_switch import language_views
from train_pair_encoder import BASE, REVISION, ROOT, AutoTokenizer, run


def evaluate(rows,predictions):
    cases=defaultdict(list)
    totals=defaultdict(Counter)
    for row,pred in zip(rows,predictions,strict=True):
        cases[row["family"],row["label"]].append(pred)
        count=totals[row["job_language"]+"/"+row["cv_language"]]
        count["total"]+=1
        count["correct"]+=int(pred==row["label"])
        count["false_full"]+=int(pred=="supported" and row["label"]!="supported")
    return dict(slices_job_then_cv=totals,changed_pairs=sum(len(set(v))>1 for v in cases.values()),
                distinct_pairs=len(cases),predictions=predictions)


def main():
    torch.set_num_threads(4)
    paths=[ROOT/"releases/match-pilot/train.jsonl",ROOT/"data/language_switch_train.jsonl"]
    base,views=([json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()] for path in paths)
    lookup={(r["family"],r["label"]):r for r in base}
    assert len(lookup)==len(base)
    originals=[r for r in views if r["original"]]
    for r in originals:
        original=lookup[r["family"],r["label"]]
        assert all(r[f]==original[f] for f in ("requirement","cv_passage"))
    extra=[r for r in views if not r["original"]]
    assert len(originals)==15 and len(extra)==45
    dev=list(language_views())
    evaluation=ROOT/"releases/match-pilot/language_switch.jsonl"
    assert dev==[json.loads(s) for s in evaluation.read_text(encoding="utf-8").splitlines()]
    assert all({r[f] for r in base+views}.isdisjoint(r[f] for r in dev) for f in ("family","requirement","cv_passage"))
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    report=dict(base=BASE,revision=REVISION,seed=17,epochs=6,batch_size=6,training_records=len(base)+len(extra),
                hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in paths},
                evaluation_sha256=sha256(evaluation.read_bytes()).hexdigest(),
                results={})
    for name,additions in (("repeat",[lookup[r["family"],r["label"]] for r in extra]),("translated",extra)):
        predictions=run(base+additions,dev,tokenizer,True,"language-"+name)["predictions"]
        scores=evaluate(dev,predictions)
        report["results"][name]=scores
        print(name,scores["changed_pairs"],dict(scores["slices_job_then_cv"]),flush=True)
    (ROOT/"reports/language-training.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
