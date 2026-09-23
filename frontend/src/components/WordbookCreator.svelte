<script>
  import WordCard from './wordbook/WordCard.svelte';
  import { normalizePrefix, samplePassage } from '../lib/problemUtils.js';
  import { saveWordbook, streamWordbook } from '../lib/api/index.js';

  export let apiPrefix = '/api/v1';
  export let onSaved = () => {};

  const defaultForm = {
    passage: '',
    include_phrases: true,
    max_related: 4
  };

  let form = { ...defaultForm };
  let isLoading = false;
  let errorMessage = '';
  let result = null;
  let partialEntries = [];
  let progressMessage = '';
  let entrySearch = '';
  let coreOnly = false;
  let usedPayload = null;
  let saveTitle = '';
  let saveState = 'idle'; // idle | saving | saved
  let saveError = '';

  // 생성이 끝나기 전에도 1차 결과를 먼저 보여 줍니다.
  $: entries = result?.entries || partialEntries;
  $: filteredEntries = filterEntries(entries, entrySearch, coreOnly);
  $: uncovered = result?.meta?.uncovered_candidates || [];
  $: notice = result?.meta?.notice || '';

  function filterEntries(list, search, onlyCore) {
    const needle = search.trim().toLowerCase();
    return list.filter((entry) => {
      if (onlyCore && entry.importance !== 'core') {
        return false;
      }
      if (!needle) {
        return true;
      }
      const haystack = [
        entry.headword,
        entry.surface_form,
        entry.passage_meaning_ko,
        ...(entry.senses || []).flatMap((sense) => [
          sense.meaning_ko,
          sense.meaning_en,
          ...(sense.synonyms || []).map((item) => item.word),
          ...(sense.antonyms || []).map((item) => item.word)
        ])
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(needle);
    });
  }

  function fillSample() {
    form = { ...form, passage: samplePassage };
  }

  function resetResult() {
    result = null;
    partialEntries = [];
    usedPayload = null;
    saveTitle = '';
    saveState = 'idle';
    saveError = '';
    progressMessage = '';
  }

  function clearAll() {
    form = { ...defaultForm };
    errorMessage = '';
    entrySearch = '';
    coreOnly = false;
    resetResult();
  }

  async function buildWordbook() {
    errorMessage = '';
    resetResult();

    if (!form.passage.trim()) {
      errorMessage = '지문을 먼저 입력해 주세요.';
      return;
    }

    const payload = {
      passage: form.passage.trim(),
      include_phrases: form.include_phrases,
      max_related: Number(form.max_related) || 4
    };

    isLoading = true;
    progressMessage = '요청을 준비하고 있습니다...';

    try {
      result = await streamWordbook(apiPrefix, payload, {
        onStatus: (event) => {
          if (event?.message) {
            progressMessage = event.message;
          }
        },
        onPartial: (event) => {
          // 1차 정리 결과를 먼저 화면에 올려 체감 대기 시간을 줄입니다.
          if (Array.isArray(event?.entries)) {
            partialEntries = event.entries;
          }
          if (event?.message) {
            progressMessage = event.message;
          }
        }
      });
      usedPayload = payload;
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : '요청 처리 중 알 수 없는 오류가 발생했습니다.';
    } finally {
      isLoading = false;
      progressMessage = '';
      partialEntries = [];
    }
  }

  async function useWordbook() {
    if (!result || !usedPayload || saveState !== 'idle') {
      return;
    }

    saveState = 'saving';
    saveError = '';

    try {
      await saveWordbook(apiPrefix, { title: saveTitle.trim(), request: usedPayload, result });
      saveState = 'saved';
      onSaved();
    } catch (err) {
      saveState = 'idle';
      saveError = err instanceof Error ? err.message : '저장에 실패했습니다.';
    }
  }
</script>

<main class="workspace">
  <section class="panel controls">
    <div class="field">
      <div class="label-row">
        <label for="wordbookPassage">영어 지문</label>
        <small>최소 60 words 권장</small>
      </div>
      <textarea
        id="wordbookPassage"
        bind:value={form.passage}
        placeholder="단어를 뽑을 지문을 입력하세요..."
        rows="14"
      ></textarea>
    </div>

    <div class="field">
      <div class="label-row">
        <label for="maxRelated">뜻당 동의어 / 반의어 개수</label>
        <small>최대 {form.max_related}개</small>
      </div>
      <input id="maxRelated" type="range" min="1" max="8" bind:value={form.max_related} />
    </div>

    <div class="field toggles option-toggles">
      <label><input type="checkbox" bind:checked={form.include_phrases} /> 숙어·연어 포함</label>
    </div>

    <div class="actions">
      <button class="primary" type="button" disabled={isLoading} on:click={buildWordbook}>
        {isLoading ? '분석 중...' : '단어장 만들기'}
      </button>
      <button class="ghost" type="button" on:click={fillSample}>샘플 채우기</button>
      <button class="ghost danger" type="button" on:click={clearAll}>초기화</button>
    </div>
  </section>

  <section class="panel result">
    <div class="result-head">
      <h2>핵심단어장</h2>
      {#if entries.length}
        <span class="wordbook-count">{filteredEntries.length} / {entries.length} 단어</span>
      {/if}
    </div>

    {#if isLoading}
      {#if progressMessage}
        <p class="stream-status"><span class="stream-dot"></span>{progressMessage}</p>
      {/if}

      {#if partialEntries.length}
        <!-- 1차 결과 미리보기. 보강 패스가 끝나면 최종 결과로 교체됩니다. -->
        <p class="stream-partial-note">1차 정리 결과입니다. 빠진 단어를 보강하는 중이에요.</p>
        <div class="wordbook-list">
          {#each partialEntries as entry}
            <article class="word-card is-partial">
              <header class="word-head">
                <h3>{entry.headword}</h3>
                {#if entry.cefr}<span class="word-cefr">{entry.cefr}</span>{/if}
              </header>
              {#if entry.passage_meaning_ko}
                <p class="word-passage-meaning"><span>이 지문에서</span>{entry.passage_meaning_ko}</p>
              {/if}
            </article>
          {/each}
        </div>
      {:else}
        <div class="skeleton">
          <span></span>
          <span></span>
          <span></span>
          <span></span>
        </div>
      {/if}
    {:else if errorMessage}
      <div class="error-box">
        <strong>요청 실패</strong>
        <p>{errorMessage}</p>
      </div>
    {:else if result}
      {#if notice}
        <div class="exam-message-box">
          <strong>뜻 정보가 비어 있습니다</strong>
          <p>{notice}</p>
        </div>
      {/if}

      {#if uncovered.length}
        <div class="exam-message-box">
          <strong>정리되지 않은 단어 {uncovered.length}개</strong>
          <p>{uncovered.join(', ')}</p>
        </div>
      {/if}

      <div class="use-bar" class:done={saveState === 'saved'}>
        {#if saveState === 'saved'}
          <div class="use-bar-text">
            <strong>개인DB에 저장했습니다</strong>
            <p>단어 {entries.length}개가 개인DB &gt; 단어장에 보관되었습니다.</p>
          </div>
          <button class="ghost" type="button" on:click={resetResult}>새로 만들기</button>
        {:else}
          <div class="use-bar-text">
            <strong>이 단어장을 쓰시겠어요?</strong>
            <p>"사용"을 눌러야 개인DB에 저장됩니다. 저장해야 단어 암기지를 만들 수 있습니다.</p>
          </div>
          <input
            class="use-title-input"
            type="text"
            bind:value={saveTitle}
            placeholder="단어장 제목 (비우면 지문 앞부분)"
          />
          <button class="primary" type="button" disabled={saveState === 'saving'} on:click={useWordbook}>
            {saveState === 'saving' ? '저장 중...' : '사용'}
          </button>
        {/if}
      </div>

      {#if saveError}
        <div class="error-box">
          <strong>저장 실패</strong>
          <p>{saveError}</p>
        </div>
      {/if}

      <div class="wordbook-tools">
        <label>
          검색
          <input type="text" bind:value={entrySearch} placeholder="단어, 뜻, 동의어 검색" />
        </label>
        <label class="wordbook-toggle">
          <input type="checkbox" bind:checked={coreOnly} /> 핵심어만 보기
        </label>
      </div>

      {#if filteredEntries.length}
        <div class="wordbook-list">
          {#each filteredEntries as entry}
            <WordCard {entry} detailed />
          {/each}
        </div>
      {:else}
        <div class="empty-box">
          <h3>검색 결과가 없습니다</h3>
          <p>검색어를 지우거나 필터를 해제해 주세요.</p>
        </div>
      {/if}
    {:else}
      <div class="empty-box">
        <h3>아직 단어장이 없습니다</h3>
        <p>좌측에 지문을 넣고 단어장 만들기를 실행하면 핵심단어가 여기에 정리됩니다.</p>
      </div>
    {/if}
  </section>
</main>
