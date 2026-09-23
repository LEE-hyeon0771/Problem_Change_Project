<script>
  import { onMount } from 'svelte';
  import HomeLanding from './components/HomeLanding.svelte';
  import LibraryHub from './components/LibraryHub.svelte';
  import MockExamBuilder from './components/MockExamBuilder.svelte';
  import ProblemCreator from './components/ProblemCreator.svelte';
  import ProblemLibrary from './components/ProblemLibrary.svelte';
  import WordbookCreator from './components/WordbookCreator.svelte';
  import WordbookLibrary from './components/WordbookLibrary.svelte';
  import { listProblems, listWordbooks } from './lib/api/index.js';

  const apiPrefix = '/api/v1';

  // 홈에서 고른 뒤에도 탭으로 모든 화면을 오갈 수 있어야 하므로 탭 목록은 홈과 분리합니다.
  const tabs = [
    { id: 'create', label: '문제변형' },
    { id: 'wordbook', label: '핵심단어장' },
    { id: 'library', label: '개인DB', badge: true },
    { id: 'exam', label: '모의고사 출제' }
  ];

  const headings = {
    create: { eyebrow: '문제변형', title: '영어 지문 문항 생성', lead: '문항 유형, 난이도, 생성 옵션을 조합해서 결과를 즉시 확인할 수 있습니다.' },
    wordbook: { eyebrow: '핵심단어장', title: '지문 핵심단어 정리', lead: '지문의 핵심단어를 모두 뽑아 뜻마다 품사와 동의어·반의어까지 정리합니다.' },
    library: { eyebrow: '개인DB', title: '내가 저장한 자료', lead: '"사용"을 누른 변형문제와 단어장이 종류별로 보관됩니다.' },
    exam: { eyebrow: '모의고사 출제', title: '문제지 · 단어 암기지 만들기', lead: '저장한 자료로 시험지와 단어 암기지를 구성하고 PDF로 출력합니다.' }
  };

  let activePage = 'home';
  // 개인DB 안의 구분: '' = 허브(2개 버튼) | 'problems' | 'wordbooks'
  let librarySection = '';

  let savedProblems = [];
  let libraryLoading = false;
  let libraryError = '';

  let savedWordbooks = [];
  let wordbookLoading = false;
  let wordbookError = '';

  $: heading = headings[activePage];
  $: savedCount = savedProblems.length + savedWordbooks.length;

  onMount(() => {
    loadProblems();
    loadWordbooks();
  });

  function navigate(page, section = '') {
    activePage = page;
    librarySection = page === 'library' ? section : '';
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  async function loadProblems(options = {}) {
    if (!options.silent) {
      libraryLoading = true;
    }
    libraryError = '';

    try {
      savedProblems = await listProblems(apiPrefix);
    } catch (err) {
      libraryError = err instanceof Error ? err.message : '저장소를 불러오지 못했습니다.';
    } finally {
      libraryLoading = false;
    }
  }

  async function loadWordbooks(options = {}) {
    if (!options.silent) {
      wordbookLoading = true;
    }
    wordbookError = '';

    try {
      savedWordbooks = await listWordbooks(apiPrefix);
    } catch (err) {
      wordbookError = err instanceof Error ? err.message : '단어장을 불러오지 못했습니다.';
    } finally {
      wordbookLoading = false;
    }
  }
</script>

<div class="page-bg"></div>
<div class="page-wrap">
  {#if activePage === 'home'}
    <HomeLanding savedCount={savedCount} onNavigate={navigate} />
  {:else}
    <header class="hero panel">
      <p class="eyebrow">{heading.eyebrow}</p>
      <h1>{heading.title}</h1>
      <p>{heading.lead}</p>
      <nav class="page-tabs" aria-label="페이지 전환">
        <button type="button" class="tab-home" on:click={() => navigate('home')}>홈</button>
        {#each tabs as tab}
          <button type="button" class:active={activePage === tab.id} on:click={() => navigate(tab.id)}>
            {tab.label}
            {#if tab.badge}<span>{savedCount}</span>{/if}
          </button>
        {/each}
      </nav>
    </header>

    {#if activePage === 'create'}
      <ProblemCreator apiPrefix={apiPrefix} onSaved={() => loadProblems({ silent: true })} />
    {:else if activePage === 'wordbook'}
      <WordbookCreator apiPrefix={apiPrefix} onSaved={() => loadWordbooks({ silent: true })} />
    {:else if activePage === 'library'}
      {#if librarySection}
        <main class="library-view">
          <nav class="sub-tabs" aria-label="개인DB 구분">
            <button type="button" on:click={() => (librarySection = '')}>← 개인DB</button>
            <button type="button" class:active={librarySection === 'problems'} on:click={() => (librarySection = 'problems')}>
              변형문제 <span>{savedProblems.length}</span>
            </button>
            <button type="button" class:active={librarySection === 'wordbooks'} on:click={() => (librarySection = 'wordbooks')}>
              단어장 <span>{savedWordbooks.length}</span>
            </button>
          </nav>

          {#if librarySection === 'problems'}
            <ProblemLibrary
              {savedProblems}
              {libraryLoading}
              {libraryError}
              onRefresh={() => loadProblems()}
            />
          {:else}
            <WordbookLibrary
              {savedWordbooks}
              loading={wordbookLoading}
              error={wordbookError}
              apiPrefix={apiPrefix}
              onRefresh={() => loadWordbooks()}
              onDeleted={() => loadWordbooks({ silent: true })}
            />
          {/if}
        </main>
      {:else}
        <LibraryHub
          problemCount={savedProblems.length}
          wordbookCount={savedWordbooks.length}
          onSelect={(section) => (librarySection = section)}
        />
      {/if}
    {:else}
      <MockExamBuilder
        {savedProblems}
        {savedWordbooks}
        {libraryLoading}
        {libraryError}
        onRefresh={() => {
          loadProblems();
          loadWordbooks();
        }}
      />
    {/if}
  {/if}
</div>
