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

The November 9, 2026 collection includes 417 Türkiye-location posting URLs from 47 employer boards. The title filter selected 108 technical roles from 23 employers. All 108 descriptions were readable. Python appeared in 48 of those postings across 16 employers. React Native appeared in 12 postings from one employer. [Explore the report](https://rezanicgil-job-radar-evidence.static.hf.space/#market)

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

For selected Workday postings, `source_requisition` and `source_listed_date` preserve the employer's requisition ID and Workday start date when available. Rows without these fields have null values. The snapshot date records when this project observed the posting.

The last collected snapshot on each Türkiye calendar day supplies the records. Collection dates record when the job board was observed. They do not establish publication dates, hiring outcomes or total demand in Türkiye. The release contains factual listing metadata and project-generated classifications. The descriptions remain on the linked employer websites. [Collection code and dated source files](https://github.com/rezanicgil/job-radar-evidence)
