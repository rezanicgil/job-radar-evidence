"""Compare the quantized browser weights to the released float encoder on identical inputs."""

from pathlib import Path
import json
from hashlib import sha256

import numpy as np
import onnxruntime as ort
import torch
from transformers import AutoModel, AutoTokenizer

from evaluate_pooled_retrieval import embeddings,ROOT
from review_cv import ENCODERS


def main():
    path=ROOT/"runs/browser-retriever/onnx/model_quantized.onnx"
    repo,rev=ENCODERS["fine-tuned"]
    tokenizer=AutoTokenizer.from_pretrained(repo,revision=rev)
    model=AutoModel.from_pretrained(repo,revision=rev).eval()
    opts=ort.SessionOptions()
    opts.intra_op_num_threads=4
    torch.set_num_threads(4)
    session=ort.InferenceSession(str(path),sess_options=opts,providers=["CPUExecutionProvider"])
    source=ROOT/"releases/match-pilot/language_switch.jsonl"
    rows=[json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    report=dict(model=repo,float_revision=rev,onnx_sha256=sha256(path.read_bytes()).hexdigest(),
                corpus_sha256=sha256(source.read_bytes()).hexdigest(),views={})
    for view in ("tr-tr","tr-en","en-tr","en-en"):
        pool=sorted((r for r in rows if f"{r['job_language']}-{r['cv_language']}"==view),
                    key=lambda r:sha256(r["cv_passage"].encode()).digest())
        targets=[i for i,r in enumerate(pool) if r["label"]=="supported"]
        texts=[pool[i]["requirement"] for i in targets]+[r["cv_passage"] for r in pool]
        quantized=[]
        baseline=[]
        for start in range(0,len(texts),8):
            batch=texts[start:start+8]
            tokens=tokenizer(batch,return_tensors="np",truncation=True,max_length=128,padding=True)
            hidden=session.run(["last_hidden_state"],dict(tokens))[0]
            mask=tokens.attention_mask[:,:,None]
            vec=(hidden*mask).sum(1)/mask.sum(1)
            quantized.extend(vec/np.linalg.norm(vec,axis=1,keepdims=True))
            baseline.extend(embeddings(model,tokenizer,batch).numpy())
        base=np.array(baseline)
        quant=np.array(quantized)
        cases={}
        for key,vec in [("float",base),("quantized",quant)]:
            n=len(targets)
            rankings=np.argsort(-(vec[:n]@vec[n:].T),axis=1)
            for i,order in zip(targets,rankings,strict=True):
                cases.setdefault(pool[i]["family"],{})[key]=order.tolist().index(i)+1
        report["views"][view]=dict(mean_embedding_cosine=float((base*quant).sum(1).mean()),ranks=cases)
        print(view,sum(c["float"]<=3 for c in cases.values()),sum(c["quantized"]<=3 for c in cases.values()))
    (ROOT/"reports/browser-encoder.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
