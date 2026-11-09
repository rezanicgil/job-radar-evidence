"""Extract a passage substring or abstain on the bilingual actor diagnostic."""

import hashlib
import json
import random
from collections import Counter

import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer
from train_pair_encoder import BASE, REVISION, ROOT


def prepare(tokenizer,rows):
    batch=tokenizer([r["component"] for r in rows],[r["cv_passage"] for r in rows],
                    padding=True,return_offsets_mapping=True,return_tensors="pt")
    offsets=batch.pop("offset_mapping").tolist()
    answers=[]
    spans=[]
    for i,row in enumerate(rows):
        context=[(k,a,b) for k,(a,b) in enumerate(offsets[i]) if batch.sequence_ids(i)[k]==1 and a<b]
        spans.append(context)
        if row["quote"] is None:
            answers.append((0,0))
        else:
            start,end=row["start"],row["end"]
            assert row["cv_passage"][start:end]==row["quote"]
            included=[k for k,a,b in context if b>start and a<end]
            if not included:raise ValueError("Quote has no passage tokens")
            answers.append((included[0],included[-1]))
    return dict(batch),spans,torch.tensor(answers)


def decode(starts,ends,context,text):
    best=(float("-inf"),None)
    for i,(left,begin,_) in enumerate(context):
        for right,_,finish in context[i:]:
            score=starts[left]+ends[right]
            if score>best[0]:
                best=(score,text[begin:finish].strip())
    return (best[1] if best[0]>starts[0]+ends[0] else None), best[1]


def measure(rows,predictions):
    counts=Counter()
    cases=[]
    for r,pred in zip(rows,predictions,strict=True):
        correct=pred==r["quote"]
        counts["exact"]+=correct
        counts["correct_null"]+=correct and pred is None
        counts["returned_on_null"]+=r["quote"] is None and pred is not None
        counts["missed_quote"]+=r["quote"] is not None and pred is None
        if r["quote"] is not None:
            counts["exact_"+r["actor"]]+=correct
        cases.append(dict(family=r["family"],component=r["component"],gold=r["quote"],predicted=pred))
    return dict(total=len(rows),counts=counts,cases=cases)


def main():
    torch.set_num_threads(4)
    torch.manual_seed(17)
    files={k:ROOT/"data"/f"actor_evidence_{k}.jsonl" for k in ("train","dev")}
    rows={k:[json.loads(s) for s in f.read_text(encoding="utf-8").splitlines()] for k,f in files.items()}
    assert {r["family"] for r in rows["train"]}.isdisjoint(r["family"] for r in rows["dev"])
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    model=AutoModelForQuestionAnswering.from_pretrained(BASE,revision=REVISION,num_labels=2)
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=5e-5)
    prepared={k:prepare(tokenizer,v) for k,v in rows.items()}
    inputs,_,targets=prepared["train"]
    order=list(range(len(targets)))
    shuffle=random.Random(17)
    model.train()
    for _ in range(6):
        shuffle.shuffle(order)
        for i in range(0,len(order),6):
            idx=order[i:i+6]
            loss=model(**{k:v[idx] for k,v in inputs.items()},
                       start_positions=targets[idx,0],end_positions=targets[idx,1]).loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    model.eval()
    dest=ROOT/"runs/actor-spans"
    model.save_pretrained(dest);tokenizer.save_pretrained(dest)
    report=dict(base=BASE,revision=REVISION,seed=17,epochs=6,batch_size=6,learning_rate=5e-5,
                sha256={k:hashlib.sha256(f.read_bytes()).hexdigest() for k,f in files.items()},splits={})
    for name,(encoded,contexts,_) in prepared.items():
        with torch.no_grad():
            out=model(**encoded)
        decoded=[decode(s,e,c,r["cv_passage"]) for s,e,c,r in
                 zip(out.start_logits.tolist(),out.end_logits.tolist(),contexts,rows[name],strict=True)]
        report["splits"][name]=measure(rows[name],[choice for choice,_ in decoded])
        positive=[(r,p) for r,(_,p) in zip(rows[name],decoded,strict=True) if r["quote"] is not None]
        report["splits"][name]["when_gold_present_force_answer"]=dict(total=len(positive),
            exact=sum(r["quote"]==p for r,p in positive))
        print(name,report["splits"][name]["counts"])
    (ROOT/"reports/actor-spans.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
