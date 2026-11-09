"""Learn relative evidence strength using matched requirement/passage triples."""

from collections import defaultdict
import hashlib
import json
import random

import torch
from transformers import AutoModel, AutoTokenizer

from train_smoke import BASE, REVISION, ROOT

LABELS = ("supported", "partial", "unverified")
TRAIN = ("match_training_v1.jsonl", "match_contrasts_v2.jsonl")
DEV = ("match_challenge_dev.jsonl",)


def read_groups(names):
    groups = defaultdict(dict)
    for name in names:
        for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key = (row["family"], row["requirement"])
            if row["label"] in groups[key]:
                raise ValueError(f"Duplicate label for {key}")
            groups[key][row["label"]] = row["cv_passage"]
    if any(set(group) != set(LABELS) for group in groups.values()):
        raise ValueError("Incomplete evidence triple")
    return groups


def scores(model, tokenizer, requirement, group):
    texts = [requirement] + [group[label] for label in LABELS]
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
    mask = inputs.attention_mask.unsqueeze(-1)
    pooled = (model(**inputs).last_hidden_state * mask).sum(1) / mask.sum(1)
    return torch.nn.functional.cosine_similarity(pooled[:1], pooled[1:])


def evaluate(model, tokenizer, groups):
    model.eval()
    result = {}
    with torch.inference_mode():
        for (family, requirement), group in groups.items():
            values = scores(model, tokenizer, requirement, group).tolist()
            result[family] = dict(scores=dict(zip(LABELS, values)), supported_first=values[0] > max(values[1:]))
    return result


def main():
    torch.manual_seed(17)
    torch.set_num_threads(4)
    rng = random.Random(17)
    training = read_groups(TRAIN)
    development = read_groups(DEV)
    if {k[0] for k in training} & {k[0] for k in development}:
        raise ValueError("Training and development families overlap")
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModel.from_pretrained(BASE, revision=REVISION)
    before = evaluate(model, tokenizer, development)
    model.requires_grad_(False)
    model.encoder.layer[-1].requires_grad_(True)
    optimizer = torch.optim.AdamW(model.encoder.layer[-1].parameters(), lr=3e-5)
    keys = list(training)
    model.train()
    for _ in range(4):
        rng.shuffle(keys)
        for start in range(0, len(keys), 3):
            batch = keys[start:start + 3]
            similarities = torch.stack([scores(model, tokenizer, k[1], training[k]) for k in batch])
            loss = (0.15 + similarities[:, 1:] - similarities[:, :-1]).clamp_min(0).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    output = ROOT / "runs/passage-ranker-v1"
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    after = evaluate(AutoModel.from_pretrained(output), tokenizer, development)
    report = dict(base=BASE, revision=REVISION, seed=17, epochs=4, margin=0.15, family_batch=3,
                  training_families=len(training), development_families=len(development),
                  sha256={n: hashlib.sha256((ROOT / "data" / n).read_bytes()).hexdigest() for n in TRAIN + DEV},
                  before=before, after=after)
    (ROOT / "reports/passage-ranker-v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for family in before:
        print(family, before[family]["supported_first"], after[family]["supported_first"])


if __name__ == "__main__":
    main()
