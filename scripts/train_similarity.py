"""Fit the final MiniLM block to ordinal evidence targets and evaluate a fixed cut point pair."""

import hashlib
import json
import random

import torch
from transformers import AutoModel, AutoTokenizer

from evaluate_similarity import classify, load_scores, metrics
from train_smoke import BASE, REVISION, ROOT

TARGET = {"supported": 0.9, "partial": 0.5, "unverified": 0.1}
CUTOFFS = (0.3, 0.7)


def main():
    torch.manual_seed(17)
    rng = random.Random(17)
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModel.from_pretrained(BASE, revision=REVISION)
    model.requires_grad_(False)
    model.encoder.layer[-1].requires_grad_(True)
    optimizer = torch.optim.AdamW(model.encoder.layer[-1].parameters(), lr=5e-5)
    file = ROOT / "data/match_training_v1.jsonl"
    rows = [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()]
    challenge = "match_challenge_dev.jsonl"
    dev = load_scores(challenge, tokenizer, model.eval())
    assert {r["family"] for r in rows}.isdisjoint(r["family"] for r in dev)
    baseline = metrics(dev, *CUTOFFS)
    model.train()
    for _ in range(5):
        rng.shuffle(rows)
        for start in range(0, len(rows), 6):
            batch = rows[start:start+6]
            texts = [r[k] for r in batch for k in ("requirement","cv_passage")]
            inputs = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
            mask = inputs.attention_mask.unsqueeze(-1)
            vectors = (model(**inputs).last_hidden_state * mask).sum(1) / mask.sum(1)
            scores = torch.nn.functional.cosine_similarity(vectors[::2], vectors[1::2])
            loss = torch.nn.functional.mse_loss(scores, torch.tensor([TARGET[r["label"]] for r in batch]))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    output = ROOT / "runs/similarity-v1"
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    trained = AutoModel.from_pretrained(output).eval()
    rows = load_scores(challenge, tokenizer, trained)
    correct, false_support = metrics(rows, *CUTOFFS)
    for r in rows:
        r["prediction"] = classify(r["cosine"], *CUTOFFS)
    report = dict(base=BASE, revision=REVISION, seed=17, train_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                  epochs=5, cutoffs=CUTOFFS, target_scores=TARGET, baseline_correct=baseline[0],
                  baseline_false_support=baseline[1], correct=correct, false_support=false_support, examples=rows)
    (ROOT / "reports/similarity-finetuned-v1.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(baseline, (correct, false_support), [r["prediction"] for r in rows])


if __name__ == "__main__":
    main()
