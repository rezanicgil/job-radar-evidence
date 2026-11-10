"""Fit a class-balanced linear head on frozen multilingual duration-context embeddings."""
import json
import torch
from transformers import AutoTokenizer,AutoModel
from evaluate_pooled_retrieval import embeddings
from evaluate_duration_training_baseline import ROOT,checked,read,features
from train_smoke import BASE,REVISION

def fit(x,y):
    # Zero initialization and fixed optimization, independent of held-out scores.
    w=torch.zeros(x.shape[1],requires_grad=True); b=torch.zeros((),requires_grad=True)
    opt=torch.optim.LBFGS([w,b],max_iter=60,line_search_fn="strong_wolfe")
    weight=torch.where(y==1,0.5/y.sum(),0.5/(1-y).sum())
    def step():
        opt.zero_grad()
        loss=torch.nn.functional.binary_cross_entropy_with_logits(x@w+b,y,weight=weight,reduction="sum")+0.005*w.square().sum()
        loss.backward();return loss
    opt.step(step)
    return w.detach(),b.detach()

def main():
    torch.set_num_threads(4)
    meta=json.loads((ROOT/"reports/duration-augmentation.json").read_text())
    rows=checked(ROOT/"data/interim/duration-training-augmented.jsonl",meta["sha256"])
    splits=json.loads((ROOT/"research/duration-splits-20261110.json").read_text())
    names={r["source"]:r["employer"] for s in splits["snapshots"] for r in read(ROOT/"data/raw"/s/"candidates.jsonl")}
    names.update({r["source"]:r["employer"] for r in read(ROOT/"research/auxiliary-duration-contexts-20261110.jsonl")})
    employers=[names[r["source"]] for r in rows]
    texts=[" ".join(features(r)) for r in rows]
    enc=AutoModel.from_pretrained(BASE,revision=REVISION).eval(); tok=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    x=torch.cat([embeddings(enc,tok,texts[i:i+16]) for i in range(0,len(texts),16)])
    y=torch.tensor([float(r["kind"]=="prior_experience") for r in rows])
    records=[];cm=[[0,0],[0,0]]
    for employer in sorted(set(employers)):
        hold=torch.tensor([e==employer for e in employers])
        w,b=fit(x[~hold],y[~hold]);scores=x[hold]@w+b
        for i,score in zip(hold.nonzero().flatten().tolist(),scores.tolist(),strict=True):
            actual=int(y[i]);pred=int(score>=0);cm[actual][pred]+=1
            records.append(dict(id=rows[i]["id"],employer=employer,actual=actual,predicted=pred))
    w,b=fit(x,y);dest=ROOT/"runs/duration-context-head";dest.mkdir(exist_ok=True)
    torch.save(dict(weight=w,bias=b,encoder=BASE,revision=REVISION),dest/"head.pt")
    report=dict(encoder=BASE,revision=REVISION,training_sha256=meta["sha256"],labels=["other duration","prior experience"],confusion=cm,
                balanced_accuracy=sum(cm[i][i]/sum(cm[i]) for i in (0,1))/2,folds=len(set(employers)),predictions=records)
    (ROOT/"reports/duration-context-head.json").write_text(json.dumps(report,indent=2)+"\n","utf8");print(cm,report["balanced_accuracy"],report["folds"])

if __name__=="__main__":main()
