# Coverage review · Türkiye software engineering

The [board inventory](inventory-2026-11-09.json) is a dated collection of posting metadata. Run `python scripts/market_inventory.py` to collect from Lever, Ashby and Greenhouse. Keep the manually reviewed five-title skills pilot separate from this broader title inventory.

All TR-location records are retained, including business roles and unmatched titles. Area counts are provisional title tags and can overlap. Unmatched titles require review before estimating software-job coverage. The location filter uses explicit country or a limited city dictionary and does not resolve every multi-office or remote arrangement. Counts of zero describe this source panel only.

The current panel overrepresents technology employers with hosted recruiting boards. Expand recruitment coverage in defense, industrial automation, electronics, automotive, telecom, finance, enterprise software and healthcare. Record employer sector independently of role family. Add direct employer sites and broaden local job boards where permitted. Track source health, reviewed title recall and distinct employers per area before ranking skills.

**Observed gap.** The board run found no embedded titles. [ATAQ's employer careers page](https://www.ataq.com.tr/kariyer) lists an embedded software engineer in Ankara. This separately observed example demonstrates a source coverage gap. It is not counted in the automated board inventory.

## Title review on the frozen snapshot

Reapplying the expanded title rules to the same 204 records tagged five previously unmatched roles. Two concern infrastructure or database reliability. Three concern quantitative development, blockchain or payments engineering. Title coverage moved from 55 to 60 on the unchanged sample. This is a retrieval count; confirming the responsibilities still requires description review.

The [direct employer register](../data/reviewed_employer_postings.jsonl) records the Ankara embedded opening, source URL and observation date separately. Its publication date is unknown. The entry cannot establish a new vacancy on the observation date or a time trend.
