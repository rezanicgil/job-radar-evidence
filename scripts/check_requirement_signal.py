"""Compare CV-only and requirement-conditioned linear probes on frozen embeddings."""

import hashlib
import json

import torch
from transformers import AutoModel, AutoTokenizer

from evaluate_pooled_retrieval import embeddings
from train_smoke import BASE, REVISION, ROOT, LABELS


def features(rows, cache, paired):
    cv=torch.stack([cache[r["cv_passage"]] for r in rows])
    if not paired:
        return cv
    job=torch.stack([cache[r["requirement"]] for r in rows])
    product=torch.nn.functional.normalize(cv*job)
    return torch.nn.functional.normalize(torch.cat([cv,job,(cv-job).abs(),product],dim=1))


def main():
    torch.set_num_threads(4)
    files=dict(train=ROOT/"releases/match-pilot/train.jsonl",added=ROOT/"data/match_employer_training.jsonl",
               validation=ROOT/"releases/match-pilot/validation.jsonl",source=ROOT/"data/match_source_dev.jsonl",
               duration=ROOT/"data/duration_threshold_dev.jsonl",switch=ROOT/"data/requirement_switch_dev.jsonl")
    rows={name:[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] for name,path in files.items()}
    training=rows["train"]+rows["added"]
    checks={k:rows[k] for k in ("validation","source")}
    checks["duration"]=[dict(family=r["skill"],cv_passage=r["cv_passage"],requirement=r[key],label=label)
                        for r in rows["duration"] for key,label in (("met","supported"),("short","partial"))]
    checks["switch"]=[dict(family=r["family"],cv_passage=r["cv_passage"],requirement=r["requirements"][label],label=label)
                      for r in rows["switch"] for label in ("supported","partial","unverified")]
    texts=sorted({r[field] for split in [training,*checks.values()] for r in split for field in ("cv_passage","requirement")})
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    encoder=AutoModel.from_pretrained(BASE,revision=REVISION).eval()
    cache={}
    for offset in range(0,len(texts),32):
        batch=texts[offset:offset+32]
        cache.update(zip(batch,embeddings(encoder,tokenizer,batch),strict=True))
    y=torch.nn.functional.one_hot(torch.tensor([LABELS.index(r["label"]) for r in training]),num_classes=3).double()
    results={}
    for paired in (False,True):
        x=features(training,cache,paired).double()
        mean=x.mean(0)
        x=x-mean
        # Closed-form ridge with one fixed penalty and an unpenalized intercept.
        weights=x.T@torch.linalg.solve(x@x.T+torch.eye(len(x),dtype=x.dtype),y-y.mean(0))
        report={}
        for name,examples in checks.items():
            scores=(features(examples,cache,paired).double()-mean)@weights+y.mean(0)
            pred=[LABELS[i] for i in scores.argmax(1).tolist()]
            pairs=[(r["label"],p) for r,p in zip(examples,pred,strict=True)]
            metrics=dict(total=len(pairs),correct=sum(a==b for a,b in pairs),
                         partial_found=pairs.count(("partial","partial")),
                         false_full=sum(a!="supported" and b=="supported" for a,b in pairs))
            if name=="duration":
                metrics["threshold_pairs_both_correct"]=sum(a=="supported" and b=="partial" for a,b in zip(pred[::2],pred[1::2],strict=True))
                metrics["threshold_pairs_changed"]=sum(a!=b for a,b in zip(pred[::2],pred[1::2],strict=True))
            if name=="switch":
                triples=list(zip(pred[::3],pred[1::3],pred[2::3],strict=True))
                metrics["families_all_correct"]=triples.count(("supported","partial","unverified"))
                metrics["families_changed"]=sum(len(set(triple))>1 for triple in triples)
            print(paired,name,metrics)
            report[name]=dict(**metrics,predictions=pred)
        results["paired" if paired else "cv_only"]=report
    output=dict(base=BASE,revision=REVISION,ridge_penalty=1,training_count=len(training),
                sha256={k:hashlib.sha256(f.read_bytes()).hexdigest() for k,f in files.items()},results=results)
    (ROOT/"reports/requirement-signal.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
