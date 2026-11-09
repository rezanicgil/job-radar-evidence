"""Adapt the released tagger with generated Turkish conditions and English training replay."""
from hashlib import sha256
import json
import random
import re

import torch
from transformers import AutoTokenizer,AutoModelForTokenClassification
from train_knowledge_spans import read_splits,ROOT,prepare,batch_inputs,evaluate,BATCH
from check_turkish_technology_mentions import VOCABULARY,mentions,MODELS

SEED=73


def augmentation():
    ordered=sorted(VOCABULARY,key=lambda s:sha256(s.encode()).digest())
    training=ordered[:40]
    templates=["{a} kullanarak üretim sorunlarını araştırabilmek.",
               "Adayın {a} konusunda deneyimli olması beklenir.",
               "Ekip içinde {a} ile geliştirme yapmış olmak tercih sebebidir.",
               "{a} ve {b} ile çalışan servislerin bakımını üstlenmek.",
               "{b} bilgisinin yanı sıra {a} kullanımına aşina olmak."]
    records=[]
    for i,a in enumerate(training):
        for j,template in enumerate(templates):
            b=training[(i+1+j)%len(training)]
            text=template.format(a=a,b=b)
            records.append(dict(text=text,template=j,mentions=mentions(text),origin="authored_template"))
    return records,training,ordered[40:]


def training_row(row):
    parts=list(re.finditer(r"\w+(?:\+\+|#)?|[^\w\s]",row["text"]))
    labels=["O"]*len(parts)
    for span in row["mentions"]:
        inside=[i for i,m in enumerate(parts) if m.start()>=span["start"] and m.end()<=span["end"]]
        assert inside and parts[inside[0]].start()==span["start"] and parts[inside[-1]].end()==span["end"]
        for j,i in enumerate(inside):labels[i]="I" if j else "B"
    return [m.group() for m in parts],labels


def main():
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    records,included,excluded=augmentation()
    path=ROOT/"releases/match-pilot/turkish_mention_training.jsonl"
    path.write_bytes("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records).encode())
    heldout={json.loads(line)["text_sha256"] for line in (ROOT/"releases/match-pilot/turkish_technology_mentions.jsonl").read_text("utf8").splitlines()}
    assert not {sha256(r["text"].encode()).hexdigest() for r in records}&heldout
    source,rev=MODELS["Job Radar"]
    tokenizer=AutoTokenizer.from_pretrained(source,revision=rev)
    model=AutoModelForTokenClassification.from_pretrained(source,revision=rev)
    data,_=read_splits()
    replay=random.Random(SEED).sample(data["train"],2*len(records))
    chunks=prepare(tokenizer,[training_row(r) for r in records]+replay)
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=2e-5)
    model.train()
    for ids in torch.randperm(len(chunks)).split(BATCH):
        inp,tags=batch_inputs([chunks[i] for i in ids.tolist()],tokenizer.pad_token_id)
        optimizer.zero_grad()
        model(**inp,labels=tags).loss.backward()
        optimizer.step()
    dest=ROOT/"runs/turkish-mention-adapted";model.save_pretrained(dest);tokenizer.save_pretrained(dest)
    metrics=evaluate(model,data["test"],prepare(tokenizer,data["test"]),tokenizer.pad_token_id)
    report=dict(base=source,revision=rev,seed=SEED,epochs=1,learning_rate=2e-5,synthetic=len(records),
                replay=len(replay),template_technologies=included,other_technologies=excluded,
                train_index_sha256=sha256(path.read_bytes()).hexdigest(),skillspan_test=metrics)
    (ROOT/"reports/turkish-mention-adaptation.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(metrics)


if __name__=="__main__":
    main()
