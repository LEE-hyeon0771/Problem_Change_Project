<script>
  /**
   * 단어 카드 하나. 핵심단어장 생성 화면과 개인DB 단어장 화면이 공유합니다.
   *
   * 두 화면의 표시 밀도가 달라서 `detailed` 로 구분합니다.
   *   detailed=true  (생성 화면)  지문 예문, 영어 정의, 사용 노트, 동의어 품사·뉘앙스까지
   *   detailed=false (개인DB)     표제어·뜻·동의어 단어만 — 접힌 목록이라 밀도를 낮춥니다
   */
  export let entry;
  export let detailed = false;
</script>

<article class="word-card">
  <header class="word-head">
    <h3>{entry.headword}</h3>
    {#if entry.surface_form && entry.surface_form !== entry.headword}
      <span class="word-surface">지문 형태: {entry.surface_form}</span>
    {/if}
    <span class="word-badge" class:supporting={entry.importance !== 'core'}>
      {entry.importance === 'core' ? '핵심' : '보조'}
    </span>
    {#if entry.cefr}
      <span class="word-cefr">{entry.cefr}</span>
    {/if}
  </header>

  {#if entry.passage_meaning_ko}
    <p class="word-passage-meaning">
      <span>이 지문에서</span>
      {entry.passage_meaning_ko}
    </p>
  {/if}

  {#if detailed && entry.example_sentence}
    <p class="word-example">{entry.example_sentence}</p>
  {/if}

  {#if entry.senses?.length}
    <ol class="sense-list">
      {#each entry.senses as sense}
        <li>
          <div class="sense-head">
            <span class="pos-badge">{sense.pos_ko || sense.pos}</span>
            <strong>{sense.meaning_ko}</strong>
          </div>
          {#if detailed && sense.meaning_en}
            <p class="sense-en">{sense.meaning_en}</p>
          {/if}
          {#if detailed && sense.usage_note}
            <p class="sense-note">{sense.usage_note}</p>
          {/if}

          {#if sense.synonyms?.length}
            <div class="relation-row">
              <span class="relation-label syn">동의어</span>
              <div class="relation-chips">
                {#each sense.synonyms as item}
                  <span class="relation-chip" title={detailed ? item.nuance || '' : undefined}>
                    <b>{item.word}</b>
                    {#if detailed && item.pos}<i>{item.pos}</i>{/if}
                    {#if item.meaning_ko}<em>{item.meaning_ko}</em>{/if}
                  </span>
                {/each}
              </div>
            </div>
          {/if}

          {#if sense.antonyms?.length}
            <div class="relation-row">
              <span class="relation-label ant">반의어</span>
              <div class="relation-chips">
                {#each sense.antonyms as item}
                  <span class="relation-chip" title={detailed ? item.nuance || '' : undefined}>
                    <b>{item.word}</b>
                    {#if detailed && item.pos}<i>{item.pos}</i>{/if}
                    {#if item.meaning_ko}<em>{item.meaning_ko}</em>{/if}
                  </span>
                {/each}
              </div>
            </div>
          {/if}
        </li>
      {/each}
    </ol>
  {/if}
</article>
