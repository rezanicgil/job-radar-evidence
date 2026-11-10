"""Rebuild the published duration classifier from this directory alone."""
import hashlib,json
from pathlib import Path
import torch
from safetensors import safe_open
from safetensors.torch import save_file
ROOT=Path(__file__).resolve().parent

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

if __name__=="__main__":
    torch.set_num_threads(4)
    train=(ROOT/"train.jsonl").read_bytes()
    with safe_open(ROOT/"train-features.safetensors",framework="pt") as f:
        if f.metadata()["train_sha256"]!=hashlib.sha256(train).hexdigest():
            raise ValueError("Training labels or row order differ from the stored features")
        x=f.get_tensor("embeddings")
    y=torch.tensor([float(json.loads(line)["kind"]=="prior_experience") for line in train.splitlines()])
    assert x.shape==(len(y),384)
    w,b=fit(x,y)
    save_file({"weight":w,"bias":b},str(ROOT/"reproduced-head.safetensors"))
    print("Rebuilt head using",len(y),"duration contexts.")
