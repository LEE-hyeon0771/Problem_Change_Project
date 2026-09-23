Task: Build a complete 핵심단어장 (core wordbook) for the passage below.

Inputs:
- passage: $passage
Context:
- passage analysis: $analysis_json
- include phrases/idioms: $include_phrases
- max synonyms/antonyms per sense: $max_related

Candidate words already detected in the passage (server-side, after removing basic vocabulary):
$candidate_words

How to use the candidate list:
- It is a coverage floor, not a ceiling.
- Cover EVERY candidate that a Korean high school student would need to study.
- Drop a candidate ONLY if it is a proper noun or genuinely basic vocabulary.
- Add anything the list missed: multi-word phrases, idioms, phrasal verbs, and collocations
  carrying meaning in this passage (only when include phrases/idioms is true).
- Target at least $min_entries entries. If the passage genuinely supports more, return more.

Per-entry requirements:
- headword: dictionary base form (e.g. "reduce", not "reduces").
- surface_form: the exact form as it appears in the passage.
- importance: "core" for words central to understanding the passage, "supporting" otherwise.
- cefr: estimated level (A1~C2), or "" when unsure.
- passage_meaning_ko: the sense used in THIS passage, in Korean.
- example_sentence: the passage sentence containing the word, copied verbatim.
- senses: one object per distinct sense. This is the most important field — do not collapse it.
  - The FIRST sense must be the one used in this passage.
  - Then add the word's other common senses that a Korean high school student is likely
    to meet in exams. Most content words have 2~3 such senses; return them all.
  - Return a single sense ONLY when the word genuinely has one sense at this level.
  - A word used as more than one part of speech (e.g. "load" as noun and verb,
    "free" as adjective and verb) MUST get one sense object per part of speech.
  - Each sense needs pos, meaning_ko, meaning_en, synonyms, antonyms.
  - Synonyms/antonyms belong to THAT sense only. The noun sense and the verb sense
    of the same word do not share synonyms.
  - At most $max_related synonyms and $max_related antonyms per sense.
  - Every synonym/antonym needs word, meaning_ko, and pos.

Synonym/antonym range (important):
- Do NOT restrict yourself to one difficulty band. Span the full range for each sense.
- Fill the allowed slots in this order, so the most useful ones survive a small $max_related:
  1) the common high-school synonym a student already half-knows,
  2) a mid-frequency academic synonym they will meet in exams,
  3) a precise academic near-synonym, with `nuance` explaining how it differs.
- Use every available slot when genuine options exist. Stop early only when the word
  truly has no further real synonym — never pad the list with loose associations.
- The same rule applies to antonyms. A word with no genuine antonym gets an empty list.

Ordering:
- Return entries in the order the words first appear in the passage.

Return JSON only.
