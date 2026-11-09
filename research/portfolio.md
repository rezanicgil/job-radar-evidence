# Job Radar Evidence

An applicant comparing their CV with a software vacancy can inspect relevant CV passages, decide whether each requirement is supported, and see the denominator behind their coverage score. A second view lets them inspect technology mentions by role and employer in a dated Türkiye job snapshot.

In the fictional demo, the CV documents 30 months developing control software with C++ and the job asks for 36. The applicant can fully document the Python reporting requirement. With one of two required conditions fully supported, the review reports 50% coverage and shows the six-month shortfall beside the selected passage. [Read the exported report](fictional-review.txt) · [Inspect the corresponding JSON](fictional-review.json)

## Engineering work

The project combines Turkish and English evidence retrieval, PDF and TXT parsing, a Flask review interface, public job-board ingestion and repeatable CPU fine-tuning experiments. The Space container has passed a Linux build and HTTP inference check in GitHub Actions.

The [public Hugging Face demo](https://huggingface.co/spaces/rezanicgil/job-radar-evidence) uses a Static Space. It processes documents in the visitor's browser and offers shared-term retrieval or optional multilingual semantic search. The server-based Docker build remains available for local deployments.

The published research classifier trained on 69 synthetic pairs. A separate English job-sentence selector trained on 3,943 deduplicated SkillSpan sentences plus 390 weakly labelled employer bullets and reached 75.5% F1 on its 2,404-sentence test split. On November 9, 2026, 47 employer boards returned 417 Türkiye-location postings. The project obtained readable descriptions for all 108 postings selected by the technical title filter, spanning 23 employers. Python appeared in 48 postings from 16 employers. [Download the underlying observations](https://huggingface.co/datasets/rezanicgil/turkiye-software-job-market)

## A decision based on evaluation

On 30 synthetic development cases inspired by ten employers, the published classifier matched 14 reference labels and missed all ten partial cases. The same evidence yielded different predictions across Turkish and English versions in 17 cases. The public demo asks applicants to verify passages and can export their decisions with exact wording and page references. Independent human validation and broader Türkiye source coverage remain open.

A second experiment fine-tuned multilingual MiniLM on 1,027 English–Turkish documentation pairs from 34 files. On 721 pairs from ten other files, it found the Turkish translation first for 674 English queries, up from 669 before training. On ten job conditions searched against 30 fictional CV passages, every target passage kept its original rank. The model is available as a research release. [Download the retriever](https://huggingface.co/rezanicgil/python-tr-en-retriever) · [Inspect the per-condition results](../reports/translation-retrieval.json)

## CV project entry

Built and published a bilingual CV evidence-review tool on Hugging Face. Fine-tuned a multilingual evidence classifier, evaluated it on requirements from ten employers, and shipped a local English job-sentence selector with 75.5% test F1 on SkillSpan.

## Reproduce and inspect

- [Training release](../releases/match-pilot/README.md)
- [Pair-encoder development results](../reports/pair-v2.json)
- [Similarity baseline](../reports/similarity-challenge.json)
- [Published classifier](https://huggingface.co/rezanicgil/job-radar-evidence-mentions-v3)
- [Employer-sourced evaluation](../reports/source-pairs-dev.json)
- [Market sources and counts](../reports/skill-mentions-2026-11-09T182408Z.md)
- [Public browser review workflow check](https://github.com/rezanicgil/job-radar-evidence/actions/runs/42670837783)
- [Container verification](https://github.com/rezanicgil/job-radar-evidence/actions/runs/42670837616)
