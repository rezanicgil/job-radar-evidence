"""Stage the local checkpoint card and verify the saved development predictions."""

import json
import shutil

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from train_pair_encoder import ROOT, encode


def main():
    path = ROOT / "runs/pair-v2"
    torch.set_num_threads(4)
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True).eval()
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    rows = [json.loads(s) for s in (ROOT / "data/match_challenge_dev.jsonl").read_text(encoding="utf-8").splitlines()]
    expected = json.loads((ROOT / "reports/pair-v2.json").read_text(encoding="utf-8"))["adapted"]["predictions"]
    with torch.inference_mode():
        predictions = [model.config.id2label[i] for i in model(**encode(rows,tokenizer)).logits.argmax(1).tolist()]
    if predictions != expected:
        raise ValueError("Model package predictions differ from the development report")
    shutil.copyfile(ROOT / "releases/pair-v2/README.md",path / "README.md")
    print(f"Verified {len(rows)} saved predictions from {path}")


if __name__ == "__main__":
    main()
