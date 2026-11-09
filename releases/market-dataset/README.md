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
  - config_name: direct_employer_observations
    data_files:
      - split: observations
        path: direct/observations.jsonl
dataset_info:
  - config_name: technologies
    features:
      - name: date
        dtype: date32
      - name: technology
        dtype: string
      - name: postings_mentioning
        dtype: int64
      - name: readable_postings
        dtype: int64
      - name: employers_mentioning
        dtype: int64
      - name: represented_employers
        dtype: int64
      - name: top_employer
        dtype: string
      - name: distinct_descriptions
        dtype: int64
      - name: distinct_descriptions_mentioning
        dtype: int64
      - name: top_employer_mentions
        dtype: int64
      - name: other_employer_mentions
        dtype: int64
      - name: other_employer_postings
        dtype: int64
      - name: compared_with_date
        dtype: date32
      - name: new_board
        dtype: int64
      - name: recovered_board
        dtype: int64
      - name: entered_sample
        dtype: int64
      - name: gained_on_shared
        dtype: int64
      - name: removed_board
        dtype: int64
      - name: unavailable_board
        dtype: int64
      - name: left_sample
        dtype: int64
      - name: lost_on_shared
        dtype: int64
---

# Türkiye software job market observations

Use this dataset to compare how often a technology appears in postings and how widely it appears across employers in the Job Radar panel. Every observation has a collection date. Choose a single date before computing shares. A posting can appear on several dates.

The November 9, 2026 collection includes 461 Türkiye-location posting URLs from 51 employer boards. The title filter selected 141 technical roles from 27 employers. All 141 descriptions were readable. Python appeared in 59 of those postings across 18 employers. React Native appeared in 12 postings from one employer. [Explore the report](https://rezanicgil-job-radar-evidence.static.hf.space/#market)

The 22:37 Türkiye-time collection expands the technical title filter to cover seven previously unselected postings. These include Java engineering, digital image processing, blockchain operations and DevSecOps. The earlier collection on the same date selected 108 postings. This change in coverage reflects a filter revision.

The 23:00 Türkiye-time collection adds Yassir, CRENNO and Lucida AI. Seven readable postings explicitly list Türkiye as an alternative location. The 129 URLs contain 124 distinct employer and normalized-description pairs. Five Lucida AI Flutter URLs share one description. A URL count measures published listings and does not establish headcount.

The 23:15 collection measures qualification sections in 46 of the 129 readable postings and preference sections in 13. The CRENNO mobile posting mentions Flutter under qualifications and Git under additional skills. Section-specific shares use only the postings with that type of measured section.

The 23:53 collection includes the Accenture Türkiye board. The embedded and firmware selection now includes eight readable postings at two employers. Ten additional vocabulary entries cover embedded and Android platform technologies. Earlier observations only measure names in their original vocabulary.

The `direct_employer_observations` configuration records 13 dated listings from eight employer sites. Its selected qualifications, preferences and source links can support manual CV review. Several positions may share a careers-page URL. These observations remain outside the automated posting and employer denominators.

On November 10 at 00:00 Türkiye time the panel was collected again, about seven minutes after the November 9 observation at 23:53. All 141 technical URLs were readable at both times and all 60 technology counts were unchanged. Select one date to estimate prevalence. Stacking the two dates repeats the same listings.

At 00:59 Türkiye time on November 10 the panel covered 145 readable roles at 27 employers. Recognizing SDET, SAP ABAP developer, low-code application developer and system administrator titles added four previously excluded URLs from the same 461-posting inventory. Python appeared in 60/145 (41.4%) compared with 59/141 (41.8%) before the title filter changed. This difference reflects the selection rule. Percentages describe the sampled boards. Dated report filenames use UTC.

## Reproduce a percentage

```python
from datasets import load_dataset

jobs = load_dataset("rezanicgil/turkiye-software-job-market", "postings", split="observations")
day = jobs.filter(lambda r: str(r["date"])[:10] == "2026-11-09" and r["description_status"] == "readable")
matches = day.filter(lambda r: "Python" in r["technologies"])
print(f"{len(matches)}/{len(day)} postings ({len(matches) / len(day):.1%})")
print(len(set(matches["employer"])), "of", len(set(day["employer"])), "employers")
```

## Fields and sampling

The postings configuration contains one row per employer posting URL per date. It includes the reported location, employer, title, title-based role categories and a link back to the posting. Rows outside the technical title filter have `description_status = not_selected`. Their technology list is null. A readable description with no tracked mentions has an empty list. Retrieval failures retain their status and a null list.

The technologies configuration contains one row per tracked name per date, including zero counts. Both denominators use readable technical postings. A mention can come from duties, required qualifications, preferences or company context. A role can have multiple categories. The sample depends on panel membership, board availability and title matching. Separately reviewed employer pages in the Space are outside these counts.

The same rows contain `distinct_descriptions_mentioning` and `distinct_descriptions`. Divide the former by the latter to count a repeated description once within an employer. Both fields are null when any readable posting on that date lacks a digest. For the November 9 cross-platform mobile selection, Flutter occurs in 6/7 posting URLs (85.7%) and 2/3 distinct descriptions (66.7%). Role-specific figures use the postings configuration.

The technology rows also identify the employer with the most postings mentioning that technology. Ties use employer name order. To recompute the share after excluding that employer, divide `other_employer_mentions` by `other_employer_postings` when the denominator is positive. These fields are null for a technology with no mentions. In the November 9 snapshot, excluding Sezzle removes all 12 React Native mentions and leaves 126 readable postings from other employers.

For a technology measured on two successive observation dates, the technology row stores the earlier date in `compared_with_date`. The eight count fields describe URLs entering or leaving the readable sample, or gaining or losing the mention on a URL readable on both dates. New, removed, recovered and unavailable boards are distinguished from changes on continuing boards. Adding gains and subtracting losses reproduces the change in posting mentions. These fields are null on the first date or when the technology was not measured on both dates. A listing can leave the sample because of changes in source availability, location or title filtering.

For Lever and Ashby, `location_scope = listed_alternative` identifies Türkiye in an explicitly listed secondary location. Other entries leave this field null. `description_sha256` is a SHA-256 digest of the measured description text with whitespace normalized. Group by employer and this digest to examine repeated copy. Older observations without a digest leave the field null.

For selected Workday postings, `source_requisition` and `source_listed_date` preserve the employer's requisition ID and Workday start date when available. Rows without these fields have null values. The snapshot date records when this project observed the posting.

The `sections` field contains recognized qualification and preference headings from structured Lever descriptions and the reviewed Lucida AI (Workable) and CRENNO (SmartRecruiters) layouts, along with the technology names found under each heading. An explicitly marked preference within a CRENNO qualification list is grouped under its preference phrase. A null value means the posting was not measured by this parser. An empty list means it found no recognized heading. For a section-specific percentage, count each posting once and use only postings with that section type as the denominator. A qualification may list alternatives or give examples. Its heading alone cannot establish that every technology mentioned is mandatory.

The last collected snapshot on each Türkiye calendar day supplies the records. Collection dates record when the job board was observed. They do not establish publication dates, hiring outcomes or total demand in Türkiye. The release contains factual listing metadata and project-generated classifications. The descriptions remain on the linked employer websites. [Collection code and dated source files](https://github.com/rezanicgil/job-radar-evidence)
