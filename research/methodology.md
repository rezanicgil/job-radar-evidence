# CV evidence matching · Experiment protocol

## Decision and intended use

Help an applicant compare a CV to a specific posting. Report confirmed coverage of required technical conditions, quoted evidence and unresolved conditions. Keep location, preferred qualifications and eligibility constraints visible separately. Evaluate extraction, evidence retrieval, matching and the final coverage calculation independently. Manual requirement/passage pairs measure only matching.

## Data and review

Start with original fictional examples and document their provenance. Maintain a dataset card covering composition, languages, generation, intended uses and known gaps, following [Datasheets for Datasets](https://arxiv.org/abs/1803.09010). Annotate exact posting and CV spans, compound conditions and evidence strength. [SkillSpan](https://aclanthology.org/2022.naacl-main.366/) informs span annotation for English job postings. Its labels do not establish applicant fit.

Two reviewers independently label a sample before adjudication. Record class counts, agreement, Cohen's kappa, disputed examples and guideline revisions. Reserve reviewed, naturalistic evaluation cases with documented permission. Keep all variants sharing a CV, posting or template family in one split, including translations and paraphrases. Check near duplicates before freezing splits. Treat all previously inspected pilot cases as development data.

Reviewers each save private JSONL rows with an `id`, `label` and verbatim `evidence` from the supplied CV passage. Use null evidence for an unverified case when no relevant passage exists. Compare the completed files locally using `python scripts/reviewer_agreement.py packet.jsonl first.jsonl second.jsonl`. The script reports raw agreement, Cohen's kappa and disagreements for adjudication. A null kappa indicates that the expected chance agreement is one. Place private review outputs under the ignored `runs/` directory.

The web form also exports a single saved decision. Share the example link so another reviewer can assess the same passage independently. Add `--allow-partial` to compare incomplete files. The report shows how many examples each reviewer assessed and how many they have in common. Agreement uses only the overlap. Report the count alongside the proportion because people who stop early may review a different mix of cases.

## Comparisons and selection

For an external whole-document check, use two ranking directions. For a given CV, compare jobs with different source labels and ask whether the higher-labelled job receives a higher score. For a given job, repeat the comparison across CVs. Give a score tie half credit. Average within each eligible group first, then across groups, so a frequently repeated CV does not dominate the result. Report each pair of label levels separately. ConFit also examines retrieval from both sides of the résumé–job matching problem. [ConFit](https://arxiv.org/abs/2401.16349)

The pinned external dataset contains 6,241 training rows and 1,759 test rows. All 71 test job descriptions are unseen in training, but 476 of 477 distinct test CVs recur in training. Six training pairs have conflicting labels. The source files provide document-level labels and do not document evaluator identity or agreement. The CV-only comparison uses the average training label of each CV and a global fallback for an unseen CV. TF-IDF learns its vocabulary and document frequencies from distinct training documents. Both neural encoders use cosine similarity after pooling all document chunks of up to 126 content tokens. The benchmark measures agreement with the source ordering. It cannot establish who performed a task in a CV passage or validate an applicant's chance of being hired. [Source dataset revision](https://huggingface.co/datasets/cnamuangtoun/resume-job-description-fit/tree/08978e21714984bb417547d2c0f9b477f5298163) · [Evaluation script](../scripts/evaluate_external_fit.py)

To collect decisions interactively, run `python scripts/label_packet.py packet.jsonl runs/reviewer-a`. Each completed answer is saved immediately. The same command resumes an interrupted review. Give the second reviewer a separate directory. The agreement script accepts these directories in place of JSONL files.

Run the skill-presence baseline, an untuned multilingual instruction model with a fixed prompt, then the same checkpoint with a supervised adapter. Record immutable model and data revisions, environment, prompt, seeds, hyperparameters, training time, memory and hardware. Inspect the upstream license and measure a short local run before selecting a checkpoint. [LoRA](https://arxiv.org/abs/2106.09685) is a candidate for efficient adaptation. Check feasibility on the available GPU.

Tune on development families only. Select by development macro-F1 with supported-class precision reported alongside it. Freeze the candidate, comparator and evaluation rules before opening the test set. Report per-class precision, recall and F1, and the fraction of unsupported or partial cases incorrectly promoted to supported. Report family-bootstrap intervals for paired metric differences when there are enough independent families. Show counts for every slice, including Turkish, English, mixed passages and cross-language pairs.

For behavioral tests, vary one condition at a time while preserving the rest. Include any/all, negation, experience duration, local/production and technology name collisions. Require irrelevant changes to names and contact details to preserve predictions. These are project-specific tests inspired by [CheckList](https://aclanthology.org/2020.acl-main.442/).

## Product and release

Evaluate whole documents including extraction errors, quotations that do not support the claim, coverage-score error against adjudication, PDF parsing failures and inference latency. Keep personal uploads out of training and feedback by default. Distinguish a quoting error from a passage that is quoted faithfully but interpreted incorrectly.

Promote a fine-tuned model only when held-out evidence shows improved matching over the strongest comparator and the false-support rate does not increase. Report inconclusive or negative experiments. Publish code, reproducible training commands, split manifests, licensing scope, a dataset card, a model card and evaluation results. Use a versioned Hugging Face demo with public feedback on fictional examples.
