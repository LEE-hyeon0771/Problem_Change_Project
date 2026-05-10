<script>
  import { onMount } from 'svelte';
  import MockExamBuilder from './components/MockExamBuilder.svelte';
  import ProblemCreator from './components/ProblemCreator.svelte';
  import ProblemLibrary from './components/ProblemLibrary.svelte';
  import { normalizePrefix } from './lib/problemUtils.js';

  const apiPrefix = '/api/v1';

  let activePage = 'create';
  let savedProblems = [];
  let libraryLoading = false;
  let libraryError = '';

  $: libraryEndpoint = `${normalizePrefix(apiPrefix)}/problems`;

  onMount(() => {
    loadLibrary();
  });

  async function loadLibrary(options = {}) {
    if (!options.silent) {
      libraryLoading = true;
    }
    libraryError = '';

    try {
      const response = await fetch(`${libraryEndpoint}?limit=300`);
      const raw = await response.text();
      let parsed;
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = null;
      }

      if (!response.ok) {
        const detail = parsed?.detail || raw || `HTTP ${response.status}`;
        throw new Error(String(detail));
      }
      if (!Array.isArray(parsed)) {
        throw new Error('저장소 응답 형식이 올바르지 않습니다.');
      }

      savedProblems = parsed;
    } catch (err) {
      libraryError = err instanceof Error ? err.message : '저장소를 불러오지 못했습니다.';
    } finally {
      libraryLoading = false;
    }
  }
</script>

<div class="page-bg"></div>
<div class="page-wrap">
  <header class="hero panel">
    <p class="eyebrow">영어 변형문제 제작소</p>
    <h1>영어 지문 문항 생성 UI</h1>
    <p>
      문항 유형, 난이도, 생성 옵션을 조합해서 결과를 즉시 확인할 수 있습니다.
    </p>
    <nav class="page-tabs" aria-label="페이지 전환">
      <button type="button" class:active={activePage === 'create'} on:click={() => (activePage = 'create')}>
        문제 만들기
      </button>
      <button type="button" class:active={activePage === 'library'} on:click={() => (activePage = 'library')}>
        내 문제 저장소 <span>{savedProblems.length}</span>
      </button>
      <button type="button" class:active={activePage === 'exam'} on:click={() => (activePage = 'exam')}>
        모의고사 시험지
      </button>
    </nav>
  </header>

  {#if activePage === 'create'}
    <ProblemCreator apiPrefix={apiPrefix} onGenerated={() => loadLibrary({ silent: true })} />
  {:else if activePage === 'library'}
    <ProblemLibrary
      {savedProblems}
      {libraryLoading}
      {libraryError}
      onRefresh={() => loadLibrary()}
    />
  {:else}
    <MockExamBuilder
      {savedProblems}
      {libraryLoading}
      {libraryError}
      onRefresh={() => loadLibrary()}
    />
  {/if}
</div>
