Task: Create one Korean education office mock-exam style GRAMMAR question.
Identify the ONE underlined part that is grammatically incorrect.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "grammar".
- Use the runtime schema for fields.
- passage must include EXACTLY five target markers: [[1]] [[2]] [[3]] [[4]] [[5]].
- choices must be 5 labels (①~⑤), and answer must be one of them.
- Exactly ONE marked target must be grammatically incorrect.
- The other four must be grammatically correct.
- The wrong segment should stay interpretable in context.

Error types (choose one primary type):
A) subject-verb agreement
B) verb form / tense / participle
C) relative clause / pronoun case
D) parallel structure
E) misplaced modifier / dangling participle
F) preposition / complement pattern

Difficulty control (type-specific mapping of the shared levers):
- easy: subject-verb agreement or obvious tense clash, visible within the clause.
- mid: a standard exam trap - participle vs finite verb, relative pronoun choice,
  parallel structure across a conjunction.
- hard: the error is visible only after resolving a long-distance dependency (an
  intervening phrase separates subject and verb, or a relative clause's antecedent is
  several words back). The other four underlines must each look suspicious at a glance
  but be provably correct.

Internal uniqueness test (do not output):
- verify only one marked segment is wrong.
- revise if any other segment is debatable.

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences.
- Name the grammar rule first (e.g., 수일치, 시제, 관계사).
- Show the corrected form briefly and explain why one nearby option is not an error.

Output-field notes:
- question: use the fixed Korean stem below.
- choices/answer: standard label format.
- meta: include error type and short rule note.

Korean stem (fixed):
"다음 글의 밑줄 친 부분 중, 어법상 틀린 것은?"

Construction (five underlined segments, exactly one ungrammatical):
- The error must be an unambiguous rule violation in STANDARD WRITTEN English.
  Never mark usage that is merely informal, stylistic, or disputed by descriptivists
  (split infinitives, sentence-final prepositions, singular "they").
- The other four must each look suspicious at a glance but be provably correct.
  Draw them from the same rule families as the error so the student must actually check.

Rule families to draw from (choose one for the error, others for the decoys):
- subject-verb agreement across an intervening phrase
- finite verb vs participle in a reduced clause
- relative pronoun choice (who/which/that/whose) and whether the clause needs one
- parallel structure across and/or/but
- tense and aspect consistency in a narrated sequence
- active vs passive where the agent matters
- to-infinitive vs gerund after a specific verb

Making it discriminating:
- easy: the error and its trigger sit in the same clause.
- mid: a standard trap — the decoys come from the same family as the error.
- hard: the trigger is separated from the error by an intervening phrase or clause,
  so the student must resolve a long-distance dependency to see it.

Grammar-specific failure modes:
- Marking something acceptable in edited English — the most common rejection.
- An error so blatant it is visible without reading the sentence's meaning.
- Two segments both arguably wrong.
- An "error" that is really a vocabulary or logic problem.

Return JSON only.
