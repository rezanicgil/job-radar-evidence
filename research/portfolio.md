# Job Radar Evidence

An applicant comparing their CV with a software vacancy can inspect relevant CV passages, decide whether each requirement is supported, and see the denominator behind their coverage score. A second view lets them inspect technology mentions by role and employer in a dated Türkiye job snapshot.

In the fictional demo, the CV documents 30 months developing control software with C++ and the job asks for 36. The applicant can fully document the Python reporting requirement. With one of two required conditions fully supported, the review reports 50% coverage and shows the six-month shortfall beside the selected passage. [Read the exported report](fictional-review.txt) · [Inspect the corresponding JSON](fictional-review.json)

## Try a real requirement with a fictional CV

In the [market view](https://rezanicgil-job-radar-evidence.static.hf.space/#market), select **Backend**, find **NewMind AI · Backend Developer** under **Reviewed requirements**, and choose **Review these conditions with my CV**. The [employer posting](https://apply.workable.com/newmindai/j/7E86986DCA/) names several ORM tools as examples and separately asks for gRPC expertise. If the posting changes, the [dated review](../data/role_reviews.jsonl) preserves the selected conditions.

Paste this fictional Turkish CV passage: **“Sipariş hizmetinde TypeORM ile veri modellerini oluşturdum ve şema değişikliklerini yönettim.”** It describes modelling order-service data and managing schema changes with TypeORM. Select that passage for the ORM condition and mark it supported. Leave gRPC unverified: the passage says nothing about communication between services.

| What the applicant sees | How to interpret it |
|---|---|
| 1 supported, 1 unverified; 50% coverage | One of two selected conditions has evidence. The rest of the posting was not assessed. |
| TypeORM mentioned, Prisma absent | The employer gives examples. A reviewer can accept relevant TypeORM work without requiring every listed tool. |
| No gRPC evidence | Add a real service-integration example if one exists. The tool cannot infer that the applicant lacks the skill. |

## Engineering work

The project combines Turkish and English evidence retrieval, PDF and TXT parsing, a Flask review interface, public job-board ingestion and repeatable CPU fine-tuning experiments. The Space container has passed a Linux build and HTTP inference check in GitHub Actions.

The [public Hugging Face demo](https://huggingface.co/spaces/rezanicgil/job-radar-evidence) uses a Static Space. It processes documents in the visitor's browser and offers shared-term retrieval or optional multilingual semantic search. The server-based Docker build remains available for local deployments.

The published research classifier trained on 69 synthetic pairs. A separate English job-sentence selector trained on 3,943 deduplicated SkillSpan sentences plus 390 weakly labelled employer bullets and reached 75.5% F1 on its 2,404-sentence test split. In the November 10, 2026 snapshot, all 53 boards responded. The title filter selected 151 of 473 Türkiye-location postings across 29 employers, and all 151 descriptions were readable. Python appeared in 61 (40.4%). A mention can describe a preference or company context. [Download the underlying observations](https://huggingface.co/datasets/rezanicgil/turkiye-software-job-market)

## A decision based on evaluation

On 30 synthetic development cases inspired by ten employers, the published classifier matched 14 reference labels and missed all ten partial cases. The same evidence yielded different predictions across Turkish and English versions in 17 cases. The public demo asks applicants to verify passages and can export their decisions with exact wording and page references. Independent human validation and broader Türkiye source coverage remain open.

A second experiment fine-tuned multilingual MiniLM on 1,027 English–Turkish documentation pairs from 34 files. On 721 pairs from ten other files, it found the Turkish translation first for 674 English queries, up from 669 before training. On ten job conditions searched against 30 fictional CV passages, every target passage kept its original rank. The model is available as a research release. [Download the retriever](https://huggingface.co/rezanicgil/python-tr-en-retriever) · [Inspect the per-condition results](../reports/translation-retrieval.json)

## What another engineer can reproduce

The [Duration Lab](https://rezanicgil-job-radar-evidence.static.hf.space/duration-lab.html) is a separate experiment: it asks whether a marked time expression describes prior experience. Its multilingual encoder is frozen; only the linear classifier is trained. The [public training features and scripts](https://huggingface.co/datasets/rezanicgil/job-radar-duration-evidence/tree/b7c3274779896b5109b28680e6a69ccaa6d35206) let another engineer regenerate both the weights and all 75 predictions from the employer-held-out experiment. Balanced accuracy was 86.7% against assistant-drafted labels. In a [separate challenge of 18 real English sentences](../reports/duration-implicit-external.json), the model got 12 right and misread both company-history examples as candidate experience. This is why its output never sets an applicant's coverage automatically.

## CV project entry

Built and published a bilingual CV evidence-review tool on Hugging Face. Fine-tuned a multilingual evidence classifier, evaluated it on requirements from ten employers, and shipped a local English job-sentence selector with 75.5% test F1 on SkillSpan.

## Reproduce and inspect

- [Training release](../releases/match-pilot/README.md)
- [Pair-encoder development results](../reports/pair-v2.json)
- [Similarity baseline](../reports/similarity-challenge.json)
- [Published classifier](https://huggingface.co/rezanicgil/job-radar-evidence-mentions-v3)
- [Employer-sourced evaluation](../reports/source-pairs-dev.json)
- [Market sources and counts](../reports/skill-mentions-2026-11-10T073313967913Z.md)
- [Public browser review workflow check](https://github.com/rezanicgil/job-radar-evidence/actions/runs/42670837783)
- [Container verification](https://github.com/rezanicgil/job-radar-evidence/actions/runs/42670837616)
