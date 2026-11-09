"""Train on individual attributed clauses, then aggregate their evidence for AND conditions."""

import hashlib
import json
import re
from collections import Counter

import torch
from check_compound_evidence import combine, metrics
from train_actor_attribution import CLASSES
from train_pair_encoder import BASE, REVISION, ROOT, LABELS, AutoTokenizer, AutoModelForSequenceClassification, encode, run


def clauses(text):
    # Split at sentence boundaries and semicolons. Keep versions such as 2.4 intact.
    return [part.strip() for part in re.split(r"(?<=[.!?;])\s+", text) if part.strip()]


def main():
    torch.set_num_threads(4)
    paths = [ROOT/"data/actor_evidence_train.jsonl", ROOT/"data/compound_evidence_dev.jsonl",
             ROOT/"releases/match-pilot/compound_transfer.jsonl"]
    actors, original, transfer = [[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] for path in paths]
    cases = original + transfer
    assert {r["family"] for r in original}.isdisjoint(r["family"] for r in transfer)
    labels = {}
    for row in actors:
        parts = clauses(row["cv_passage"])
        if row["quote"]:
            assert sum(row["quote"] in part for part in parts) == 1
        for part in parts:
            key = (part, row["component"])
            label = row["actor"] if row["quote"] and row["quote"] in part else "not_stated"
            assert labels.setdefault(key, label) == label
    training = [dict(cv_passage=part, requirement=req, label=label) for (part, req), label in labels.items()]
    evaluation = []
    for row in cases:
        for req in row["components"]:
            for part in clauses(row["cv_passage"]):
                evaluation.append(dict(requirement=req, cv_passage=part))
    for key in ("requirement","cv_passage"):
        assert {r[key] for r in training}.isdisjoint(r[key] for r in evaluation)
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    # run() also computes accuracy. Only its predictions are used here, since the
    # compound diagnostic has gold labels at component level, not per clause.
    # Use the training set as the labeled dev argument, then reload for inference.
    run(training, training, tokenizer, True, "clause-attribution", CLASSES, "applicant")
    model = AutoModelForSequenceClassification.from_pretrained(ROOT/"runs/pair-clause-attribution").eval()
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(evaluation), 16):
            batch = evaluation[start:start+16]
            predictions.extend(CLASSES[i] for i in model(**encode(batch,tokenizer)).logits.argmax(1).tolist())
    pos = 0
    details = []
    for row in cases:
        size = len(clauses(row["cv_passage"]))
        parts = []
        for req in row["components"]:
            votes = predictions[pos:pos+size]
            pos += size
            parts.append("supported" if "applicant" in votes else "unverified")
        details.append(dict(family=row["family"], expected=combine(row["component_labels"]),
                            prediction=combine(parts), component_predictions=parts))
    assert pos == len(predictions)
    baseline = AutoModelForSequenceClassification.from_pretrained(ROOT/"runs/pair-mentions-v3").eval()
    with torch.inference_mode():
        direct = [LABELS[i] for i in baseline(**encode(cases,tokenizer)).logits.argmax(1).tolist()]
    report = dict(base=BASE, revision=REVISION, seed=17,
                  data_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  unique_training_pairs=len(training), classes=Counter(labels.values()),splits={})
    for name, subset, start in [("original",original,0),("transfer",transfer,len(original))]:
        stop = start+len(subset)
        batch = details[start:stop]
        expected = [c["expected"] for c in batch]
        result = dict(compound=metrics(expected,[c["prediction"] for c in batch]),
                      direct_baseline=metrics(expected,direct[start:stop]),
                      atomic=metrics([label for row in subset for label in row["component_labels"]],
                                     [label for row in batch for label in row["component_predictions"]]),
                      cases=[dict(c,direct=d) for c,d in zip(batch,direct[start:stop],strict=True)])
        report["splits"][name]=result
        print(name,result["compound"],result["direct_baseline"])
    (ROOT/"reports/clause-attribution.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
