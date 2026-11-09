# Job Radar Evidence

An applicant comparing their CV with a software vacancy can inspect relevant CV passages, decide whether each requirement is supported, and see the denominator behind their coverage score. A second view lets them inspect technology mentions by role and employer in a dated Türkiye job snapshot.

## Engineering work

The project combines Turkish and English evidence retrieval, PDF and TXT parsing, a Flask review interface, public job-board ingestion and repeatable CPU fine-tuning experiments. The Space container has passed a Linux build and HTTP inference check in GitHub Actions.

The [public Hugging Face demo](https://huggingface.co/spaces/rezanicgil/job-radar-evidence) uses a Static Space. It processes documents in the visitor's browser and offers shared-term retrieval or optional multilingual semantic search. The server-based Docker build remains available for local deployments.

The published research classifier trained on 69 synthetic pairs. A separate English job-sentence selector trained on 3,943 deduplicated SkillSpan sentences and reached 75.0% F1 on its 2,404-sentence test split. The November 9 snapshot includes 72 readable descriptions from 18 employers. Readers can inspect source links and compare posting share with employer share.

## A decision based on evaluation

On 30 synthetic development cases inspired by ten employers, the published classifier matched 14 reference labels and missed all ten partial cases. The same evidence yielded different predictions across Turkish and English versions in 17 cases. The public demo asks applicants to verify passages and can export their decisions with exact wording and page references. Independent human validation and broader Türkiye source coverage remain open.

## CV project entry

Built and published a bilingual CV evidence-review tool on Hugging Face. Fine-tuned a multilingual evidence classifier, evaluated it on requirements from ten employers, and shipped a local English job-sentence selector with 75.0% test F1 on SkillSpan.

## Reproduce and inspect

- [Training release](../releases/match-pilot/README.md)
- [Pair-encoder development results](../reports/pair-v2.json)
- [Similarity baseline](../reports/similarity-challenge.json)
- [Published classifier](https://huggingface.co/rezanicgil/job-radar-evidence-mentions-v3)
- [Employer-sourced evaluation](../reports/source-pairs-dev.json)
- [Market sources and counts](../reports/skill-mentions-2026-11-09T163018Z.md)
- [Public browser review workflow check](https://github.com/rezanicgil/job-radar-evidence/actions/runs/42654331798)
- [Container verification](https://github.com/rezanicgil/job-radar-evidence/actions/runs/42635859051)
