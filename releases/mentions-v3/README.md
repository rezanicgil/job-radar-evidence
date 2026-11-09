---
language: [tr, en]
license: mit
base_model: MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli
datasets: [rezanicgil/job-radar-match-pilot]
---

# Job Radar bilingual evidence classifier

This research checkpoint predicts how well a single CV passage supports a single job requirement. The download contains the 20 tensors changed during training, stored as exact replacements for the final encoder layer and classification head. Load the remaining weights from the pinned base model.

## Run locally

Download [predict.py](https://huggingface.co/rezanicgil/job-radar-evidence-mentions-v3/resolve/main/predict.py) and [requirements.txt](https://huggingface.co/rezanicgil/job-radar-evidence-mentions-v3/resolve/main/requirements.txt) into one folder. From that folder, using a Python environment with the listed dependencies, run:

```console
python -m pip install -r requirements.txt
python predict.py --example
```

The first prediction fetches a pinned base model, tokenizer and verified research weights. To enter your own Turkish or English pair interactively, run `python predict.py`. With the files cached, `python predict.py --offline` also accepts your pair without fetching weights. In a pipeline, supply one UTF-8 JSON object on standard input:

```json
{"cv_passage":"I monitored the deployment while a colleague released the app.","requirement":"Release a mobile app to production."}
```

Output contains the predicted research label, immutable model revision, input token count and a truncation flag. The pair is processed on your computer. Use short passages: the model sees at most 128 tokens including special tokens. [Browse 30 recorded predictions](https://rezanicgil-job-radar-evidence.static.hf.space/model.html).

## Training and limitations

The classifier trained on 69 synthetic pairs for six epochs with AdamW, learning rate 5e-5, batch size six and seed 17. Its predictions matched nine of 18 author-assigned development labels, with two incorrect predictions of full support. It credited meeting logistics as practical Docker experience. This small, previously inspected development set cannot establish accuracy on real applicants. Use the weights for reproducibility and error analysis. The applicant-facing Space uses passage retrieval and reviewer-confirmed coverage. [Predictions](https://github.com/rezanicgil/job-radar-evidence/blob/dba6189/reports/pair-mentions-v3.json) · [Dataset revision](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/tree/6aead3277f882235adb73ca42bc939b187d0862d)

Base model by Moritz Laurer, derived from Microsoft's multilingual MiniLMv2. The base model identifies its license as MIT. Project-specific adaptations by the Job Radar project. [Upstream model and citation](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli/tree/0a71e92a985b6e1ad1828cf67ce9c459639c1dca)

## Selective suggestions

Across 30 fictional cases grounded in ten employers' qualifications, the checkpoint matched 14/30 reference labels and missed all ten partial examples. When each case was rendered in four job/CV language combinations, the predicted label varied for 17/30 cases. The 120 views represent 30 underlying examples. [Inspect a language-dependent prediction](https://rezanicgil-job-radar-evidence.static.hf.space/model.html?family=cloud-runtime&reference=supported&job=tr&cv=en#example-cloud-runtime-supported)

A class-specific threshold on the difference between the two largest logits was chosen on the 18 original development pairs. A class needed at least three accepted predictions and 80% empirical precision there. Only the supported class qualified. On the separate 30 source-grounded development pairs, the model suggested full support five times and was correct once. It withheld the remaining 25 predictions. The margin therefore does not provide a dependable confidence percentage for an applicant. Both sets are synthetic and have previously been inspected during development. [Thresholds and individual predictions](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/selective-evidence.json)
