---
language: [tr, en]
base_model: MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli
library_name: transformers
pipeline_tag: text-classification
---

# Job Radar Evidence · Pair encoder v2 (research checkpoint)

This experimental classifier predicts evidence strength for a single CV passage and job condition. Use it to reproduce the failure analysis. It has no independent accuracy estimate and is unsuitable for applicant scoring or hiring decisions.

## Inputs and labels

Encode the CV passage as the first sequence and the requirement as the second, truncating at 128 tokens. The output labels are `partial`, `supported` and `unverified`. The classifier produces a label only; evidence extraction and market analysis use separate components.

## Training

Base revision: `0a71e92a985b6e1ad1828cf67ce9c459639c1dca`. Fifty-four fictional examples from 18 families supplied supervision. The classification head and final encoder layer were trainable for six epochs using AdamW, learning rate 5e-5, batch size 6 and seed 17. Reproduce with `python scripts/train_pair_encoder.py --contrasts` in the [source repository](https://github.com/rezanicgil/job-radar-evidence).

## Development results

On nine synthetic development pairs the adapted model matched three labels and incorrectly predicted full support twice. Head-only fitting matched four labels with one false support. A calibrated similarity baseline matched six labels but missed every fully supported example. The adapted model credited simulated firmware work toward a physical-device requirement. The public demo therefore uses passage retrieval and reviewer-confirmed coverage. See the [per-case predictions](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/pair-v2.json).

## Local inference

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

path = "runs/pair-v2"
model = AutoModelForSequenceClassification.from_pretrained(path).eval()
tokenizer = AutoTokenizer.from_pretrained(path)
pair = tokenizer("I debugged firmware in a simulator.", "Debug firmware on physical hardware.",
                 truncation=True, max_length=128, return_tensors="pt")
with torch.inference_mode():
    label = model.config.id2label[model(**pair).logits.argmax().item()]
print(label)
```

The upstream checkpoint identifies its license as MIT. Preserve upstream notices and verify the redistribution scope before uploading weights. Original project code is licensed separately.
