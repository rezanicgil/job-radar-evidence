"""Test selective suggestions using margins chosen only on the original validation split."""

import hashlib
import json

import torch
from train_pair_encoder import ROOT, AutoModelForSequenceClassification, AutoTokenizer, encode

MIN_ACCEPTED = 3
TARGET_PRECISION = 0.8


def predictions(path, rows):
    model = AutoModelForSequenceClassification.from_pretrained(path).eval()
    tokenizer = AutoTokenizer.from_pretrained(path)
    with torch.inference_mode():
        logits = model(**encode(rows, tokenizer)).logits
        values, indices = logits.topk(2, dim=1)
    return [dict(family=row["family"], actual=row["label"], predicted=model.config.id2label[i],
                 margin=margin) for row,i,margin in
            zip(rows,indices[:,0].tolist(),(values[:,0]-values[:,1]).tolist(),strict=True)]


def thresholds(rows):
    result = {}
    for label in ("supported","partial","unverified"):
        group = [r for r in rows if r["predicted"]==label]
        result[label] = None
        for threshold in sorted({r["margin"] for r in group}):
            chosen = [r for r in group if r["margin"]>=threshold]
            hits = sum(r["actual"]==label for r in chosen)
            if len(chosen)>=MIN_ACCEPTED and hits/len(chosen)>=TARGET_PRECISION:
                result[label] = threshold
                break
    return result


def measure(rows, cutoffs):
    accepted = [r for r in rows if cutoffs[r["predicted"]] is not None and r["margin"]>=cutoffs[r["predicted"]]]
    return dict(total=len(rows), accepted=len(accepted), abstained=len(rows)-len(accepted),
                correct=sum(r["actual"]==r["predicted"] for r in accepted),
                suggested_full=sum(r["predicted"]=="supported" for r in accepted),
                false_full=sum(r["predicted"]=="supported" and r["actual"]!="supported" for r in accepted),
                partial_found=sum(r["actual"]==r["predicted"]=="partial" for r in accepted))


def main():
    torch.set_num_threads(4)
    splits = {}
    hashes = {}
    for split in ("validation","source_validation"):
        path = ROOT/"releases/match-pilot"/(split+".jsonl")
        splits[split] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(min_accepted=MIN_ACCEPTED,target_dev_precision=TARGET_PRECISION,
                  split_sha256=hashes,models={})
    for checkpoint in ("pair-mentions-v3","pair-duration-weak"):
        path=ROOT/"runs"/checkpoint
        evaluated={split:predictions(path,rows) for split,rows in splits.items()}
        cutoffs=thresholds(evaluated["validation"])
        result={}
        for split,rows in evaluated.items():
            result[split]=dict(unfiltered=measure(rows,dict.fromkeys(cutoffs,0)),
                               selective=measure(rows,cutoffs),predictions=rows)
        report["models"][checkpoint]=dict(cutoffs=cutoffs,splits=result)
        print(checkpoint,cutoffs,result["source_validation"]["selective"])
    (ROOT/"reports/selective-evidence.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
