---
title: Job Radar Evidence
emoji: 🔎
colorFrom: green
colorTo: blue
sdk: static
app_file: index.html
license: apache-2.0
---

# Job Radar Evidence

Review CV evidence locally in your browser. Use a fictional example, paste text or open a PDF or TXT. The default search ranks passages by shared terms. Optional multilingual semantic retrieval downloads a quantized MiniLM model to the browser. Your CV and job text stay on your device. Only reviewer-confirmed technical conditions enter the coverage score.

Choose **Try a bilingual example** to review a fictional candidate with 30 months of C++ experience against a 36-month requirement. Confirm passages for this and a Python reporting requirement, then download the review with its denominator and page references.

The completed example shows 50% coverage across two required conditions. [Read the sample report](https://github.com/rezanicgil/job-radar-evidence/blob/main/research/fictional-review.txt) · [Inspect its JSON](https://github.com/rezanicgil/job-radar-evidence/blob/main/research/fictional-review.json)

The market view shows dated technology mentions by posting or employer. The [research results](https://rezanicgil-job-radar-evidence.static.hf.space/model.html) let you compare the published classifier's predictions with project-authored labels and inspect language-dependent errors. [Dataset](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot) · [Open-source experiments](https://github.com/rezanicgil/job-radar-evidence) · [Review fictional examples](https://rezanicgil-job-radar-evidence.static.hf.space/annotate.html)

The bilingual retrieval experiment used 1,027 technical translation pairs. All ten target CV passages kept their ranks on the original job-condition diagnostic. [Download the research retriever](https://huggingface.co/rezanicgil/python-tr-en-retriever) · [Download the Türkiye market data](https://huggingface.co/datasets/rezanicgil/turkiye-software-job-market)
