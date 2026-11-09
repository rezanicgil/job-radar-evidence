"""Fine-tune the last encoder block and a three-way head on development data."""

import hashlib
import json
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
BASE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
LABELS = ["partial", "supported", "unverified"]


def main():
    torch.manual_seed(17)
    torch.set_num_threads(4)
    path = ROOT / "data/match_pilot.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, revision=REVISION, num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)), label2id={v:i for i,v in enumerate(LABELS)},
    )
    model.base_model.requires_grad_(False)
    block = model.base_model.encoder.layer[-1]
    block.requires_grad_(True)
    tracked = next(block.parameters())
    before = tracked.detach().clone()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=3e-5)
    losses = []
    model.train()
    for start in range(0, len(rows), 3):
        batch = rows[start:start + 3]
        inputs = tokenizer([r["requirement"] for r in batch], [r["cv_passage"] for r in batch],
                           padding=True, truncation=True, max_length=128, return_tensors="pt")
        targets = torch.tensor([LABELS.index(r["label"]) for r in batch])
        optimizer.zero_grad()
        loss = model(**inputs, labels=targets).loss
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
    delta = (before - tracked.detach()).abs().max().item()
    if not delta > 0 or not torch.isfinite(torch.tensor(losses)).all():
        raise RuntimeError("Invalid encoder update")
    output = ROOT / "runs" / "smoke"
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    reloaded = AutoModelForSequenceClassification.from_pretrained(output).eval()
    model.eval()
    with torch.no_grad():
        torch.testing.assert_close(reloaded(**inputs).logits, model(**inputs).logits)
    report = dict(base=BASE, revision=REVISION, dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  seed=17, device="cpu", steps=len(losses), losses=losses, encoder_max_update=delta,
                  checkpoint_reload_verified=True)
    (output / "run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
