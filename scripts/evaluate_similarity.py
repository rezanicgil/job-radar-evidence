"""Calibrate cosine similarity on the pilot and evaluate on the development challenge."""

from itertools import combinations
import json

import torch
from transformers import AutoModel, AutoTokenizer

from train_smoke import BASE, REVISION, ROOT


def load_scores(file, tokenizer, model):
    rows = [json.loads(line) for line in (ROOT / "data" / file).read_text(encoding="utf-8").splitlines()]
    texts = [r[k] for r in rows for k in ("requirement", "cv_passage")]
    batch = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
    with torch.inference_mode():
        hidden = model(**batch).last_hidden_state
        mask = batch.attention_mask.unsqueeze(-1)
        vectors = (hidden * mask).sum(1) / mask.sum(1)
        scores = torch.nn.functional.cosine_similarity(vectors[::2], vectors[1::2])
    for row, score in zip(rows, scores.tolist(), strict=True):
        row["cosine"] = score
    return rows


def classify(score, low, high):
    if score < low:
        return "unverified"
    return "partial" if score < high else "supported"


def metrics(rows, low, high):
    pairs = [(classify(r["cosine"], low, high), r["label"]) for r in rows]
    return (sum(p == y for p, y in pairs),
            sum(p == "supported" and y != p for p, y in pairs))


def main():
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModel.from_pretrained(BASE, revision=REVISION).eval()
    pilot = load_scores("match_pilot.jsonl", tokenizer, model)
    scores = sorted({r["cosine"] for r in pilot})
    thresholds = [-1.01, *((a+b)/2 for a,b in zip(scores,scores[1:])), 1.01]
    def selection_key(cutoffs):
        correct, false_support = metrics(pilot, *cutoffs)
        return correct, -false_support, cutoffs[1]
    low, high = max(combinations(thresholds,2), key=selection_key)
    challenge = load_scores("match_challenge_dev.jsonl", tokenizer, model)
    correct, false_support = metrics(challenge, low, high)
    for r in challenge:
        r["prediction"] = classify(r["cosine"], low, high)
    result = dict(base=BASE, revision=REVISION, calibration_file="match_pilot.jsonl",
                  low=low, high=high, correct=correct, total=len(challenge),
                  false_support=false_support, examples=challenge)
    output = ROOT / "reports/similarity-challenge.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Correct: {correct}/{len(challenge)}. False support: {false_support}.")


if __name__ == "__main__":
    main()
