Task: Extend an existing 핵심단어장 that missed some words.

A previous pass built a wordbook for this passage, but the words below were left out.
Return entries ONLY for the missing words. Do not repeat words already covered.

Inputs:
- passage: $passage
Context:
- max synonyms/antonyms per sense: $max_related

Already covered headwords (do NOT return these again):
$covered_words

Missing words to cover now:
$missing_words

Rules:
- Return one entry per missing word, in the order given.
- Apply the same per-entry requirements as the main wordbook task:
  headword, surface_form, importance, cefr, passage_meaning_ko, example_sentence, senses.
- Each sense carries its own part of speech, Korean meaning, English definition,
  and sense-matched synonyms/antonyms (at most $max_related each).
- Span the full range for synonyms: common → mid-frequency academic → precise near-synonym,
  in that order, using every slot that has a genuine option.
- The first sense is the passage sense; add the word's other common exam senses too,
  one sense object per part of speech.
- If a missing word is a proper noun or genuinely basic vocabulary that no student
  needs to study, omit it rather than padding the list with a weak entry.

Return JSON only.
