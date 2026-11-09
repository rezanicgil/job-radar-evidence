"""Adapt the SkillSpan encoder on frozen section-derived training labels."""
import json
import re
from hashlib import sha256
from html import unescape

import requests
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from train_section_selector import INDEX,STATS,ROOT,normalized,reference_splits,metrics


def main():
    torch.set_num_threads(4)
    torch.manual_seed(31)
    source=ROOT/"runs/english-posting-sections.json"
    rows=[json.loads(s) for s in INDEX.read_text("utf8").splitlines()]
    bodies=[]
    if source.exists():
        assert sha256(source.read_bytes()).hexdigest()==json.loads(STATS.read_text("utf8"))["source_cache_sha256"]
        bodies=[body for _,_,_,body in json.loads(source.read_text("utf8"))]
    else:
        for url in sorted({r["url"] for r in rows}):
            board,key=url.split("/")[-2:]
            response=requests.get(f"https://api.lever.co/v0/postings/{board}/{key}",timeout=15)
            response.raise_for_status()
            bodies.extend(section["content"] for section in response.json()["lists"])
    bullets={}
    for body in bodies:
        for item in re.findall(r"<li\b[^>]*>(.*?)</li>",body,re.I|re.S):
            text=" ".join(unescape(re.sub("<[^>]+>"," ",item)).split())
            bullets[sha256(normalized(text).encode()).hexdigest()]=text
    missing={r["text_sha256"] for r in rows}-bullets.keys()
    if missing:
        raise ValueError(f"Could not reconstruct {len(missing)} indexed bullets from employer text")
    examples=[(bullets[r["text_sha256"]],r["weak_label"]) for r in rows]
    splits,_,excluded=reference_splits()
    assert not {normalized(s) for s,_ in examples}&excluded
    checkpoint=ROOT/"runs/skill-sentences"
    tokenizer=AutoTokenizer.from_pretrained(checkpoint)
    model=AutoModelForSequenceClassification.from_pretrained(checkpoint)
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    opt=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=4e-5)
    counts=torch.bincount(torch.tensor([y for _,y in examples]),minlength=2)
    loss=torch.nn.CrossEntropyLoss(weight=counts.sum()/(2*counts.float()))
    def logits(texts):
        return model(**tokenizer(texts,padding=True,truncation=True,max_length=96,return_tensors="pt")).logits
    model.train()
    for ids in torch.randperm(len(examples)).split(24):
        batch=[examples[i] for i in ids.tolist()]
        opt.zero_grad()
        loss(logits([s for s,_ in batch]),torch.tensor([y for _,y in batch])).backward()
        opt.step()
    out=ROOT/"runs/skill-section-adapted"
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)
    model.eval()
    test=splits["test"]
    with torch.inference_mode():
        pred=[y for i in range(0,len(test),32) for y in logits([s for s,_ in test[i:i+32]]).argmax(1).tolist()]
    report=dict(training_index_sha256=sha256(INDEX.read_text("utf8").encode()).hexdigest(),
                seed=31,epochs=1,training_class_counts=counts.tolist(),skillspan_test=metrics([y for _,y in test],pred))
    (ROOT/"reports/skill-section-adaptation.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(report)


if __name__=="__main__":
    main()
