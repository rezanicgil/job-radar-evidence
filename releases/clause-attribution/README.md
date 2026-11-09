---
language: [tr, en]
license: mit
library_name: transformers
pipeline_tag: text-classification
base_model: MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli
datasets: [rezanicgil/job-radar-match-pilot]
---

# Job Radar clause attribution

This research classifier reads a CV clause followed by a job requirement and predicts whether the clause attributes relevant work to the applicant, to someone else, or leaves it unstated. Use its scores to investigate candidate passages for human review. The model has no calibration against hiring outcomes.

## Run locally

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

repo = "rezanicgil/job-radar-clause-attribution"
tokenizer = AutoTokenizer.from_pretrained(repo)
model = AutoModelForSequenceClassification.from_pretrained(repo).eval()
inputs = tokenizer("Panoyu ekip arkadaşım geliştirdi.", "Build a reporting dashboard.",
                   return_tensors="pt", truncation=True, max_length=128)
with torch.inference_mode():
    logits = model(**inputs).logits
print(model.config.id2label[logits.argmax(-1).item()])
```

## Training and evaluation

The final encoder layer and classification head were adapted using 144 distinct project-authored clause and requirement pairs. The labels include 24 applicant examples, 24 examples of work performed by another actor and 96 examples where the clause does not establish who performed the required work. The base revision was `0a71e92a985b6e1ad1828cf67ce9c459639c1dca`. [Training code](https://github.com/rezanicgil/job-radar-evidence/blob/main/scripts/train_clause_attribution.py)

On four sourced conditions with three fictional competing passages per condition, ranking passages by their highest applicant score across clauses retrieved the intended passage first for two of four English conditions with Turkish passages and two of four Turkish conditions with English passages. The Python translation encoder retrieved one and zero respectively. The four underlying conditions are shared across language views. Independent human labels and a larger evaluation are needed to assess generalization. [Examples](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/viewer/cross_language_attribution/validation) · [Rankings](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/cross-language-attribution.json)
