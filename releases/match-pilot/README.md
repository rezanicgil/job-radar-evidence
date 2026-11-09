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
---

# Job Radar · Bilingual CV evidence pilot

This pilot contains 54 fictional requirement–CV passage pairs from 18 families. Use it to develop and critique applicant-facing evidence matching. Each family presents one requirement with three different CV passages. The three labels each occur 18 times.

## How to read a row

`family` identifies related cases. `requirement` describes an employer's condition. `cv_passage` contains the fictional applicant's statement. `label` is the author's judgment of the passage. Supported means the passage establishes the condition, partial means it establishes a relevant component, and unverified means the condition has no supporting evidence in that passage.

## Provenance and evaluation

The project assistant authored the examples and initial labels during dataset development. The pilot covers English, Turkish and cross-language matching. The data has no independent human adjudication. All rows are training material. The balanced distribution was intentional and does not estimate real-world class frequencies.

Keep related CVs, translations, rephrasings and templates together when creating new evaluation sets. The scores of models trained on this pilot are unsuitable for estimating an applicant's likelihood of getting hired. Use an independently reviewed external set for product decisions.

This release contains no user CV uploads or republished employer postings. Apache-2.0 applies to these original synthetic records. When reporting a label issue, include the family, the passage and the wording that supports your correction.
