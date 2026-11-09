---
language: [tr, en]
license: mit
base_model: MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli
datasets: [rezanicgil/job-radar-match-pilot]
---

# Job Radar bilingual evidence classifier

This research checkpoint predicts how well a single CV passage supports a single job requirement. The download contains the 20 tensors changed during training, stored as exact replacements for the final encoder layer and classification head. Load the remaining weights from the pinned base model.

## Run locally

Install PyTorch, Transformers, safetensors and huggingface_hub. Pass the CV passage first and the job requirement second.

```python
import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
from transformers import AutoModelForSequenceClassification, AutoTokenizer

base = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"
revision = "0a71e92a985b6e1ad1828cf67ce9c459639c1dca"
model = AutoModelForSequenceClassification.from_pretrained(base, revision=revision).eval()
tokenizer = AutoTokenizer.from_pretrained(base, revision=revision)
path = hf_hub_download("rezanicgil/job-radar-evidence-mentions-v3", "trained_layers.safetensors")
state = model.state_dict()
state.update(load_file(path))
model.load_state_dict(state, strict=True)
labels = ["partial", "supported", "unverified"]
model.config.id2label = dict(enumerate(labels))
model.config.label2id = {v: k for k, v in enumerate(labels)}
inputs = tokenizer("Docker ile sipariş servisini konteynerde çalıştırdım.",
                   "Run a backend service with Docker.", truncation=True, max_length=128,
                   return_tensors="pt")
with torch.inference_mode():
    print(labels[model(**inputs).logits.argmax(-1).item()])
```

## Training and limitations

The classifier trained on 69 synthetic pairs for six epochs with AdamW, learning rate 5e-5, batch size six and seed 17. Its predictions matched nine of 18 author-assigned development labels, with two incorrect predictions of full support. It credited meeting logistics as practical Docker experience. This small, previously inspected development set cannot establish accuracy on real applicants. Use the weights for reproducibility and error analysis. The applicant-facing Space uses passage retrieval and reviewer-confirmed coverage. [Predictions](https://github.com/rezanicgil/job-radar-evidence/blob/dba6189/reports/pair-mentions-v3.json) · [Dataset revision](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/tree/6aead3277f882235adb73ca42bc939b187d0862d)

Base model by Moritz Laurer, derived from Microsoft's multilingual MiniLMv2. The base model identifies its license as MIT. Project-specific adaptations by the Job Radar project. [Upstream model and citation](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli/tree/0a71e92a985b6e1ad1828cf67ce9c459639c1dca)

## Selective suggestions

A class-specific threshold on the difference between the two largest logits was chosen on the 18 original development pairs. A class needed at least three accepted predictions and 80% empirical precision there. Only the supported class qualified. On the separate 30 source-grounded development pairs, the model suggested full support five times and was correct once. It withheld the remaining 25 predictions. The margin therefore does not provide a dependable confidence percentage for an applicant. Both sets are synthetic and have previously been inspected during development. [Thresholds and individual predictions](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/selective-evidence.json)
