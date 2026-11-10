"""Fixed last-block adaptation from the published duration head; exploratory comparison."""
import json,runpy,re
import torch
from transformers import AutoModel,AutoTokenizer
from safetensors.torch import load_file,save_file
from huggingface_hub import snapshot_download
from evaluate_duration_training_baseline import ROOT,checked,features
from evaluate_job_ner_experience import REPO,REV,pq,hf_hub_download
from probe_experience_context import CASES
from pathlib import Path

def main():
    torch.manual_seed(42);torch.set_num_threads(4)
    revision="ed338d59d26219b6574245aaf9488cda4dc3c5e9"
    snap=Path(snapshot_download("rezanicgil/job-radar-duration-context",revision=revision))
    mod=runpy.run_path(str(snap/"predict.py"));tok=AutoTokenizer.from_pretrained(mod["BASE"],revision=mod["REV"])
    enc=AutoModel.from_pretrained(mod["BASE"],revision=mod["REV"])
    enc.requires_grad_(False);enc.encoder.layer[-1].requires_grad_(True)
    head=load_file(str(snap/"head.safetensors"));w=torch.nn.Parameter(head["weight"]);b=torch.nn.Parameter(head["bias"])
    def logits(texts):
        batch=tok(texts,padding=True,truncation=True,max_length=128,return_tensors="pt");mask=batch.attention_mask.unsqueeze(-1)
        x=torch.nn.functional.normalize((enc(**batch).last_hidden_state*mask).sum(1)/mask.sum(1))
        return x@w+b
    meta=json.loads((ROOT/"reports/duration-augmentation.json").read_text())
    rows=checked(ROOT/"data/interim/duration-training-augmented.jsonl",meta["sha256"])
    texts=[" ".join(features(r)) for r in rows];y=torch.tensor([float(r["kind"]=="prior_experience") for r in rows])
    opt=torch.optim.AdamW([*enc.encoder.layer[-1].parameters(),w,b],lr=2e-5)
    for epoch in range(3):
        enc.train()
        for ix in torch.randperm(len(rows)).split(12):
            out=logits([texts[i] for i in ix]);loss=torch.nn.functional.binary_cross_entropy_with_logits(out,y[ix],weight=torch.where(y[ix]>0,1.,4.))
            opt.zero_grad();loss.backward();opt.step()
    enc.eval();dest=ROOT/"runs/duration-adapted";dest.mkdir(exist_ok=True)
    save_file({**{"last."+k:v for k,v in enc.encoder.layer[-1].state_dict().items()},"weight":w.detach(),"bias":b.detach()},str(dest/"delta.safetensors"))
    ext=json.loads((ROOT/"reports/duration-implicit-external.json").read_text())["cases"]
    source=pq.read_table(hf_hub_download(REPO,"data/train-00000-of-00001.parquet",repo_type="dataset",revision=REV)).to_pylist()
    cases=[]
    for r in ext:
        t=" ".join(source[r["row_index"]]["tokens"]);m=re.search(r"\b(?:\d+|two) years?\b",t,re.I)
        cases.append(("external",str(r["row_index"]),t[:m.start()]+"["+m.group()+"]"+t[m.end():],r["expected"]=="prior experience"))
    for family,lang,pos,neg in CASES:cases.extend([(lang,family,pos,True),(lang,family,neg,False)])
    with torch.inference_mode():pred=(logits([mod["context"](c[2]) for c in cases])>=0).tolist()
    results=[dict(slice=g,case=k,actual=a,predicted=p) for (g,k,_,a),p in zip(cases,pred,strict=True)]
    summary={g:[sum(r["actual"]==r["predicted"] for r in results if r["slice"]==g),sum(r["slice"]==g for r in results)] for g in ("external","en","tr")}
    report=dict(parent=revision,training_sha256=meta["sha256"],epochs=3,seed=42,summary=summary,cases=results)
    (ROOT/"reports/duration-adapted.json").write_text(json.dumps(report,indent=2)+"\n","utf8");print(summary)

if __name__=="__main__":main()
