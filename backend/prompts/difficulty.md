## DIFFICULTY SPECIFICATION (applies to every item type)

Current level: **$difficulty**

Difficulty is NOT a vague feeling. It is produced by five measurable levers.
Follow the row for the current level EXACTLY. Do not average the levels, and do not
soften `hard` because the item feels unfair — a hard item must still be uniquely solvable.

### L1. Answer paraphrase distance
How much of the passage's own wording the CORRECT option may reuse.

- **easy**: the key reuses 2~3 content words from the passage verbatim, and reads close to
  a sentence a careful reader could point at. Recognition should be enough.
- **mid**: at most 1 content word verbatim, AND the key must fuse ideas from **two different
  sentences** — it may not be a restatement of any single sentence. Recognition is not enough;
  the student must combine.
- **hard**: ZERO content words reused. Express the idea with hypernyms, nominalization,
  or a different part of speech. A student who only pattern-matches vocabulary must fail.

(Content word = not an article, preposition, pronoun, auxiliary, or conjunction.)

### L2. Distractor–key distance
How close the wrong options sit to the correct one.

- **easy**: 3 of the 4 distractors are wrong on TOPIC. A student who grasped the gist
  eliminates them instantly.
- **mid**: 2 distractors share the passage topic and fail on SCOPE or POLARITY.
  The other 2 may be topic-level wrong.
- **hard**: ALL 4 distractors share the topic AND the register of the key.
  Each must fail on exactly ONE of these dimensions, and a different one where possible:
  `scope` (too broad/narrow) · `polarity` (reverses stance) · `agent` (who acts)
  · `degree` (how much/always vs sometimes) · `causal direction` (cause↔effect swapped).
  **Do not use off-topic distractors at hard level — they are free eliminations.**

### L3. Evidence span
How much text must be integrated to justify the key.

- **easy**: one sentence contains the whole justification.
- **mid**: exactly two sentences, and they must contribute DIFFERENT parts of the key
  (e.g. one supplies the claim, the other the condition or contrast).
- **hard**: three or more sentences, including at least one from a different part of
  the passage than the others. The key must not be derivable from any single sentence.

### L4. Option vocabulary level (CEFR)

- **easy**: A2~B1 only. No option may contain a word above B1.
- **mid**: B1~B2.
- **hard**: B2~C1. At least 2 options must contain a C1-level word.

### L5. Attractive-distractor count
Options a mid-level student would seriously consider before rejecting.

- **easy**: 1
- **mid**: 2
- **hard**: 3 or more

### Mandatory self-audit (compute internally, do not output)

Before returning, verify each item and revise if any fails:

1. Count the passage content words reused in the key → matches L1?
   At `mid`, also confirm the key is not a restatement of any single sentence.
2. For each distractor, name the single dimension it fails on → matches L2?
3. Count the sentences needed to justify the key → matches L3?
4. Scan every option for words above the L4 band → any violation?
5. Count genuinely attractive distractors → matches L5?

**The three levels must be visibly different.** If your `easy` and `mid` drafts would look
interchangeable to a teacher, the `mid` draft is wrong — push it toward fusion (L1/L3).

If a lever cannot be satisfied without breaking answer uniqueness, **uniqueness wins** —
but then adjust another lever so the overall level still lands where it should.
