# Job Radar Evidence

An applicant comparing their CV with a software vacancy can inspect relevant CV passages, decide whether each requirement is supported, and see the denominator behind their coverage score. A second view lets them inspect technology mentions by role and employer in a dated Türkiye job snapshot.

## Engineering work

The project combines Turkish and English evidence retrieval, PDF and TXT parsing, a Flask review interface, public job-board ingestion and repeatable CPU fine-tuning experiments. The Space container has passed a Linux build and HTTP inference check in GitHub Actions.

The [public Hugging Face demo](https://huggingface.co/spaces/rezanicgil/job-radar-evidence) uses a Static Space. It processes documents in the visitor's browser and offers shared-term retrieval or optional multilingual semantic search. The server-based Docker build remains available for local deployments.

The synthetic training release contains 54 examples from 18 scenario families. The first broader technology snapshot includes 61 readable descriptions from title-tagged postings. Readers can inspect source links and employer counts. The snapshot reflects the tracked sources on November 9, 2026.

## A decision based on evaluation

On nine synthetic development examples, the calibrated similarity baseline returned six correct labels but missed all three fully supported cases. The 54-example adapted pair encoder returned three correct labels and two false claims of full support. The demo therefore retrieves candidate evidence and asks the applicant to confirm coverage. Independent evaluation and broader source coverage remain open.

## CV project entry

Built an open-source bilingual CV evidence-review prototype, fine-tuned multilingual encoders on 54 synthetic requirement–CV pairs, and shipped a Docker-tested interface with source-linked technology counts for a Türkiye software-jobs snapshot.

## Reproduce and inspect

- [Training release](../releases/match-pilot/README.md)
- [Pair-encoder development results](../reports/pair-v2.json)
- [Similarity baseline](../reports/similarity-challenge.json)
- [Market sources and counts](../reports/skill-mentions-2026-11-09T142802Z.md)
- [Container verification](https://github.com/rezanicgil/job-radar-evidence/actions/runs/42635859051)
