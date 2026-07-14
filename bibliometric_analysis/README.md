# Bibliometric Analysis

`bibliometric_analysis.xlsx` is the full per-reference bibliometric table for the thesis's Literature Review chapter: 152 references, each matched against the [OpenAlex](https://api.openalex.org) API by DOI (132 references) or exact-title search (6 references), recording title, authors, year, journal, first-author country, and the OpenAlex global citation count as of 10 July 2026.

- **Sheet "Bibliometric Table"**: one row per reference, including its OpenAlex ID and DOI so every value can be independently cross-checked.
- **Sheet "Summary"**: aggregate counts (matched/unmatched, total citations).

See Chapter 2, Section 2.7 of the thesis for the analysis and discussion, and Appendix A for how this file relates to the rest of the supplementary data.
