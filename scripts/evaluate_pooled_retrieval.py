"""Find each authored supporting passage among all source-development passages."""

from collections import Counter
from hashlib import sha256
import json
import math
import re

import torch
from transformers import AutoModel, AutoTokenizer
from train_smoke import BASE, REVISION, ROOT


def terms(text):
    return re.findall(r"[\w+#]+",text.casefold())


def bm25(query,documents):
    frequencies=Counter(word for doc in documents for word in set(doc))
    average=sum(map(len,documents))/len(documents)
    scores=[]
    for doc in documents:
        counts=Counter(doc)
        score=0.0
        for word in set(terms(query)):
            tf=counts[word]
            if tf:
                idf=math.log1p((len(documents)-frequencies[word]+0.5)/(frequencies[word]+0.5))
                score+=idf*tf*2.2/(tf+1.2*(0.25+0.75*len(doc)/average))
        scores.append(score)
    return scores


def embeddings(model,tokenizer,texts):
    inputs=tokenizer(texts,padding=True,truncation=True,max_length=128,return_tensors="pt")
    with torch.inference_mode():
        mask=inputs.attention_mask.unsqueeze(-1)
        pooled=(model(**inputs).last_hidden_state*mask).sum(1)/mask.sum(1)
        return torch.nn.functional.normalize(pooled)


def order(scores):
    return sorted(range(len(scores)),key=lambda i:-scores[i])


def main():
    torch.set_num_threads(4)
    path=ROOT/"data/match_source_dev.jsonl"
    rows=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows.sort(key=lambda row:sha256(row["cv_passage"].encode()).digest())
    passages=[row["cv_passage"] for row in rows]
    assert len(set(passages))==len(passages)
    targets=[i for i,row in enumerate(rows) if row["label"]=="supported"]
    queries=[rows[i]["requirement"] for i in targets]
    assert len(set(queries))==len(queries)
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    docs=list(map(terms,passages))
    rankings={"bm25":[bm25(q,docs) for q in queries]}
    checkpoints={"semantic":(BASE,REVISION),"fine_tuned":(ROOT/"runs/passage-ranker-v1",None)}
    for name,(source,revision) in checkpoints.items():
        model=AutoModel.from_pretrained(source,revision=revision).eval()
        vectors=embeddings(model,tokenizer,queries+passages)
        rankings[name]=(vectors[:len(queries)]@vectors[len(queries):].T).tolist()
        fused=[]
        for dense,lexical in zip(rankings[name],rankings["bm25"],strict=True):
            scores=[0.0]*len(rows)
            for rank,i in enumerate(order(dense),1):
                scores[i]+=1/(60+rank)
            for rank,i in enumerate(order(lexical),1):
                if lexical[i]>0:scores[i]+=1/(60+rank)
            fused.append(scores)
        rankings[name+"_bm25"]=fused
    result={}
    for name,queries_scores in rankings.items():
        cases={}
        for target,scores in zip(targets,queries_scores,strict=True):
            ranked=order(scores)
            if name=="bm25":ranked=[i for i in ranked if scores[i]>0]
            position=ranked.index(target)+1 if target in ranked else None
            cases[rows[target]["family"]]=dict(target_rank=position,top_three=[
                dict(family=rows[i]["family"],label_for_own_family=rows[i]["label"]) for i in ranked[:3]])
        positions=[r["target_rank"] for r in cases.values()]
        summary=dict(first=positions.count(1),in_first_three=sum(v is not None and v<=3 for v in positions),
                     mrr=sum(1/v for v in positions if v)/len(positions))
        result[name]=dict(summary=summary,cases=cases)
        print(name,summary)
    report=dict(source_sha256=sha256(path.read_bytes()).hexdigest(),base=BASE,revision=REVISION,
                queries=len(queries),pool=len(rows),rrf_k=60,
                interpretation="Rank of the authored positive. Other-family relevance is unjudged.",results=result)
    (ROOT/"reports/pooled-retrieval.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
