---
title: Job Radar Evidence Review
emoji: 🔎
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
license: apache-2.0
---

# Job Radar Evidence Review

Compare job requirements against a fictional CV or submit a text PDF or TXT. Enter one condition per line. The multilingual encoder ranks candidate passages and the reviewer decides which conditions count toward required technical coverage.

The server processes the CV for the current request. Uploaded files are removed after text extraction. Please use fictional examples in public bug reports and community discussions. Include the example input, expected passage and observed output when submitting feedback.

The demo uses a pinned multilingual MiniLM encoder for retrieval. Experimental fine-tuned classifiers are being evaluated separately. The synthetic training pilot and the market inventory are separate artifacts.
