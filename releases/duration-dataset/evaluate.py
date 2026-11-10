"""Recompute draft-label metrics from the public training split, holding out employers."""
import hashlib,json
from collections import Counter
from reproduce import ROOT,fit,torch,safe_open

def main():
    torch.set_num_threads(4)
    data=(ROOT/"train.jsonl").read_bytes();rows=[json.loads(l) for l in data.splitlines()]
    with safe_open(ROOT/"train-features.safetensors",framework="pt") as f:
        if f.metadata()["train_sha256"]!=hashlib.sha256(data).hexdigest():raise ValueError("Mismatched feature order")
        x=f.get_tensor("embeddings")
    y=torch.tensor([float(r["kind"]=="prior_experience") for r in rows])
    employers=sorted({r["employer"] for r in rows}); cm=[[0,0],[0,0]];predictions={};errors=Counter()
    for employer in employers:
        held=torch.tensor([r["employer"]==employer for r in rows])
        w,b=fit(x[~held],y[~held]);pred=(x[held]@w+b>=0).int().tolist()
        for i,p in zip(held.nonzero().flatten().tolist(),pred,strict=True):
            actual=int(y[i]);cm[actual][p]+=1;predictions[rows[i]["id"]]=p
            if actual!=p:errors[rows[i]["kind"]]+=1
    assert len(predictions)==len(rows)==len(x)
    print(json.dumps(dict(labels=["other duration","prior experience"],folds=len(employers),confusion=cm,
            balanced_accuracy=sum(cm[i][i]/sum(cm[i]) for i in (0,1))/2,errors_by_kind=errors,predictions=predictions),indent=2))
if __name__=="__main__":main()
