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
  - config_name: source_grounded
    data_files:
      - split: validation
        path: source_validation.jsonl
---

# Job Radar · Bilingual CV evidence pilot

This pilot contains 69 training pairs from 23 families and 18 development pairs from six other families. Each family presents one job requirement and three fictional CV passages with different evidence labels. The training split contains 23 examples per label and the validation split contains six per label.

The validation file begins with nine general challenge examples and ends with nine examples about Docker, Terraform and Prometheus. A passage can name the right technology while describing event logistics rather than engineering work. The [experiment predictions](https://github.com/rezanicgil/job-radar-evidence/blob/dba6189/reports/pair-mentions-v3.json) show where the model confused the two. The [original 54-row release](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/tree/cb96ff522186ae77a3b9f1bada3ee32842d91b15) remains available for earlier experiments.

## How to read a row

| Split | Pairs | Requirement families | Supported / partial / unverified |
| --- | ---: | ---: | --- |
| Train | 69 | 23 | 23 / 23 / 23 |
| Validation | 18 | 6 | 6 / 6 / 6 |

For the requirement “Package and run a backend service with Docker”, listing Docker in a skills section receives a partial label. Describing personally building an image and running a service supports the condition. Booking a room for Docker training receives an unverified label.

`family` identifies related cases. `requirement` describes an employer's condition. `cv_passage` contains the fictional applicant's statement. `label` is the author's judgment of the passage. Supported means the passage establishes the condition, partial means it establishes a relevant component, and unverified means the condition has no supporting evidence in that passage.

## Provenance and evaluation

The project assistant authored the examples and initial labels during dataset development. The pilot covers English, Turkish and cross-language matching. The data has no independent human adjudication. Developers have inspected validation outcomes during model development. The balanced distribution was intentional and does not estimate real-world class frequencies.

Keep related CVs, translations, rephrasings and templates together when creating new evaluation sets. The scores of models trained on this pilot are unsuitable for estimating an applicant's likelihood of getting hired. Use an independently reviewed external set for product decisions.

### What the current classifier misses

The mentions-v3 checkpoint recovered 4/6 supported examples (66.7%), 0/6 partial examples (0%) and 5/6 unverified examples (83.3%). Overall accuracy was 9/18 (50%). Each class percentage measures recall against the synthetic author labels. [Per-example predictions](https://github.com/rezanicgil/job-radar-evidence/blob/dba6189/reports/pair-mentions-v3.json)

The next collection batch contains 12 unlabeled fictional passages paired with requirements adapted from three source postings. They are available for review outside these splits. Further collection should sample independent employers and requirements across software specialties, include all four Turkish/English language directions, and prioritize passages that share a technology name while differing in responsibility or deployment experience. [Review candidates](https://github.com/rezanicgil/job-radar-evidence/blob/a7f1a6d/research/source_grounded_candidates.jsonl)

### Source-grounded development configuration

Select `source_grounded` for 30 additional synthetic pairs. Ten selected qualifications from ten employers supplied the context for original requirement paraphrases and fictional CV passages. Each row includes the source URL, section, bullet position and normalized-text fingerprint. The project authored the three labels per family. We checked for exact family, requirement and passage overlap with training. These are development cases with related skills and synthetic author labels, without independent adjudication.

On these cases the published mentions-v3 checkpoint recovered 7/10 fully supported examples, 0/10 partial examples and 7/10 unverified examples. It incorrectly marked 9/20 partial or unverified examples as supported. [Predictions](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/source-pairs-dev.json)

This release contains no user CV uploads or republished employer postings. Apache-2.0 applies to these original synthetic records. When reporting a label issue, include the family, the passage and the wording that supports your correction.
