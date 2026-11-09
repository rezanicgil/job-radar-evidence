"""Compare lexical and multilingual retrieval of exact actor evidence spans."""

from hashlib import sha256
import json
import re

import torch
from transformers import AutoModel, AutoTokenizer
from evaluate_pooled_retrieval import bm25, embeddings, terms
from train_smoke import BASE, REVISION, ROOT


def candidates(passage):
    # Keep whole sentences as candidates when a conjunction joins nouns or adjectives.
    sentences=[s.strip(" .!?\t\n") for s in re.split(r"[;!?]|(?<!\d)\.(?=\s|$)|\n",passage)]
    return list(dict.fromkeys(s for sentence in sentences for s in
                 [sentence,*re.split(r"\s+(?:and|ve)\s+",sentence,flags=re.I)] if s))


def top(row, vectors, method):
    texts=candidates(row["cv_passage"])
    if method!="bm25":
        scores=[vectors[row["component"]].dot(vectors[t]).item() for t in texts]
    else:
        scores=bm25(row["component"],[terms(t) for t in texts])
    best=max(range(len(texts)),key=lambda i:scores[i])
    return texts[best],scores[best]


def metrics(rows,hits,threshold):
    preds=[text if score>=threshold else None for text,score in hits]
    cases=[dict(family=r["family"],component=r["component"],actor=r["actor"],gold=r["quote"],predicted=p)
           for r,p in zip(rows,preds,strict=True)]
    positives=[c for c in cases if c["gold"] is not None]
    return dict(total=len(rows),exact=sum(c["gold"]==c["predicted"] for c in cases),
                positive_exact=sum(c["gold"]==c["predicted"] for c in positives),positive=len(positives),
                returned_on_null=sum(c["gold"] is None and c["predicted"] is not None for c in cases),
                null=len(rows)-len(positives),cases=cases)


def main():
    torch.set_num_threads(4)
    files={k:ROOT/"data"/f"actor_evidence_{k}.jsonl" for k in ("train","dev")}
    rows={k:[json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] for k,p in files.items()}
    texts=sorted({t for split in rows.values() for r in split for t in [r["component"],*candidates(r["cv_passage"])]})
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    result={}
    for method in ("bm25","semantic","fine_tuned"):
        vectors={}
        if method!="bm25":
            model=(AutoModel.from_pretrained(BASE,revision=REVISION) if method=="semantic"
                   else AutoModel.from_pretrained(ROOT/"runs/passage-ranker-v1")).eval()
            for i in range(0,len(texts),32):
                batch=texts[i:i+32]
                vectors.update(zip(batch,embeddings(model,tokenizer,batch),strict=True))
        hits={k:[top(r,vectors,method) for r in records] for k,records in rows.items()}
        thresholds={score for _,score in hits["train"]}
        thresholds.add(max(thresholds)+1)
        # Break exact-accuracy ties toward abstention. Do not use dev labels to set the cutoff.
        cutoff=max(thresholds,key=lambda v:(metrics(rows["train"],hits["train"],v)["exact"],v))
        result[method]=dict(cutoff=cutoff,dev=metrics(rows["dev"],hits["dev"],cutoff))
        print(method,{k:v for k,v in result[method]["dev"].items() if k!="cases"})
    positives=[r for r in rows["dev"] if r["quote"] is not None]
    output=dict(base=BASE,revision=REVISION,ranker_weights_sha256=sha256((ROOT/"runs/passage-ranker-v1/model.safetensors").read_bytes()).hexdigest(),
                source_hashes={k:sha256(p.read_bytes()).hexdigest() for k,p in files.items()},
                candidate_exact_ceiling=sum(r["quote"] in candidates(r["cv_passage"]) for r in positives),
                positive_dev=len(positives),results=result)
    (ROOT/"reports/clause-retrieval.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
