Task: Propose synonym substitutions that make a familiar passage feel unfamiliar,
WITHOUT changing its meaning.

Why: Korean high school students often memorize passages from past exams.
Replacing a few words defeats rote recall and forces real reading.
The passage must still read as natural, exam-quality English.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- how many swaps to propose: $swap_count

Hard rules:
- Output JSON only.
- Propose EXACTLY $swap_count swaps (fewer only if the passage genuinely cannot support more).
- `original` must be copied VERBATIM from the passage, including capitalization.
- `original` must appear EXACTLY ONCE in the passage. Skip any word that repeats.
- Keep the same part of speech and grammatical form
  (plural stays plural, past tense stays past tense, -ing stays -ing).
- The sentence must stay grammatical after substitution. Check the article too
  ("a" vs "an" must still fit the new word; if it would not, choose another word).
- Preserve register. Academic prose stays academic; do not drop to casual wording.
- Preserve collocation. Replace only where the new word is idiomatic in that phrase.

NEVER swap these:
- Discourse connectives: however, but, yet, nevertheless, therefore, thus,
  consequently, for example, for instance, such as, moreover, furthermore, in addition.
  These are the answer evidence for order/insertion/irrelevant items.
- Proper nouns, numbers, technical terms whose meaning would shift.
- Basic vocabulary every learner knows (the, people, make, good...).
- The thesis word the whole passage is about, if replacing it would change the topic.

Spread the swaps across the passage. Aim for roughly one per sentence rather than
clustering several in one sentence.

Difficulty control - this decides WHICH words you pick and WHAT you replace them with.
Word SELECTION (which passage words to target):
- easy: content words a student already knows (CEFR A2~B1) - adverbs, common verbs, plain nouns.
  Do not touch the passage's key argumentative terms.
- mid: B1~B2 words, including one or two that carry part of the argument.
- hard: B2~C1 words, and deliberately include the passage's topic-bearing nouns.
  Changing these is what makes a memorized passage feel unfamiliar.
REPLACEMENT choice (what to put in):
- easy: the most frequent everyday synonym; the reader does not slow down at all.
  e.g. typically -> usually, rewards -> benefits
- mid: a mid-frequency academic synonym; the reader pauses briefly but never doubts meaning.
  e.g. incentive -> motivation, influence -> affect
- hard: a precise, lower-frequency near-synonym from academic register. Genuinely
  interchangeable HERE, but not a word the student would have produced.
  e.g. exploitation -> utilization, capture -> sequestration, protection -> mitigation
Level discipline:
- Do NOT mix levels. At easy a single C1 replacement ruins the level;
  at hard a merely common synonym wastes the slot.
- If a word has no synonym at the required level, skip it and pick a different word
  rather than dropping to an easier replacement.

For each swap, `note` briefly states in Korean why it is safe
(품사·어감·연어가 유지되는 이유). One short phrase is enough.

Return JSON only.
