# Portal Submission Keyword Analysis

This directory contains notebooks and outputs for our keyword analysis of portal submissions in Ohio, Missouri, Wisconsin, and Michigan. The goal of this analysis is to find a representative set of keywords in the submissions that can be used in our topic modeling and visualization pipeline.

## Methodology
We combine [spaCy](https://spacy.io/) models with principled manual filtering. Specifically, the workflow to produce `{oh, mo, wi, mi}_{filtered, accepted}.csv` involved (for each state):
1. Loading the raw submission text (including titles) from the August 10 data dump (not included), removing named entities (places, people, and the like) from each submission, and finding lemmatized noun chunks (with common stop words removed) in each of these de-entitied submissions. (See `Top N keywords.ipynb`.)
2. Filtering the lemmatized noun chunks using previously developed filter lists. The filter lists are path-dependent: we started without a filter list in MI; applied the MI filter list to MO; applied the MI and MO filter lists to WI; and applied the MI, MO, and WI filter lists to OH. (See `Top N keywords.ipynb`.)
3. Generating counts of the filtered noun chunks, filtering further using a count cutoff (15 for MI; 10 for WI; 5 for MO and OH), and emitting `{oh, mo, wi, mi}_noun_chunks.csv`.  (See `Top N keywords.ipynb`.)
4. Manually loading noun chunks into Excel and tagging chunks for filtering that matched the following criteria, which occasionally overlap:
  * **Generic political term**: A term broadly related to government, politics, redistricting, or redistricting commissions. _(examples: "government", "state senate", "constituent", "commission", "democracy")_.
  * **Generic geographic term**: A term that could refer to a broad range of geographic or geopolitical entities _(examples: "state", "county", "town", "municipality", "district line")_. This does _not_ include geographic terms that are likely to refer to one region of a state or geographic features that are more prevalent in some regions than others _(examples: "shoreline", "artery", "river")_.
  * **Generic term**: A term that might be meaningful in some contexts but is too generic to be particularly valuable for tagging purposes _(examples: "person", "thing", "place", "adult", "kind")_.
  * **Not interpretable**: A nonsense term generated as an artifact of aggressive filtering and lemmatization, a term that has no obvious relevance in the context of redistricting, or an unlikely/awkward/redundant combination of an adjective and a noun produced by lemmatization _(examples: "family home", "thank", "wife", "s")_. A few terms that would otherwise fall under this category were corrected manually—for instance, cases where "media" was lemmatized to "medium" were fixed in Wisconsin. These cases are explicitly noted.
  * **Variant**: An obvious spelling variant _(example: we prefer "homeowner" to "home owner")_. This does _not_ include synonyms _(example: "child" vs. "kid")_.
5. Splitting manually filtered noun chunks (in `{oh, mo, wi, mi}_noun_chunks_labeled.csv`) into `filtered` and `accepted` CSVs. (See `Keyword sieve.ipynb`.)

Additionally, we include the union of the four `accepted` CSVs in `wi_mi_mo_oh_union_accepted.csv`. See `Keyword sieve.ipynb`.)
