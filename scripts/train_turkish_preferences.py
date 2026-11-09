"""Test isolated Turkish preference bullets on an employer excluded from training."""
from hashlib import sha256
import json
import re

import requests
import torch
from transformers import AutoModelForSequenceClassification,AutoTokenizer
from check_crenno_sections import extract
from train_pair_encoder import BASE,REVISION,ROOT
from train_skill_sentences import metrics


def examples(index,board):
    records=[json.loads(s) for s in index.read_text("utf8").splitlines()]
    classes={}
    texts={}
    for url in sorted({r["source_url"] for r in records}):
        selected=[r for r in records if r["source_url"]==url]
        key=url.split("/")[-1]
        api=("https://api.lever.co/v0/postings/roofstacks/" if board=="roof" else
             "https://api.smartrecruiters.com/v1/companies/CRENNO/postings/")+key
        response=requests.get(api,timeout=15)
        response.raise_for_status()
        payload=response.json()
        if board=="roof":
            lines=payload["descriptionPlain"].splitlines()
            items=[(" ".join(lines[r["line"]-1].split()),r["label"]=="preference") for r in selected]
        else:
            _,expected,refs=extract(payload)
            assert selected==refs
            items=list(expected.items())
        assert {sha256(text.encode()).hexdigest() for text,_ in items}=={r["text_sha256"] for r in selected}
        for text,label in items:
            fingerprint=" ".join(text.casefold().split())
            texts[fingerprint]=text
            classes.setdefault(fingerprint,set()).add(label)
    return [(texts[k],next(iter(v))) for k,v in sorted(classes.items()) if len(v)==1]


def train_predict(train,test):
    torch.manual_seed(41)
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    model=AutoModelForSequenceClassification.from_pretrained(BASE,revision=REVISION,num_labels=2,ignore_mismatched_sizes=True)
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=4e-5)
    labels=torch.tensor([int(label) for _,label in train])
    loss=torch.nn.CrossEntropyLoss(weight=len(train)/(2*torch.bincount(labels).float()))
    def logits(texts):
        return model(**tokenizer(texts,padding=True,truncation=True,max_length=128,return_tensors="pt")).logits
    model.train()
    for _ in range(3):
        for ids in torch.randperm(len(train)).split(12):
            optimizer.zero_grad()
            loss(logits([train[i][0] for i in ids]),labels[ids]).backward()
            optimizer.step()
    model.eval()
    with torch.inference_mode():
        return [bool(v) for i in range(0,len(test),24) for v in logits([x for x,_ in test[i:i+24]]).argmax(1).tolist()]


def main():
    torch.set_num_threads(4)
    folder=ROOT/"releases/match-pilot"
    indexes={"roof":folder/"turkish_section_index.jsonl","crenno":folder/"turkish_crenno_sections.jsonl"}
    data={name:examples(path,name) for name,path in indexes.items()}
    report=dict(base=BASE,revision=REVISION,seed=41,epochs=3,
                index_sha256={name:sha256(path.read_text("utf8").encode()).hexdigest() for name,path in indexes.items()},folds={})
    for train_name,test_name in [("roof","crenno"),("crenno","roof")]:
        train=data[train_name]
        keys={" ".join(s.casefold().split()) for s,_ in train}
        test=[(s,y) for s,y in data[test_name] if " ".join(s.casefold().split()) not in keys]
        predicted=train_predict(train,test)
        cue=[bool(re.search(r"tercihen|tercih (?:sebebi|nedenidir|edilir)|artı (?:olur|sayılır|değer olarak değerlendirilir)|zorunlu değil",s,re.I)) for s,_ in test]
        truth=[y for _,y in test]
        report["folds"][test_name]=dict(train=train_name,train_size=len(train),train_optional=sum(y for _,y in train),
            test_size=len(test),test_optional=sum(truth),excluded_overlap=len(data[test_name])-len(test),
            adapted=metrics(truth,predicted),explicit_wording=metrics(truth,cue),cases=[
                dict(text_sha256=sha256(s.encode()).hexdigest(),optional=y,model=p,cue=c)
                for (s,y),p,c in zip(test,predicted,cue,strict=True)])
        print(test_name,{k:v for k,v in report["folds"][test_name].items() if k!="cases"},flush=True)
    (ROOT/"reports/turkish-preference-transfer.json").write_text(json.dumps(report,indent=2)+"\n","utf8")


if __name__=="__main__":
    main()
