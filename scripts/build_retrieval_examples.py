"""Record the displayed top three passages and verify target ranks against the evaluation."""

from hashlib import sha256
import json

import torch
from transformers import AutoModel,AutoTokenizer
from evaluate_pooled_retrieval import BASE,REVISION,ROOT,embeddings


def main():
    rows=[json.loads(line) for line in (ROOT/"releases/match-pilot/language_switch.jsonl").read_text(encoding="utf-8").splitlines()]
    reference=json.loads((ROOT/"reports/translation-retrieval.json").read_text(encoding="utf-8"))
    result={}
    torch.set_num_threads(4)
    for stage,checkpoint,revision in [("before",BASE,REVISION),("after",ROOT/"runs/python-tr-retriever",None)]:
        tokenizer=AutoTokenizer.from_pretrained(checkpoint,revision=revision)
        model=AutoModel.from_pretrained(checkpoint,revision=revision).eval()
        for lang,expected in reference[stage]["cv_language_views"].items():
            job,cv=lang.split("-")
            pool=sorted((r for r in rows if r["job_language"]==job and r["cv_language"]==cv),
                        key=lambda r:sha256(r["cv_passage"].encode()).digest())
            vectors=torch.cat([embeddings(model,tokenizer,[r["cv_passage"] for r in pool[i:i+24]])
                               for i in range(0,len(pool),24)])
            targets=[i for i,r in enumerate(pool) if r["label"]=="supported"]
            queries=embeddings(model,tokenizer,[pool[i]["requirement"] for i in targets])
            for i,order in zip(targets,(queries@vectors.T).argsort(descending=True).tolist(),strict=True):
                row=pool[i]
                rank=order.index(i)+1
                assert rank==expected["ranks"][row["family"]]
                case=result.setdefault(row["family"],{}).setdefault(lang,dict(
                    requirement=row["requirement"],target=row["cv_passage"],source=row["source_url"]))
                case[stage]=dict(rank=rank,top3=[pool[j]["cv_passage"] for j in order[:3]])
    (ROOT/"releases/static-space/retrieval-examples.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(sum(map(len,result.values())),"paired comparisons")


if __name__=="__main__":
    main()
