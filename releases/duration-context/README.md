---
license: apache-2.0
language: [en, tr]
base_model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
tags: [job-postings, duration, research]
---
# Job Radar · Duration context

Does a **marked time expression** in a job posting refer to prior experience? This research head predicts one of two labels: prior experience or other duration. It does not extract dates, establish whether a requirement is mandatory, or evaluate an applicant. Text is processed locally.

Download this repository and run:

~~~sh
hf download rezanicgil/job-radar-duration-context --local-dir duration-context
cd duration-context
python -m pip install torch transformers==4.52.4 safetensors
python predict.py "We require [three years] of backend experience." "Taşınma için [iki gün] izin sunuyoruz."
~~~

The first run also downloads the pinned multilingual MiniLM encoder. Only the linear classification head was trained. Ten words on either side of the marked duration are retained, the duration itself is masked, and normalized mean-pooled embeddings feed a class-balanced logistic classifier. No remote custom model code is required by Transformers.

**Data and evaluation.** 75 assistant-labelled duration mentions, including 60 prior-experience cases and 15 others. In 19 leave-one-employer-out folds within this draft training corpus, 60/60 experience mentions and 11/15 other durations were classified correctly (86.7% balanced accuracy; context-word baseline 80%). Published weights were then fitted on all 75 examples. The evaluation is not independent human validation, a Turkish-specific accuracy estimate, or a measure of CV matching quality. The four misclassified examples concerned program length, recent deployments, and starting availability. No hiring probability is produced.

[Training code and out-of-fold predictions](https://github.com/rezanicgil/job-radar-evidence/commit/ec5a061). Please share public or fictional examples in the Community tab rather than personal CV data.

**Bilingual contrast check.** Four authored scenarios paired a work-experience statement with an unrelated duration in each language. English: 2/4 experience statements and 4/4 unrelated durations correct; Turkish: 4/4 and 4/4. The English experience statements missed were in the network, data scenarios. These translated examples are diagnostic, not a representative language benchmark. [Case results](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/duration-context-bilingual.json).
