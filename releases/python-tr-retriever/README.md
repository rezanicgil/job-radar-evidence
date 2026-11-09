---
license: apache-2.0
language: [en, tr]
library_name: transformers
pipeline_tag: feature-extraction
base_model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
datasets: [rezanicgil/job-radar-match-pilot]
---

# Python documentation retriever for Turkish and English

This encoder retrieves parallel passages from Python documentation. We adapted the final transformer block of multilingual MiniLM on 1,027 pairs from 34 documentation files. Each batch used the other translations in the batch as negatives. We trained for one epoch with a symmetric contrastive loss.

| First result matches the target | Base | Adapted |
| --- | ---: | ---: |
| English query against 721 Turkish translations | 669/721 | 674/721 |
| Turkish query against 721 English translations | 684/721 | 688/721 |
| Job condition against 30 fictional CV passages | 5/10 | 5/10 |

The documentation evaluation uses ten held-out files. The base model's pretraining may include related material. In the separate CV diagnostic the target passage appeared in the first three for nine of ten conditions with either encoder. All ten target ranks stayed the same. The evaluation covers one training run and author-assigned CV targets. Applicant suitability and hiring outcomes were not measured.

```python
import torch
from transformers import AutoModel, AutoTokenizer

repo = "rezanicgil/python-tr-en-retriever"
tokenizer = AutoTokenizer.from_pretrained(repo)
model = AutoModel.from_pretrained(repo).eval()
texts = ["Look up values by key.", "Değerleri anahtara göre ara."]
tokens = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
with torch.inference_mode():
    mask = tokens.attention_mask.unsqueeze(-1)
    pooled = (model(**tokens).last_hidden_state * mask).sum(1) / mask.sum(1)
    vectors = torch.nn.functional.normalize(pooled)
    print((vectors[0] @ vectors[1]).item())
```

[Training code](https://github.com/rezanicgil/job-radar-evidence/blob/main/scripts/train_translation_retrieval.py) · [Per-condition ranks and split details](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/translation-retrieval.json) · [Python Turkish translators and source texts](https://github.com/python/python-docs-tr/tree/caa8b1e08b8534a1e1344a82889fc6c820768a91)
