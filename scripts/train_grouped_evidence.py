"""Compare matched-family batches with and without an ordinal loss."""

from collections import defaultdict
import hashlib
import json
import random

import torch
import torch.nn.functional as F
from train_pair_encoder import BASE, REVISION, LABELS, ROOT, AutoModelForSequenceClassification, AutoTokenizer, encode

ORDER = ["unverified", "partial", "supported"]


def train(groups, tokenizer, margin_weight):
    torch.manual_seed(17)
    shuffle = random.Random(17)
    model = AutoModelForSequenceClassification.from_pretrained(BASE, revision=REVISION)
    model._init_weights(model.classifier.out_proj)
    model.config.id2label = dict(enumerate(LABELS))
    model.config.label2id = {name:i for i,name in enumerate(LABELS)}
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=5e-5)
    order = list(groups)
    model.train()
    for _ in range(6):
        shuffle.shuffle(order)
        for start in range(0,len(order),2):
            rows = [groups[g][label] for g in order[start:start+2] for label in ORDER]
            logits = model(**encode(rows,tokenizer)).logits
            targets = torch.tensor([LABELS.index(r["label"]) for r in rows])
            probs = logits.softmax(-1)
            strength = (probs[:,LABELS.index("supported")]-probs[:,LABELS.index("unverified")]).reshape(-1,3)
            loss = F.cross_entropy(logits, targets) + margin_weight*F.relu(0.25-strength.diff(dim=1)).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    return model.eval()


def measure(model,tokenizer,rows):
    with torch.inference_mode():
        pred = [LABELS[i] for i in model(**encode(rows,tokenizer)).logits.argmax(-1).tolist()]
    pairs = [(r["label"],p) for r,p in zip(rows,pred,strict=True)]
    return dict(correct=sum(a==p for a,p in pairs), count=len(pairs),
                partial_found=pairs.count(("partial","partial")),
                false_support=sum(a!="supported" and p=="supported" for a,p in pairs),
                predictions=pred)


def main():
    torch.set_num_threads(4)
    tokenizer=AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    files = {k:ROOT/"releases/match-pilot"/(k+".jsonl") for k in ("train","validation","source_validation")}
    rows={k:[json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()] for k,p in files.items()}
    groups=defaultdict(dict)
    for r in rows["train"]:
        groups[r["family"]][r["label"]]=r
    assert all(set(group)==set(ORDER) for group in groups.values())
    for split in ("validation","source_validation"):
        assert set(groups).isdisjoint(r["family"] for r in rows[split])
    report=dict(base=BASE,revision=REVISION,seed=17,epochs=6,margin=0.25,learning_rate=5e-5,
                file_hashes={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()},results={})
    for name,weight in (("grouped_ce",0),("grouped_ordinal",1)):
        model=train(groups,tokenizer,weight)
        report["results"][name]={split:measure(model,tokenizer,rows[split]) for split in ("validation","source_validation")}
        dest=ROOT/"runs"/name
        model.save_pretrained(dest)
        tokenizer.save_pretrained(dest)
    target=ROOT/"reports/grouped-evidence.json"
    target.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    for name,result in report["results"].items():
        print(name,{split:{k:v for k,v in values.items() if k!="predictions"} for split,values in result.items()})


if __name__=="__main__":
    main()
