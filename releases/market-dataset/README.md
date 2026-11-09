---
language:
  - en
  - tr
configs:
  - config_name: postings
    default: true
    data_files:
      - split: observations
        path: postings/*.jsonl
  - config_name: technologies
    data_files:
      - split: observations
        path: technologies/*.jsonl
---

# Türkiye software job market observations

Use this dataset to compare how often a technology appears in postings and how widely it appears across employers in the Job Radar panel. Every observation has a collection date. Choose a single date before computing shares. A posting can appear on several dates.

The November 9, 2026 collection includes 443 Türkiye-location posting URLs from 50 employer boards. The title filter selected 129 technical roles from 26 employers. All 129 descriptions were readable. Python appeared in 51 of those postings across 17 employers. React Native appeared in 12 postings from one employer. [Explore the report](https://rezanicgil-job-radar-evidence.static.hf.space/#market)

The 22:37 Türkiye-time collection expands the technical title filter to cover seven previously unselected postings. These include Java engineering, digital image processing, blockchain operations and DevSecOps. The earlier collection on the same date selected 108 postings. This change in coverage reflects a filter revision.

The 23:00 Türkiye-time collection adds Yassir, CRENNO and Lucida AI. Seven readable postings explicitly list Türkiye as an alternative location. The 129 URLs contain 124 distinct employer and normalized-description pairs. Five Lucida AI Flutter URLs share one description. A URL count measures published listings and does not establish headcount.

## Reproduce a percentage

```python
from datasets import load_dataset

jobs = load_dataset("rezanicgil/turkiye-software-job-market", "postings", split="observations")
day = jobs.filter(lambda r: r["date"] == "2026-11-09" and r["description_status"] == "readable")
matches = day.filter(lambda r: "Python" in r["technologies"])
print(f"{len(matches)}/{len(day)} postings ({len(matches) / len(day):.1%})")
print(len(set(matches["employer"])), "of", len(set(day["employer"])), "employers")
```

## Fields and sampling

The postings configuration contains one row per employer posting URL per date. It includes the reported location, employer, title, title-based role categories and a link back to the posting. Rows outside the technical title filter have `description_status = not_selected`. Their technology list is null. A readable description with no tracked mentions has an empty list. Retrieval failures retain their status and a null list.

The technologies configuration contains one row per tracked name per date, including zero counts. Both denominators use readable technical postings. A mention can come from duties, required qualifications, preferences or company context. A role can have multiple categories. The sample depends on panel membership, board availability and title matching. Separately reviewed employer pages in the Space are outside these counts.

The same rows contain `distinct_descriptions_mentioning` and `distinct_descriptions`. Divide the former by the latter to count a repeated description once within an employer. Both fields are null when any readable posting on that date lacks a digest. For the November 9 cross-platform mobile selection, Flutter occurs in 6/7 posting URLs (85.7%) and 2/3 distinct descriptions (66.7%). Role-specific figures use the postings configuration.

The technology rows also identify the employer with the most postings mentioning that technology. Ties use employer name order. To recompute the share after excluding that employer, divide `other_employer_mentions` by `other_employer_postings` when the denominator is positive. These fields are null for a technology with no mentions. In the November 9 snapshot, excluding Sezzle removes all 12 React Native mentions and leaves 114 readable postings from other employers.

For Lever and Ashby, `location_scope = listed_alternative` identifies Türkiye in an explicitly listed secondary location. Other entries leave this field null. `description_sha256` is a SHA-256 digest of the measured description text with whitespace normalized. Group by employer and this digest to examine repeated copy. Older observations without a digest leave the field null.

For selected Workday postings, `source_requisition` and `source_listed_date` preserve the employer's requisition ID and Workday start date when available. Rows without these fields have null values. The snapshot date records when this project observed the posting.

The `sections` field contains recognized qualification and preference headings from structured Lever descriptions, along with the technology names found under each heading. A null value means the posting was not measured by this parser. An empty list means it found no recognized heading. For a section-specific percentage, count each posting once and use only postings with that section type as the denominator. A qualification may list alternatives or give examples. Its heading alone cannot establish that every technology mentioned is mandatory.

The last collected snapshot on each Türkiye calendar day supplies the records. Collection dates record when the job board was observed. They do not establish publication dates, hiring outcomes or total demand in Türkiye. The release contains factual listing metadata and project-generated classifications. The descriptions remain on the linked employer websites. [Collection code and dated source files](https://github.com/rezanicgil/job-radar-evidence)
