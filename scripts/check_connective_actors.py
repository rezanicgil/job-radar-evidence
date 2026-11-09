"""Evaluate mention matching and clause attribution with the same AND/OR requirements."""

from collections import Counter
from hashlib import sha256
import json
import re
import runpy

import torch
from train_clause_attribution import ROOT,clauses,AutoModelForSequenceClassification,AutoTokenizer,encode


def outcomes(evidenced,technologies):
    complete=set(evidenced)==set(technologies)
    return {"all":"supported" if complete else "partial" if evidenced else "unverified",
            "any":"supported" if evidenced else "unverified"}


def evaluate(rows,actor,tokenizer,direct,predictor):
    cases=[]
    for row in rows:
        technologies=row["technologies"]
        parts=clauses(row["cv_passage"])
        mentions=[t for t in technologies if re.search(r"(?<!\w)"+re.escape(t)+r"(?!\w)",row["cv_passage"],re.I)]
        credited=[]
        for tech in technologies:
            pattern=re.escape(technologies[0])+r" (?:and|ve) "+re.escape(technologies[1])
            requirement,n=re.subn(pattern,lambda m:tech,row["all"],count=1)
            assert n==1
            inputs=encode([dict(cv_passage=p,requirement=requirement) for p in parts],tokenizer)
            with torch.inference_mode():
                votes=actor(**inputs).logits.argmax(1).tolist()
            if any(actor.config.id2label[i]=="applicant" for i in votes):
                credited.append(tech)
        gold=outcomes(row["evidenced"],technologies)
        assert all(row[k+"_label"]==gold[k] for k in gold)
        direct_labels={k:predictor(row["cv_passage"],row[k],*direct)["prediction"] for k in gold}
        cases.append(dict(family=row["family"],passage_sha256=sha256(row["cv_passage"].encode()).hexdigest(),
                          expected=gold,mentions=outcomes(mentions,technologies),actor=outcomes(credited,technologies),
                          direct=direct_labels,credited=credited))
    summary={}
    for method in ("direct","mentions","actor"):
        pairs=Counter((c["expected"][k],c[method][k]) for c in cases for k in ("all","any"))
        changes=[c for c in cases if c["expected"]["all"]!=c["expected"]["any"]]
        summary[method]=dict(correct=sum(n for (a,b),n in pairs.items() if a==b),total=sum(pairs.values()),
              false_full=sum(n for (a,b),n in pairs.items() if a!="supported" and b=="supported"),
              nonfull_targets=sum(n for (a,_),n in pairs.items() if a!="supported"),
              both_correct_on_switch=sum(c["expected"]==c[method] for c in changes),should_switch=len(changes))
    return dict(summary=summary,cases=cases)


def main():
    torch.set_num_threads(4)
    release=runpy.run_path(str(ROOT/"releases/mentions-v3/predict.py"))
    direct=release["load_research_model"](False)
    checkpoint=ROOT/"runs/pair-clause-attribution"
    actor=AutoModelForSequenceClassification.from_pretrained(checkpoint).eval()
    tokenizer=AutoTokenizer.from_pretrained(checkpoint)
    result=dict(classifier_revision=release["REV"],actor_weights_sha256=sha256((checkpoint/"model.safetensors").read_bytes()).hexdigest(),splits={})
    for name in ("technology_connectives","connective_actors"):
        path=ROOT/"releases/match-pilot"/(name+".jsonl")
        rows=[json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
        result["splits"][name]=dict(source_sha256=sha256(path.read_bytes()).hexdigest(),
            **evaluate(rows,actor,tokenizer,direct,release["predict"]))
        print(name,result["splits"][name]["summary"],flush=True)
    (ROOT/"reports/connective-actors.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
