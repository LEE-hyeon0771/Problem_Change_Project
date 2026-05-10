<script>
  import {
    buildPassageSegments,
    formatMetaValue,
    getInsertionBody,
    getInsertionGivenSentence,
    getSummaryBody,
    getSummaryText,
    isImplicitType,
    isInsertionType,
    isSummaryType,
    parseSummaryChoice,
    toMarkerDisplay,
    usesEmbeddedChoices
  } from '../lib/problemUtils.js';

  export let problem = null;
  export let showMeta = true;
</script>

{#if problem}
  <article class="item-card">
    <h3>{String(problem.type || '').toUpperCase()}</h3>
    <p class="question">{problem.question}</p>

    {#if isInsertionType(problem.type) && getInsertionGivenSentence(problem.type, problem.passage, problem.meta)}
      <section class="given-box">
        <p class="given-label">주어진 문장</p>
        <p class="given-text">{getInsertionGivenSentence(problem.type, problem.passage, problem.meta)}</p>
      </section>
    {/if}

    {#if isSummaryType(problem.type)}
      {#if getSummaryBody(problem.type, problem.passage)}
        <div class="passage">{getSummaryBody(problem.type, problem.passage)}</div>
      {/if}
      {#if getSummaryBody(problem.type, problem.passage) && getSummaryText(problem.type, problem.passage)}
        <p class="summary-divider">↓</p>
      {/if}
      {#if getSummaryText(problem.type, problem.passage)}
        <section class="summary-box">
          <p class="summary-label">Summary Sentence</p>
          <p class="summary-text">{getSummaryText(problem.type, problem.passage)}</p>
        </section>
      {/if}
    {:else}
      <div class="passage">
        {#each buildPassageSegments(problem.type, getInsertionBody(problem.type, problem.passage, problem.meta), problem.choices) as segment}
          {#if segment.kind === 'target'}
            {#if isImplicitType(problem.type)}
              <span class="passage-target">{segment.text}</span>
            {:else}
              <span class="passage-target-group"><span class="passage-marker">{toMarkerDisplay(segment.marker)}</span> <span class="passage-target">{segment.text}</span></span>
            {/if}
          {:else}
            <span>{segment.text}</span>
          {/if}
        {/each}
      </div>
    {/if}

    {#if usesEmbeddedChoices(problem.type)}
      <p class="choice-note">선택지는 지문 내부 표식 사용 • 정답 {problem.answer?.label}</p>
    {:else}
      <ul class="choice-list">
        {#each problem.choices || [] as choice}
          <li class:correct={choice.label === problem.answer?.label}>
            <span class="choice-label">{choice.label}</span>
            {#if isSummaryType(problem.type)}
              {@const pair = parseSummaryChoice(choice.text)}
              {#if pair}
                <p class="summary-choice">(A) {pair.a} / (B) {pair.b}</p>
              {:else}
                <p>{choice.text}</p>
              {/if}
            {:else}
              <p>{choice.text}</p>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}

    <section class="explanation">
      <p class="answer-line">답: {problem.answer?.label || '-'}</p>
      {#if problem.explanation}
        <p>{problem.explanation}</p>
      {/if}
    </section>

    {#if showMeta && problem.meta && Object.keys(problem.meta).length}
      <div class="meta-grid">
        {#each Object.entries(problem.meta) as [key, value]}
          <div>
            <small>{key}</small>
            <p>{formatMetaValue(value)}</p>
          </div>
        {/each}
      </div>
    {/if}
  </article>
{/if}
