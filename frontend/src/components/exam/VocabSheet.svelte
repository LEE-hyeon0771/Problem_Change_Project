<script>
  import { formatDate } from '../../lib/problemUtils.js';

  export let savedWordbooks = [];
  export let libraryLoading = false;
  export let onRefresh = () => {};

  // --- 단어 암기지 ---
  let vocabTitle = '영어 단어 암기장';
  let vocabSelectedUids = [];
  let vocabSheetMode = 'study'; // study = 뜻 보임, quiz = 뜻 빈칸
  let vocabShowSynonyms = true;
  let vocabCoreOnly = false;
  let vocabColumns = 2;
  let vocabItems = [];
  let vocabError = '';
  let vocabMessage = '';

  $: vocabPool = savedWordbooks.filter((record) => (record.result?.entries || []).length);
  $: vocabSelectedCount = vocabSelectedUids.length;

  function toggleWordbook(uid) {
    vocabSelectedUids = vocabSelectedUids.includes(uid)
      ? vocabSelectedUids.filter((selected) => selected !== uid)
      : [...vocabSelectedUids, uid];
  }

  function selectAllWordbooks() {
    vocabSelectedUids = vocabPool.map((record) => record.wordbook_uid);
  }

  function clearWordbooks() {
    vocabSelectedUids = [];
  }

  function buildVocabSheet() {
    vocabError = '';
    vocabMessage = '';

    if (!vocabSelectedUids.length) {
      vocabError = '단어 암기지에 넣을 단어장을 하나 이상 선택해 주세요.';
      return;
    }

    const selected = new Set(vocabSelectedUids);
    const seen = new Set();
    const collected = [];

    for (const record of vocabPool) {
      if (!selected.has(record.wordbook_uid)) {
        continue;
      }
      for (const entry of record.result?.entries || []) {
        if (vocabCoreOnly && entry.importance !== 'core') {
          continue;
        }
        // 여러 단어장에 같은 단어가 있으면 한 번만 싣습니다.
        const key = (entry.headword || '').trim().toLowerCase();
        if (!key || seen.has(key)) {
          continue;
        }
        seen.add(key);
        collected.push(entry);
      }
    }

    if (!collected.length) {
      vocabError = '선택한 단어장에서 조건에 맞는 단어를 찾지 못했습니다.';
      return;
    }

    vocabItems = collected;
    vocabMessage = `${collected.length}개 단어로 암기지를 구성했습니다.`;
  }

  function clearVocabSheet() {
    vocabItems = [];
    vocabError = '';
    vocabMessage = '';
  }

  function primaryMeaning(entry) {
    return entry.passage_meaning_ko || entry.senses?.[0]?.meaning_ko || '';
  }

  function primaryPos(entry) {
    const sense = entry.senses?.[0];
    return sense?.pos_ko || sense?.pos || '';
  }

  function relatedWords(entry, kind) {
    const sense = entry.senses?.[0];
    return (sense?.[kind] || []).map((item) => item.word).filter(Boolean);
  }

  function printExamPaper() {
    window.print();
  }
</script>

  <section class="panel exam-builder">
    <div class="library-head">
      <div>
        <p class="eyebrow">단어 암기지 구성</p>
        <h2>단어 암기지</h2>
        <p>개인DB에 저장한 단어장을 골라 학생 배포용 암기지와 단어 시험지를 만듭니다.</p>
      </div>
      <button class="ghost" type="button" on:click={onRefresh} disabled={libraryLoading}>
        {libraryLoading ? '불러오는 중...' : '저장소 새로고침'}
      </button>
    </div>

    <div class="exam-controls">
      <label>
        암기지 제목
        <input type="text" bind:value={vocabTitle} placeholder="영어 단어 암기장" />
      </label>
      <label>
        단 수
        <select bind:value={vocabColumns}>
          <option value={1}>1단</option>
          <option value={2}>2단</option>
          <option value={3}>3단</option>
        </select>
      </label>
      <label class="answer-toggle">
        <input type="checkbox" bind:checked={vocabShowSynonyms} />
        동의어·반의어 표시
      </label>
      <label class="answer-toggle">
        <input type="checkbox" bind:checked={vocabCoreOnly} />
        핵심어만
      </label>
    </div>

    <fieldset class="exam-type-field">
      <div class="exam-field-head">
        <legend>출력 형식</legend>
      </div>
      <div class="segmented" role="group" aria-label="암기지 형식">
        <button type="button" class:active={vocabSheetMode === 'study'} on:click={() => (vocabSheetMode = 'study')}>
          암기장 (뜻 보임)
        </button>
        <button type="button" class:active={vocabSheetMode === 'quiz'} on:click={() => (vocabSheetMode = 'quiz')}>
          시험지 (뜻 빈칸)
        </button>
      </div>
    </fieldset>

    <fieldset class="exam-type-field">
      <div class="exam-field-head">
        <legend>사용할 단어장</legend>
        <div class="exam-type-actions">
          <button class="ghost" type="button" on:click={selectAllWordbooks}>전체 선택</button>
          <button class="ghost" type="button" on:click={clearWordbooks}>전체 해제</button>
        </div>
      </div>
      {#if vocabPool.length}
        <div class="exam-type-grid" role="group" aria-label="사용할 단어장">
          {#each vocabPool as record (record.wordbook_uid)}
            <button
              type="button"
              class:selected={vocabSelectedUids.includes(record.wordbook_uid)}
              aria-pressed={vocabSelectedUids.includes(record.wordbook_uid)}
              on:click={() => toggleWordbook(record.wordbook_uid)}
            >
              <span>{record.title || '제목 없는 단어장'}</span>
              <small>{record.entry_count}단어 · {formatDate(record.created_at)}</small>
            </button>
          {/each}
        </div>
      {:else}
        <div class="empty-box">
          <h3>저장된 단어장이 없습니다</h3>
          <p>핵심단어장 화면에서 단어장을 만들고 "사용"을 눌러 주세요.</p>
        </div>
      {/if}
    </fieldset>

    <div class="actions exam-actions">
      <button class="primary" type="button" on:click={buildVocabSheet}>암기지 만들기</button>
      <button class="ghost" type="button" on:click={printExamPaper} disabled={!vocabItems.length}>인쇄 / PDF 저장</button>
      <button class="ghost danger" type="button" on:click={clearVocabSheet} disabled={!vocabItems.length}>비우기</button>
    </div>

    <p class="exam-pool-note">
      선택한 단어장 {vocabSelectedCount}개 · 저장된 단어장 전체 {savedWordbooks.length}개
    </p>

    {#if vocabError}
      <div class="error-box">
        <strong>암기지 처리 실패</strong>
        <p>{vocabError}</p>
      </div>
    {/if}
    {#if vocabMessage}
      <div class="exam-message-box">
        <strong>암기지 상태</strong>
        <p>{vocabMessage}</p>
      </div>
    {/if}
  </section>

  {#if vocabItems.length}
    <section class="exam-shell vocab-shell">
      <article class="exam-paper">
        <header class="exam-paper-head">
          <p>영어 어휘 영역</p>
          <h2>{vocabTitle || '영어 단어 암기장'}{vocabSheetMode === 'quiz' ? ' 단어 시험지' : ''}</h2>
          <small>
            총 {vocabItems.length}단어
            {#if vocabSheetMode === 'quiz'}· 이름 __________ 점수 ______{/if}
          </small>
        </header>

        <ol class="vocab-sheet" style={`column-count:${vocabColumns}`}>
          {#each vocabItems as entry, index}
            <li class="vocab-row">
              <span class="vocab-no">{index + 1}</span>
              <div class="vocab-body">
                <div class="vocab-word-line">
                  <strong>{entry.headword}</strong>
                  {#if primaryPos(entry)}<span class="vocab-pos">{primaryPos(entry)}</span>{/if}
                </div>

                {#if vocabSheetMode === 'study'}
                  <p class="vocab-meaning">{primaryMeaning(entry)}</p>
                  {#if vocabShowSynonyms}
                    {#if relatedWords(entry, 'synonyms').length}
                      <p class="vocab-related"><span class="syn">동</span>{relatedWords(entry, 'synonyms').join(', ')}</p>
                    {/if}
                    {#if relatedWords(entry, 'antonyms').length}
                      <p class="vocab-related"><span class="ant">반</span>{relatedWords(entry, 'antonyms').join(', ')}</p>
                    {/if}
                  {/if}
                {:else}
                  <p class="vocab-blank"></p>
                  {#if vocabShowSynonyms && relatedWords(entry, 'synonyms').length}
                    <p class="vocab-hint">힌트: {relatedWords(entry, 'synonyms')[0]}</p>
                  {/if}
                {/if}
              </div>
            </li>
          {/each}
        </ol>
      </article>

      {#if vocabSheetMode === 'quiz'}
        <article class="exam-explanation-paper">
          <header class="exam-paper-head">
            <p>정답</p>
            <h2>{vocabTitle || '영어 단어 암기장'} 정답지</h2>
            <small>총 {vocabItems.length}단어</small>
          </header>
          <ol class="vocab-sheet" style={`column-count:${vocabColumns}`}>
            {#each vocabItems as entry, index}
              <li class="vocab-row">
                <span class="vocab-no">{index + 1}</span>
                <div class="vocab-body">
                  <div class="vocab-word-line">
                    <strong>{entry.headword}</strong>
                    {#if primaryPos(entry)}<span class="vocab-pos">{primaryPos(entry)}</span>{/if}
                  </div>
                  <p class="vocab-meaning">{primaryMeaning(entry)}</p>
                </div>
              </li>
            {/each}
          </ol>
        </article>
      {/if}
    </section>
  {:else}
    <section class="panel exam-empty">
      <h3>아직 구성된 암기지가 없습니다</h3>
      <p>사용할 단어장을 고르고 암기지 만들기를 누르면 학생 배포용 암기지가 생성됩니다.</p>
    </section>
  {/if}
