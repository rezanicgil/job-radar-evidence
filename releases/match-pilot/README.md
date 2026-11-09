---
language:
  - tr
  - en
license: apache-2.0
size_categories:
  - 1K<n<10K
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
  - config_name: posting_modality
    data_files:
      - split: validation
        path: posting_modality.jsonl
  - config_name: section_training_index
    data_files:
      - split: train
        path: section_training_index.jsonl
  - config_name: turkish_section_index
    data_files:
      - split: validation
        path: turkish_section_index.jsonl
  - config_name: technology_connectives
    data_files:
      - split: validation
        path: technology_connectives.jsonl
  - config_name: connective_actors
    data_files:
      - split: validation
        path: connective_actors.jsonl
  - config_name: python_translation_index
    data_files:
      - split: train
        path: python-translation-index-train.jsonl
      - split: validation
        path: python-translation-index-validation.jsonl
  - config_name: duration_weak
    data_files:
      - split: train
        path: duration_weak.jsonl
  - config_name: employer_tr
    data_files:
      - split: train
        path: employer_tr.jsonl
  - config_name: requirement_switch
    data_files:
      - split: train
        path: requirement_switch_train.jsonl
      - split: validation
        path: requirement_switch.jsonl
  - config_name: compound_evidence
    data_files:
      - split: validation
        path: compound_evidence.jsonl
      - split: test
        path: compound_transfer.jsonl
  - config_name: actor_evidence
    data_files:
      - split: train
        path: actor_evidence_train.jsonl
      - split: validation
        path: actor_evidence.jsonl
  - config_name: language_switch
    data_files:
      - split: train
        path: language_switch_train.jsonl
      - split: validation
        path: language_switch.jsonl
---

# Job Radar · Bilingual CV evidence pilot

The default configuration contains 69 training pairs from 23 families and 18 development pairs from six other families. Each default family presents one job requirement and three fictional CV passages with different evidence labels. The default training split contains 23 examples per label and its validation split contains six per label. The optional configurations include controlled augmentation and additional annotations of existing passages; summing their row counts would overstate the number of independent examples.

The validation file begins with nine general challenge examples and ends with nine examples about Docker, Terraform and Prometheus. A passage can name the right technology while describing event logistics rather than engineering work. The [experiment predictions](https://github.com/rezanicgil/job-radar-evidence/blob/dba6189/reports/pair-mentions-v3.json) show where the model confused the two. The [original 54-row release](https://huggingface.co/datasets/rezanicgil/job-radar-match-pilot/tree/cb96ff522186ae77a3b9f1bada3ee32842d91b15) remains available for earlier experiments.

## How to read a row

In `technology_connectives`, each of 24 fictional passages has two versions of the same requirement. One asks for both named technologies and one accepts either. The six families cover messaging, embedded drivers, Android, cloud deployment, iOS and model training. Twelve passages demonstrate exactly one option. The reference label changes from partial to supported when the requirement changes from AND to OR in these cases. The published classifier produced the correct change on 0/12. The references are project-authored. [Predictions per pair](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/technology-connectives.json)

In `connective_actors`, each of 18 project-authored fictional CV passages mentions both named technologies. The applicant demonstrates both, one or neither in six passages each. The study reuses the six technology pairs above. Across 36 AND and OR decisions, literal mentions incorrectly awarded full support in 18 of 18 cases where the reference was partial or unverified. The released classifier did so in 16/18. Splitting the requirement by technology and classifying who performed each action reduced this to 2/18, with 26/36 decisions correct overall. These controlled examples test attribution errors. Independent reviewers have yet to evaluate the labels. [Case-level predictions](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/connective-actors.json)


The `turkish_section_index` configuration contains 96 source pointers from five technical postings on one employer's board. Section headings distinguish qualifications, communication skills and teamwork expectations. Two bullets begin with “Tercihen” and are labelled as preferences. Each row contains its source URL, line number, document fingerprint and whitespace-normalized line fingerprint. Several postings repeat the same wording. These examples were used to develop the parsing rules and represent section-based references rather than independent human judgments. [Before and after counts](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/turkish-board-sections.json)

The `section_training_index` links 390 deduplicated English job bullets to their sources in 33 Türkiye-location postings from nine employer boards. Each record identifies a bullet by its one-based position, heading and normalized text fingerprint. Qualification and preference headings supplied 361 weak positives. Benefits and employer-offer headings supplied 29 weak negatives. These labels describe the section and have no independent human skill annotations. The sample is employer-selected and weighted toward positive examples. [Aggregate word counts](https://github.com/rezanicgil/job-radar-evidence/blob/main/data/section-training-counts.json) · [Comparison with SkillSpan-only training](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/section-training.json)

The `python_translation_index` configuration indexes 1,748 English–Turkish documentation pairs from the [Python Turkish translation project](https://github.com/python/python-docs-tr/tree/caa8b1e08b8534a1e1344a82889fc6c820768a91). Each row links to a pinned source file and fingerprints both normalized texts. These are translation pairs for training a passage retriever. The CV evidence labels belong to the other configurations. The 1,027 training pairs come from 34 documents. The 721 validation pairs come from ten other documents. Translations marked fuzzy or obsolete, identical bilingual strings, and repeated texts on either side were excluded. Python documentation and translations retain their upstream terms.

To reconstruct the text pairs from the project checkout, install `polib==1.2.0` alongside the training dependencies and run `python scripts/train_translation_retrieval.py --export`. The resulting JSONL files under `runs/python-translations-*.jsonl` include both texts. Running the same script without `--export` trains and evaluates the retriever. [Training and evaluation script](https://github.com/rezanicgil/job-radar-evidence/blob/main/scripts/train_translation_retrieval.py)

The `posting_modality` view contains twelve project-authored diagnostic inputs in English and Turkish. Each row records the expected required and optional wording from the posting. The examples cover reversed clause order, groups of languages, alternatives and explicit exemption from a requirement. The paired examples in the two languages represent six constructions. These examples were written alongside the extraction rules and serve as regression checks. They do not estimate accuracy on employer postings.

The `compound_evidence` test split contains 12 fictional cases from four additional requirements covering Android uploads, firmware updates, payments and iOS accessibility. Each requirement has two necessary components and three passages. A clause classifier trained on 144 distinct clause–requirement pairs found 4/6 partial matches in the original diagnostic and 1/4 in this new split. Overall accuracy on the new split was 5/12, versus 7/12 for the released classifier. The labels come from the project authors. [Predictions per case](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/clause-attribution.json)

The `language_switch` diagnostic renders each of the same 30 source-grounded pairs in four language combinations (job/CV). These 120 views contain 30 distinct underlying cases. Translations are project-authored and lack independent review. Across the four views the released model changed its prediction for 17/30 cases. Accuracy was 13/30 for Turkish/Turkish, 16/30 for Turkish/English, 13/30 for English/Turkish and 11/30 for English/English. Keep translations in one partition whenever training or evaluating. [Results per pair](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/language-switch.json)

The training split of this configuration contains four language views for each of 15 original default-training cases. All 60 views belong to training families, separate from the 30 evaluation cases. Training source links refer to the original synthetic data; evaluation links refer to the employers that inspired the requirements. [Equal-step augmentation experiment](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/language-training.json)

The `actor_evidence` view annotates the same 18 compound cases at component level. Its 36 rows identify who performed the required action: `applicant`, `other`, or `not_stated`. These are project-authored judgments. Nonempty quotes come directly from the fictional passage, with zero-based Unicode character offsets and an exclusive end. When no one is described performing the required action, the quote and offsets are null. Do not pool these rows with the compound cases as independent observations. The released classifier marked five of six actions attributed to someone else as fully supported for the applicant. [Error breakdown](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/actor-evidence.json)

The actor training split adds 144 synthetic component queries over 48 passages from eight other scenario families. In each passage the applicant and a colleague perform different actions. Each of three target actions rotates between applicant, colleague and unstated, with 48 records per class. Family, passage and component text are disjoint from actor validation. [Training and validation confusion matrices](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/actor-swaps.json)

The actor classifier identified 8/18 applicant actions and 10/12 unstated actions on validation. Of six actions performed by others, it assigned two to the applicant and four to unstated. It recovered none of the 48 other-actor training actions either. This checkpoint should not be used to assign applicant credit.

An additional baseline used the upstream natural language inference model without task-specific training. Each action was rewritten as two claims, one about the applicant and one about another person. The model treated both claims as entailed in 21/36 cases. Requiring only the applicant claim to be entailed reduced false applicant assignments to 1/18, while recovering only 4/18 true applicant actions. The author-written prompts and these synthetic cases have not been independently reviewed. [Results and hypotheses](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/actor-entailment.json)

The `compound_evidence` diagnostic contains 18 fictional passages across six requirements. Each requirement has two mandatory components with separate project-authored evidence labels. Full coverage requires both components to be supported; a mixture of supported and unverified components yields partial coverage. The released classifier matched 10 of 18 whole-condition labels directly and 9 of 18 after classifying components and combining them. Incorrect full-support decisions rose from seven to nine. Splitting conjunctions alone did not solve the evidence attribution errors in this sample. [Comparison](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/compound-evidence.json)

The `requirement_switch` configuration contains 36 training pairs from 12 fictional passages and 24 validation pairs from eight other passages. Each passage is paired with three different requirements. The train and validation splits share no exact passage, requirement or family. A useful match score should change with the requirement even when the applicant's writing stays the same. One frozen-embedding classifier that saw only the CV got 23/30 correct on the source-grounded development split, but just 8/24 on this diagnostic. The analogous paired classifier scored 9/24 and failed to classify all three requirements correctly for any passage. These constructed cases test sensitivity to requirements. [Probe and results](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/requirement-signal.json)

| Split | Pairs | Requirement families | Supported / partial / unverified |
| --- | ---: | ---: | --- |
| Train | 69 | 23 | 23 / 23 / 23 |
| Validation | 18 | 6 | 6 / 6 / 6 |

For the requirement “Package and run a backend service with Docker”, listing Docker in a skills section receives a partial label. Describing personally building an image and running a service supports the condition. Booking a room for Docker training receives an unverified label.

`family` identifies related cases. `requirement` describes an employer's condition. `cv_passage` contains the fictional applicant's statement. `label` is the author's judgment of the passage. Supported means the passage establishes the condition, partial means it establishes a relevant component, and unverified means the condition has no supporting evidence in that passage.

## Provenance and evaluation

The optional `employer_tr` configuration adds 36 training pairs across 12 Turkish requirements informed by four employer pages. Source URLs and qualification versus preference scope accompany each record. CV passages are fictional and include Turkish and English. Labels are project judgments. The training experiment combines these records with the 69 default training pairs. None of these four source employers appear among the ten employers in the source-grounded development split.

At seed 17, the expanded classifier produced the same predicted labels as mentions-v3 on both development splits (9/18 and 14/30 correct). It recovered none of the 16 partial examples across those splits. [Experiment output](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/employer-tr.json)

The project assistant authored the examples and initial labels during dataset development. The pilot covers English, Turkish and cross-language matching. The data has no independent human adjudication. Developers have inspected validation outcomes during model development. The balanced distribution was intentional and does not estimate real-world class frequencies.

Keep related CVs, translations, rephrasings and templates together when creating new evaluation sets. The scores of models trained on this pilot are unsuitable for estimating an applicant's likelihood of getting hired. Use an independently reviewed external set for product decisions.

### What the current classifier misses

The mentions-v3 checkpoint recovered 4/6 supported examples (66.7%), 0/6 partial examples (0%) and 5/6 unverified examples (83.3%). Overall accuracy was 9/18 (50%). Each class percentage measures recall against the synthetic author labels. [Per-example predictions](https://github.com/rezanicgil/job-radar-evidence/blob/dba6189/reports/pair-mentions-v3.json)

The next collection batch contains 12 unlabeled fictional passages paired with requirements adapted from three source postings. They are available for review outside these splits. Further collection should sample independent employers and requirements across software specialties, include all four Turkish/English language directions, and prioritize passages that share a technology name while differing in responsibility or deployment experience. [Review candidates](https://github.com/rezanicgil/job-radar-evidence/blob/a7f1a6d/research/source_grounded_candidates.jsonl)

Reviewers can save one decision or a full packet in the [blind review form](https://rezanicgil-job-radar-evidence.static.hf.space/annotate.html). Once two people have independently reviewed shared examples, the local comparison tool can evaluate the frozen classifier against each set of decisions and identify disputed labels. Results on agreed cases carry their own denominator. [Command and interpretation](https://github.com/rezanicgil/job-radar-evidence/blob/main/research/methodology.md)

### Duration augmentation

The separate `duration_weak` training configuration contains 768 programmatically labeled pairs derived from eight technology names, three thresholds, four durations, technical versus administrative work, and four language directions. The same passage can support a two-year requirement and partially support a five-year requirement. These are 128 distinct CV strings and 48 distinct requirements with substantial template reuse. Treat the 768 rows as controlled augmentation, not independent observations. Administrative examples account for half of the rows.

### Source-grounded development configuration

Select `source_grounded` for 30 additional synthetic pairs. Ten selected qualifications from ten employers supplied the context for original requirement paraphrases and fictional CV passages. Each row includes the source URL, section, bullet position and normalized-text fingerprint. The project authored the three labels per family. We checked for exact family, requirement and passage overlap with training. These are development cases with related skills and synthetic author labels, without independent adjudication.

On these cases the published mentions-v3 checkpoint recovered 7/10 fully supported examples, 0/10 partial examples and 7/10 unverified examples. It incorrectly marked 9/20 partial or unverified examples as supported. [Predictions](https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/source-pairs-dev.json)

This release contains no user CV uploads or republished employer postings. Apache-2.0 applies to these original synthetic records. When reporting a label issue, include the family, the passage and the wording that supports your correction.
