"""Rank three fictional passages for each sourced condition in both language directions."""
import argparse
from hashlib import sha256
import json
from train_clause_attribution import clauses, encode, AutoModelForSequenceClassification

import torch
from evaluate_pooled_retrieval import BASE, REVISION, ROOT, embeddings, AutoModel, AutoTokenizer


def main():
    torch.set_num_threads(4)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",choices=["cross_language_attribution","git_evidence_transfer"],default="cross_language_attribution")
    name=parser.parse_args().dataset
    dataset=ROOT/"releases/match-pilot"/(name+".jsonl")
    output=ROOT/"reports"/(name.replace("_","-")+".json")
    rows=[json.loads(line) for line in dataset.read_text(encoding="utf8").splitlines()]
    families=sorted({r["family"] for r in rows})
    report=dict(source_sha256=sha256(dataset.read_bytes()).hexdigest(),checkpoints={},methods={})
    for name,checkpoint,revision in [("base",BASE,REVISION),("fine_tuned","rezanicgil/python-tr-en-retriever","813078062d92ba7d57487fd97b14af3acd620522"),
                                     ("attribution","rezanicgil/job-radar-clause-attribution","c818969bb437370febedbfe2f5a80adac976d331")]:
        report["checkpoints"][name]=dict(repo=checkpoint,revision=revision)
        loader=AutoModelForSequenceClassification if name=="attribution" else AutoModel
        model=loader.from_pretrained(checkpoint,revision=revision).eval()
        tokenizer=AutoTokenizer.from_pretrained(checkpoint,revision=revision)
        views={}
        for job,cv in [("en","tr"),("tr","en"),("en","en"),("tr","tr")]:
            cases={}
            for family in families:
                options=sorted((r for r in rows if r["family"]==family),
                               key=lambda r:sha256(r["cv_"+cv].encode()).digest())
                assert sorted(r["category"] for r in options)==["adjacent_or_future","other_actor","target"]
                req=options[0]["requirement_"+job]
                if name=="attribution":
                    scores=[]
                    for row in options:
                        batch=[dict(requirement=req,cv_passage=c) for c in clauses(row["cv_"+cv])]
                        with torch.inference_mode():
                            logits=model(**encode(batch,tokenizer)).logits
                            scores.append(logits.softmax(-1)[:,model.config.label2id["applicant"]].max())
                    scores=torch.stack(scores)
                else:
                    vectors=embeddings(model,tokenizer,[req]+[r["cv_"+cv] for r in options])
                    scores=vectors[1:]@vectors[0]
                ranking=scores.argsort(descending=True).tolist()
                ordered=[options[i]["category"] for i in ranking]
                cases[family]=dict(order=ordered,target_rank=1+ordered.index("target"))
            ranks=[v["target_rank"] for v in cases.values()]
            views[job+"-"+cv]=dict(target_first=ranks.count(1),target_last=ranks.count(3),total=len(ranks),cases=cases)
        report["methods"][name]=views
    output.write_text(json.dumps(report,indent=2)+"\n","utf8")
    for name,views in report["methods"].items():
        print(name,{lang:(row["target_first"],row["target_last"]) for lang,row in views.items()})


if __name__=="__main__":
    main()
