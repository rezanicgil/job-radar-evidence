"""Train and evaluate an auxiliary English job sentence selector on SkillSpan."""

import hashlib
import json
from pathlib import Path

import torch
from huggingface_hub import hf_hub_download
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from train_pair_encoder import BASE, REVISION, ROOT
from market_skills import PATTERNS as CURRENT_PATTERNS

# Keep the originally evaluated dictionary fixed as the market vocabulary grows.
PATTERNS = {name:CURRENT_PATTERNS[name] for name in
            json.loads((ROOT/"data/market_vocabulary_v1.json").read_text(encoding="utf-8"))}

DATA = "jjzha/skillspan"
VERSION = "33062e6bd0e03a5e01ae299ce0518f4613ef4298"


def metrics(truth, predictions):
    tp = sum(a and b for a, b in zip(truth, predictions, strict=True))
    fp = sum(not a and b for a, b in zip(truth, predictions, strict=True))
    fn = sum(a and not b for a, b in zip(truth, predictions, strict=True))
    return dict(tp=tp, fp=fp, fn=fn, precision=tp/max(1,tp+fp),
                recall=tp/max(1,tp+fn), f1=2*tp/max(1,2*tp+fp+fn))


def main():
    torch.manual_seed(31)
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(BASE,revision=REVISION,num_labels=2,
                                                              ignore_mismatched_sizes=True)
    model.config.id2label = {0:"no_span",1:"skill_or_knowledge_span"}
    model.config.label2id = {v:k for k,v in model.config.id2label.items()}
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=4e-5)
    seen=set()
    report=dict(dataset=DATA,revision=VERSION,base=BASE,base_revision=REVISION,seed=31,
                epochs=1,max_tokens=96,batch_size=32,splits={})
    for split in ("train","dev","test"):
        path=Path(hf_hub_download(DATA,split+".json",repo_type="dataset",revision=VERSION))
        texts,labels=[],[]
        total=0
        for raw in path.read_text(encoding="utf-8").splitlines():
            row=json.loads(raw)
            total+=1
            text=" ".join(row["tokens"])
            key=" ".join(text.casefold().split())
            if key in seen:
                continue
            seen.add(key)
            texts.append(text)
            labels.append(int(any(t!="O" for t in row["tags_skill"]+row["tags_knowledge"])))
        training=split=="train"
        model.train(training)
        order=torch.randperm(len(texts)).tolist() if training else list(range(len(texts)))
        predictions=[]
        for start in range(0,len(order),32):
            ids=order[start:start+32]
            batch=tokenizer([texts[i] for i in ids],return_tensors="pt",padding=True,truncation=True,max_length=96)
            with torch.set_grad_enabled(training):
                result=model(**batch,labels=torch.tensor([labels[i] for i in ids]))
                if training:
                    optimizer.zero_grad()
                    result.loss.backward()
                    optimizer.step()
                else:
                    predictions.extend(result.logits.argmax(1).tolist())
        record=dict(source_rows=total,unique_used=len(texts),positive=sum(labels),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        if training:
            target=ROOT/"runs/skill-sentences"
            model.save_pretrained(target)
            tokenizer.save_pretrained(target)
        else:
            record["adapted"]=metrics(labels,predictions)
            record["technology_dictionary"]=metrics(labels,[any(p.search(t) for p in PATTERNS.values()) for t in texts])
        report["splits"][split]=record
        print(split,record,flush=True)
    (ROOT/"reports/skill-sentences.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
