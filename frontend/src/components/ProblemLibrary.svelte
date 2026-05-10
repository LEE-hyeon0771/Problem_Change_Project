<script>
  import ProblemView from './ProblemView.svelte';
  import { formatDate, normalizeDisplayText, previewText, typeLabel, typeOptions } from '../lib/problemUtils.js';

  export let savedProblems = [];
  export let libraryLoading = false;
  export let libraryError = '';
  export let onRefresh = () => {};

  let libraryType = 'all';
  let librarySearch = '';
  let selectedRecord = null;

  $: filteredProblems = filterSavedProblems(savedProblems, libraryType, librarySearch);
  $: modalProblem = selectedRecord?.result || null;

  function filterSavedProblems(records, type, search) {
    const needle = search.trim().toLowerCase();
    return records.filter((record) => {
      const result = record?.result || {};
      const matchesType = type === 'all' || record.problem_type === type;
      const haystack = [
        record.problem_type,
        result.question,
        result.passage,
        result.answer?.text,
        result.explanation
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return matchesType && (!needle || haystack.includes(needle));
    });
  }

  function openProblem(record) {
    selectedRecord = record;
  }

  function closeModal() {
    selectedRecord = null;
  }
</script>

<main class="library-view">
  <section class="panel library-panel">
    <div class="library-head">
      <div>
        <p class="eyebrow">내 문제 저장소</p>
        <h2>내 문제 저장소</h2>
        <p>생성했던 변형문제를 최신순으로 보관합니다. 카드를 누르면 큰 화면으로 다시 볼 수 있습니다.</p>
      </div>
      <button class="ghost" type="button" on:click={onRefresh} disabled={libraryLoading}>
        {libraryLoading ? '불러오는 중...' : '새로고침'}
      </button>
    </div>

    <div class="library-tools">
      <label>
        유형
        <select bind:value={libraryType}>
          <option value="all">전체 유형</option>
          {#each typeOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>
      <label>
        검색
        <input type="text" bind:value={librarySearch} placeholder="지문, 질문, 해설 검색" />
      </label>
    </div>

    {#if libraryError}
      <div class="error-box">
        <strong>저장소 조회 실패</strong>
        <p>{libraryError}</p>
      </div>
    {:else if libraryLoading}
      <div class="skeleton library-skeleton">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>
    {:else if filteredProblems.length}
      <div class="library-grid">
        {#each filteredProblems as record}
          <button class="library-card" type="button" on:click={() => openProblem(record)}>
            <span class="library-type">{typeLabel(record.problem_type)}</span>
            <span class="library-date">{formatDate(record.created_at)}</span>
            <strong>{record.result?.question || '문항 지시문 없음'}</strong>
            <p>{previewText(record.result?.passage, 170)}</p>
            <small>attempt {record.attempt_no} · {normalizeDisplayText(record.passage_id)}</small>
          </button>
        {/each}
      </div>
    {:else}
      <div class="empty-box">
        <h3>저장된 문제가 없습니다</h3>
        <p>문제 만들기 화면에서 문항을 생성하면 이곳에 자동으로 쌓입니다.</p>
      </div>
    {/if}
  </section>
</main>

{#if modalProblem}
  <div class="modal-layer">
    <button class="modal-backdrop" type="button" aria-label="모달 닫기" on:click={closeModal}></button>
    <section class="modal-panel" role="dialog" aria-modal="true" aria-label="저장된 문제 상세">
      <div class="modal-head">
        <div>
          <p class="eyebrow">{typeLabel(selectedRecord.problem_type)} · {formatDate(selectedRecord.created_at)}</p>
          <h2>저장된 변형문제</h2>
        </div>
        <button class="ghost" type="button" on:click={closeModal}>닫기</button>
      </div>

      <div class="modal-item">
        <ProblemView problem={modalProblem} />
      </div>
    </section>
  </div>
{/if}
