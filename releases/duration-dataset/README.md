---
pretty_name: Job Radar Duration Evidence Index
language: [en, tr]
license: cc-by-4.0
configs:
  - config_name: default
    data_files:
      - split: train
        path: train.jsonl
      - split: validation
        path: validation.jsonl
      - split: test
        path: test.jsonl
---
# Job Radar Duration Evidence Index

Explore which time expressions informed the [duration classifier](https://huggingface.co/rezanicgil/job-radar-duration-context), where they appeared, and how they were interpreted. This is a provenance and annotation index, not a standalone text-training corpus. CC BY 4.0 covers our index and annotations; linked employer descriptions are not redistributed.

**Unit:** one marked duration, not one job. Each row links to the observed employer posting, which can change or close. The passage hash uses SHA-256 of NFKC, case-folded, whitespace-normalized text. Start (inclusive) and end (exclusive) are character offsets in the collected passage before hash normalization, not in the entire web page.

**Training:** 75 assistant-draft mentions, including 11 auxiliary examples from outside tracked software role families. Only 60 describe prior experience; the remaining 15 describe other durations. No human-confirmed training labels. The released binary classifier maps all non-experience categories to “other duration”.

**Reserved for independent review:** 35 validation and 23 test mentions. Their labels and scopes are deliberately null. Employers do not cross partitions. No score against these unlabeled splits is reported. Exact normalization and a near-duplicate check do not rule out translated or paraphrased duplicates.

This sample does not estimate national job demand or applicant eligibility. [Collection, split design and training code](https://github.com/rezanicgil/job-radar-evidence) · [Try the browser demo](https://rezanicgil-job-radar-evidence.static.hf.space/duration-lab.html).

## Reproduce the classification head

The 75 frozen training embeddings are available in train-features.safetensors, aligned to train.jsonl by file hash and row order. The held-out partitions are excluded. These vectors describe public job posting contexts, not personal CVs. They support retraining the linear head only; the source texts are still needed to change or retrain the encoder.

Download the dataset repository and run the following in its directory:
~~~sh
python -m pip install torch==2.7.0 safetensors==0.5.3
python reproduce.py
~~~
This writes reproduced-head.safetensors. On the reference CPU environment its weight and bias tensors are exactly equal to the [released head](https://huggingface.co/rezanicgil/job-radar-duration-context/blob/ed338d59d26219b6574245aaf9488cda4dc3c5e9/head.safetensors). Different hardware or numerical libraries can produce small numerical differences.

## Reproduce the reported evaluation

Run `python evaluate.py` in the same directory. It refits the head for each of 19 employers, scoring only that employer in its fold. It reports an ID-level prediction for all 75 training records. No validation or test labels are used. The published result is 60/60 correct prior-experience mentions and 11/15 correct other durations: balanced accuracy is the mean of these two recall rates (86.7%). Two recent-action windows, one program length and one starting window were incorrectly called prior experience. Reproducing these predictions verifies the computation, not the underlying draft annotations.
