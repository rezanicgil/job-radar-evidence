"""Compare head-only fitting with last-layer adaptation of the same pair encoder."""

import argparse
import hashlib
import json
import random

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from train_smoke import LABELS, ROOT

BASE = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"
REVISION = "0a71e92a985b6e1ad1828cf67ce9c459639c1dca"


def encode(rows, tokenizer):
    return tokenizer([r["cv_passage"] for r in rows], [r["requirement"] for r in rows],
                     padding=True, truncation=True, max_length=128, return_tensors="pt")


def run(training, dev, tokenizer, adapt, version, labels=LABELS, positive_label="supported"):
    torch.manual_seed(17)
    order = list(range(len(training)))
    shuffle = random.Random(17)
    model = AutoModelForSequenceClassification.from_pretrained(BASE, revision=REVISION)
    # The upstream NLI categories differ from the evidence-strength labels.
    model._init_weights(model.classifier.out_proj)
    model.config.id2label = dict(enumerate(labels))
    model.config.label2id = {v:k for k,v in enumerate(labels)}
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(adapt)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=5e-5)
    model.train()
    for _ in range(6):
        shuffle.shuffle(order)
        for start in range(0,len(order),6):
            batch = [training[i] for i in order[start:start+6]]
            targets = torch.tensor([labels.index(r["label"]) for r in batch])
            optimizer.zero_grad()
            loss = model(**encode(batch, tokenizer),labels=targets).loss
            loss.backward()
            optimizer.step()
    model.eval()
    if adapt:
        dest = ROOT / "runs" / f"pair-{version}"
        model.save_pretrained(dest)
        tokenizer.save_pretrained(dest)
        model = AutoModelForSequenceClassification.from_pretrained(dest).eval()
    with torch.inference_mode():
        predictions = [labels[i] for i in model(**encode(dev, tokenizer)).logits.argmax(1).tolist()]
    pairs = list(zip(predictions,[r["label"] for r in dev],strict=True))
    return dict(correct=sum(a==b for a,b in pairs), false_support=sum(a==positive_label and a!=b for a,b in pairs),
                predictions=predictions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contrasts", action="store_true")
    contrasts = parser.parse_args().contrasts
    version = "v2" if contrasts else "v1"
    torch.set_num_threads(4)
    paths = [ROOT / "data" / f for f in ("match_training_v1.jsonl","match_challenge_dev.jsonl")]
    training, dev = [[json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()] for p in paths]
    if contrasts:
        paths.append(ROOT / "data/match_contrasts_v2.jsonl")
        training.extend(json.loads(s) for s in paths[-1].read_text(encoding="utf-8").splitlines())
    assert {r["family"] for r in training}.isdisjoint(r["family"] for r in dev)
    tokenizer = AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    result = dict(base=BASE,revision=REVISION,seed=17,epochs=6, batch_size=6, learning_rate=5e-5,
                  sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  training_rows=len(training), training_families=len({r["family"] for r in training}),
                  head_only=run(training,dev,tokenizer,False,version), adapted=run(training,dev,tokenizer,True,version))
    (ROOT / "reports" / f"pair-{version}.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(result["head_only"], result["adapted"])


if __name__ == "__main__":
    main()
