"""Compare raw action and actor-specific hypotheses using the unchanged upstream NLI head."""

from collections import Counter
from hashlib import sha256
import json

import torch
from train_pair_encoder import BASE, REVISION, ROOT, AutoModelForSequenceClassification, AutoTokenizer


def main():
    torch.set_num_threads(4)
    dev=ROOT/"data/actor_evidence_dev.jsonl"
    prompts=ROOT/"research/actor_hypotheses.jsonl"
    rows=[json.loads(s) for s in dev.read_text(encoding="utf-8").splitlines()]
    hypotheses={r["component"]:r for r in map(json.loads,prompts.read_text(encoding="utf-8").splitlines())}
    assert hypotheses.keys()=={r["component"] for r in rows}
    model=AutoModelForSequenceClassification.from_pretrained(BASE,revision=REVISION).eval()
    tok=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    pairs=[(r["cv_passage"],hypotheses[r["component"]][key]) for r in rows for key in ("component","applicant","other")]
    results=[]
    with torch.inference_mode():
        for i in range(0,len(pairs),16):
            passages,claims=zip(*pairs[i:i+16])
            inputs=tok(list(passages),list(claims),return_tensors="pt",padding=True,truncation=True,max_length=128)
            results.extend(model.config.id2label[j] for j in model(**inputs).logits.argmax(-1).tolist())
    cases=[]
    for i,r in enumerate(rows):
        raw,app,other=results[3*i:3*i+3]
        inferred={ (False,False):"not_stated",(True,False):"applicant",(False,True):"other",(True,True):"ambiguous" }[
            (app=="entailment",other=="entailment")]
        cases.append(dict(family=r["family"],component=r["component"],actual=r["actor"],
                          raw=raw,applicant=app,other=other,inferred=inferred))
    metrics={}
    for name in ("raw","applicant","inferred"):
        count=Counter()
        for case in cases:
            claims=case["inferred"]=="applicant" if name=="inferred" else case[name]=="entailment"
            count["correct_applicant" if case["actual"]=="applicant" else "false_applicant"]+=int(claims)
        metrics[name]=dict(count)
    confusion=Counter((r["actual"],r["inferred"]) for r in cases)
    matrix={a:{b:confusion[a,b] for b in ("applicant","other","not_stated","ambiguous")}
            for a in ("applicant","other","not_stated")}
    report=dict(base=BASE,revision=REVISION,dev_sha256=sha256(dev.read_bytes()).hexdigest(),
                prompts_sha256=sha256(prompts.read_bytes()).hexdigest(),metrics=metrics,actual_by_inferred=matrix,cases=cases)
    (ROOT/"reports/actor-entailment.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(metrics,matrix)


if __name__=="__main__":
    main()
