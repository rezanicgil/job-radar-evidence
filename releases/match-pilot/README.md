---
language:
  - tr
  - en
license: apache-2.0
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files:
      - split: train
        path: train.jsonl
      - split: validation
        path: validation.jsonl
---

# Job Radar · Bilingual CV evidence pilot

This pilot contains 69 training pairs from 23 families and 18 development pairs from six other families. Each family presents one job requirement and three fictional CV passages with different evidence labels. The training split contains 23 examples per label and the validation split contains six per label.

The validation file begins with nine general challenge examples and ends with nine examples about Docker, Terraform and Prometheus. A passage can name the right technology while describing event logistics rather than engineering work. The [experiment predictions](https://github.com/rezanicgil/job-radar-evidence/blob/dba6189/reports/pair-mentions-v3.json) show where the model confused the two. The [original 54-row release](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/tree/cb96ff522186ae77a3b9f1bada3ee32842d91b15) remains available for earlier experiments.

## How to read a row

`family` identifies related cases. `requirement` describes an employer's condition. `cv_passage` contains the fictional applicant's statement. `label` is the author's judgment of the passage. Supported means the passage establishes the condition, partial means it establishes a relevant component, and unverified means the condition has no supporting evidence in that passage.

## Provenance and evaluation

The project assistant authored the examples and initial labels during dataset development. The pilot covers English, Turkish and cross-language matching. The data has no independent human adjudication. Developers have inspected validation outcomes during model development. The balanced distribution was intentional and does not estimate real-world class frequencies.

Keep related CVs, translations, rephrasings and templates together when creating new evaluation sets. The scores of models trained on this pilot are unsuitable for estimating an applicant's likelihood of getting hired. Use an independently reviewed external set for product decisions.

This release contains no user CV uploads or republished employer postings. Apache-2.0 applies to these original synthetic records. When reporting a label issue, include the family, the passage and the wording that supports your correction.
