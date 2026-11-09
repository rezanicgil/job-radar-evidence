"""Rank first-person experience against technology and responsibility distractors."""
from hashlib import sha256
import json

import torch
from transformers import AutoModel, AutoTokenizer

from evaluate_pooled_retrieval import bm25, embeddings, terms
from train_smoke import BASE, REVISION, ROOT


def main(adapt=False):
    path = ROOT / "releases/match-pilot/duration_scope_retrieval.jsonl"
    cases = [json.loads(line) for line in path.read_text("utf8").splitlines()]
    roles = ("other_technology", "direct_work", "other_responsibility")
    texts = sorted({text for case in cases for key in ("requirement", *roles)
                    for text in case[key].values()})
    checkpoints = {"base": (BASE, REVISION), "fine_tuned": (
        "rezanicgil/python-tr-en-retriever", "813078062d92ba7d57487fd97b14af3acd620522")}
    results = {}
    for method in ("bm25", *checkpoints, *(["scope_candidate"] if adapt else [])):
        if method != "bm25":
            repo, revision = checkpoints.get(method, checkpoints["fine_tuned"])
            tokenizer = AutoTokenizer.from_pretrained(repo, revision=revision)
            model = AutoModel.from_pretrained(repo, revision=revision).eval()
            if method == "scope_candidate":
                from train_scope_retriever import adapt_last_layer
                adapt_last_layer(model, tokenizer)
            vectors = dict(zip(texts, embeddings(model, tokenizer, texts), strict=True))
        rankings = []
        for case in cases:
            for source in ("en", "tr"):
                query = case["requirement"][source]
                for target in ("en", "tr"):
                    passages = [case[key][target] for key in roles]
                    scores = (bm25(query, [terms(p) for p in passages]) if method == "bm25" else
                              [float(vectors[query] @ vectors[p]) for p in passages])
                    winners = [name for name, score in zip(roles, scores) if score == max(scores)]
                    rankings.append(dict(family=case["family"], direction=source+"-"+target, first=winners))
        hits = sum(row["first"] == ["direct_work"] for row in rankings)
        results[method] = dict(unique_first=hits, comparisons=len(rankings), cases=rankings)
        print(method, hits, "/", len(rankings))
    report = dict(packet_sha256=sha256(path.read_bytes()).hexdigest(), checkpoints=checkpoints, models=results)
    (ROOT / "reports/duration-scope-retrieval.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf8")


if __name__ == "__main__":
    torch.set_num_threads(4)
    import argparse
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--adapt", action="store_true")
    main(cli.parse_args().adapt)
