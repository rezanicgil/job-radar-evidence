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

The same ten job conditions were also tested in four translated job/CV language combinations. In Turkish/Turkish retrieval, one target moved from fourth to third and another from first to second. In Turkish/English retrieval, one target moved from fifth to sixth. The two English-query views kept all ten original ranks within each view.

## Try a requirement against your own CV

In the [public Space](https://huggingface.co/spaces/rezanicgil/job-radar-evidence), choose **Fine-tuned research encoder (118 MB)** to download the quantized model into your browser. CV passages are ranked on your device. Quantization can change which passages appear in the first three. The browser uses ONNX weights pinned to revision `813078062d92ba7d57487fd97b14af3acd620522`. [Float and quantized ranks on 40 language views](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/browser-encoder.json)

For Transformers.js 2.17.2, the Space loads the compatible tokenizer from `Xenova/paraphrase-multilingual-MiniLM-L12-v2` at `2c4055b12046f11709e9df2c122e59ffbdc2f900`. It preserves word starts and the final separator when truncating to 128 tokens. The Space's tokenizer matched the Python token IDs on 80 distinct bilingual inputs and one long input. [Browser implementation](https://github.com/rezanicgil/job-radar-evidence/blob/main/releases/static-space/research-tokenizer.js)

In the Job Radar checkout, use a text PDF or a UTF-8 TXT file. The command downloads the pinned encoder on first use and processes the CV locally. It prints up to three passages with page references. For an interactive review of multiple requirements, use `--posting job.txt` in place of the quoted requirement. [Local review CLI](https://github.com/rezanicgil/job-radar-evidence/blob/main/scripts/review_cv.py)

```console
python scripts/review_cv.py my-cv.pdf "Diagnose slow SQL queries using execution plans." --encoder fine-tuned
```

## External whole-document ranking

We tested all 1,759 held-out CV/job pairs in an English-language external dataset. Within each CV, we compared pairs of jobs with different source labels and counted how often the model placed the higher-labelled job first. Ties earned half credit. The table gives each eligible CV or job equal weight.

| Method | Rank jobs for one CV (275 CVs) | Rank CVs for one job (61 jobs) |
| --- | ---: | ---: |
| CV's mean training label | 50.00% | 66.13% |
| TF-IDF cosine | 56.18% | 62.12% |
| Base encoder | 63.25% | 66.18% |
| Adapted encoder | 64.58% | 65.11% |

All 71 test job descriptions were unseen in the external training split. Of 477 distinct test CVs, 476 also appeared in training. The dataset provides whole-document labels with undocumented reviewer provenance. These results measure agreement with its ordering. They cannot establish evidence for an individual job requirement. [Pinned dataset](https://huggingface.co/datasets/cnamuangtoun/resume-job-description-fit/tree/08978e21714984bb417547d2c0f9b477f5298163) · [Audit and label-level results](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/external-fit-ranking.json)

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

## External Git translation retrieval

Git’s Turkish localization catalog supplied 3,039 distinct evaluation pairs. Each message was retrieved against the entire opposite-language pool. The checkpoint and base model were frozen. Top-three retrieval rose from 2,151 to 2,204 in English-to-Turkish search and from 2,165 to 2,190 in Turkish-to-English search. The task tests exact technical translation retrieval. The separate job-condition experiments describe the model’s behavior on CV passages. [Source index](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/viewer/git_localization_index/validation) · [Scores and pairwise changes](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/git-localization-retrieval.json)
