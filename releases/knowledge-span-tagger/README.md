---
license: mit
base_model: MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli
library_name: transformers
pipeline_tag: token-classification
language: [en]
datasets: [jjzha/skillspan]
---

# Job Radar knowledge phrase tagger

Given one job condition, this research model marks the words that describe tools or areas of knowledge under the SkillSpan annotation scheme. It predicts the beginning, continuation and outside of a knowledge phrase. The training labels are English. Turkish performance is measured separately on project-authored examples. A span prediction does not determine whether the employer requires the phrase or whether an applicant has that knowledge.

## Run the evaluated extractor

Install the CPU training environment described in the project repository, then run:

```shell
python scripts/extract_knowledge_spans.py --checkpoint rezanicgil/job-radar-knowledge-spans "Create reports in Power BI or Tableau."
```

The command returns source-character offsets and the original text for each predicted span. It uses the first subtoken of each word and splits long inputs at word boundaries. [Extraction script](https://github.com/rezanicgil/job-radar-evidence/blob/main/scripts/extract_knowledge_spans.py)

## Training and evaluation

The final MiniLM encoder layer and classification head were trained using the knowledge tags in SkillSpan by Mike Zhang, Kristian Jensen, Sif Sonniks and Barbara Plank. The upstream release lists the dataset under CC BY 4.0. The base encoder revision is `0a71e92a985b6e1ad1828cf67ce9c459639c1dca`. The script removes normalized sentence duplicates in training, development and test order. It trains two epochs, weights the token loss by inverse square-root frequency, and selects the checkpoint with the highest development exact-span F1. A span counts as correct only when both word boundaries match. The comparison baseline uses the longest matching phrase previously labelled in training. [SkillSpan paper](https://aclanthology.org/2022.naacl-main.366/) · [Pinned annotations](https://huggingface.co/datasets/jjzha/skillspan/tree/33062e6bd0e03a5e01ae299ce0518f4613ef4298) · [Training script](https://github.com/rezanicgil/job-radar-evidence/blob/main/scripts/train_knowledge_spans.py)

The second epoch had the higher development F1. We then fitted a shared bias for B and I using only the development split and stored the resulting classifier parameters in this checkpoint. Bias candidates ranged from -2 to +2 in steps of 0.25. The selected value was -1.25. The calibration script is part of the reproducible training path. Run `python scripts/train_knowledge_spans.py`, then `python scripts/calibrate_knowledge_tagger.py`. [Development sweep](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/knowledge-span-calibration.json)

## Results

| Exact spans on 2,404 English test sentences | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Longest memorized training phrase | 11.7% | 50.4% | 19.0% |
| Fine-tuned model before calibration | 12.8% | 42.1% | 19.6% |
| Released model | 23.8% | 22.0% | 22.9% |
| Published JobBERT reference | 56.2% | 70.5% | 62.5% |

The released model retrieved 219 of 994 reference spans and produced 700 unmatched predictions. On ten project-authored paired examples per language, it found 14 of 18 reference spans in each language, with four unmatched predictions. For example, it split “Power BI” into two spans. The paired examples reuse the same technology names. They do not establish general Turkish accuracy. The Space uses the tagger for research examples and keeps CV coverage based on reviewer decisions. [Interactive examples](https://rezanicgil-job-radar-evidence.static.hf.space/model.html#knowledge) · [Example data](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/viewer/bilingual_knowledge_spans/validation)

We evaluated the published JobBERT checkpoint on the same deduplicated test inputs with the same word-boundary scorer. These figures are our measurements. JobBERT has a different training history. [Reference model](https://huggingface.co/jjzha/jobbert_knowledge_extraction) · [Pinned comparison](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/jobbert-span-reference.json)
