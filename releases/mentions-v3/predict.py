"""Predict a research evidence label for one passage/requirement pair on CPU."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
from transformers import AutoModelForSequenceClassification, AutoTokenizer

BASE = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"
BASE_REV = "0a71e92a985b6e1ad1828cf67ce9c459639c1dca"
REPO = "rezanicgil/job-radar-evidence-mentions-v3"
REV = "790d07e85db18780d60e2d1a7ba4a968463fe257"
LAYER_SHA256 = "a64e0d9d01c6cecdd749bab840b24f7d8f366a4b19b3cbf09da9f4c6fa6256e9"
LABELS = ("partial", "supported", "unverified")
LIMIT = 128


def pair_from_input(example):
    if example:
        return "Docker ile sipariş servisini konteynerde çalıştırdım.", "Run a backend service with Docker."
    if sys.stdin.isatty():
        print("CV passage:", file=sys.stderr)
        passage=input()
        print("Job requirement:", file=sys.stderr)
        requirement=input()
    else:
        pair=json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if not isinstance(pair,dict):
            raise ValueError("Provide a JSON object with cv_passage and requirement.")
        passage,requirement=pair.get("cv_passage"),pair.get("requirement")
    if any(not isinstance(s,str) or not s.strip() for s in (passage,requirement)):
        raise ValueError("Both cv_passage and requirement must contain text.")
    return passage.strip(),requirement.strip()


def load_research_model(offline):
    weights=Path(hf_hub_download(REPO,"trained_layers.safetensors",revision=REV,local_files_only=offline))
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=LAYER_SHA256:
        raise ValueError("Research weights failed the checksum check.")
    model=AutoModelForSequenceClassification.from_pretrained(BASE,revision=BASE_REV,local_files_only=offline).eval()
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=BASE_REV,local_files_only=offline)
    state=model.state_dict()
    state.update(load_file(weights))
    model.load_state_dict(state,strict=True)
    return model,tokenizer


def predict(passage,requirement,model,tokenizer):
    length=len(tokenizer(passage,requirement,verbose=False)["input_ids"])
    inputs=tokenizer(passage,requirement,truncation=True,max_length=LIMIT,return_tensors="pt")
    with torch.inference_mode():
        label=LABELS[model(**inputs).logits.argmax(-1).item()]
    return dict(prediction=label,model=REPO,revision=REV,input_tokens=length,truncated=length>LIMIT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example",action="store_true",help="Use a fictional Turkish passage and English requirement.")
    parser.add_argument("--offline",action="store_true",help="Use previously downloaded model files only.")
    args=parser.parse_args()
    try:
        passage,requirement=pair_from_input(args.example)
        model,tokenizer=load_research_model(args.offline)
        print(json.dumps(predict(passage,requirement,model,tokenizer),ensure_ascii=False))
    except (ValueError,OSError,EOFError) as exc:
        parser.exit(2,f"{exc}\n")


if __name__=="__main__":
    main()
