<script>
  import ProblemSheet from './exam/ProblemSheet.svelte';
  import VocabSheet from './exam/VocabSheet.svelte';

  export let savedProblems = [];
  export let savedWordbooks = [];
  export let libraryLoading = false;
  export let libraryError = '';
  export let onRefresh = () => {};

  // 'problem' = 변형문제로 시험지 출제, 'vocab' = 단어장으로 암기지 출제
  let examMode = 'problem';
</script>

<main class="exam-view">
  <nav class="sub-tabs exam-mode-tabs" aria-label="출제 구분">
    <button type="button" class:active={examMode === 'problem'} on:click={() => (examMode = 'problem')}>
      문제 출제 <span>{savedProblems.length}</span>
    </button>
    <button type="button" class:active={examMode === 'vocab'} on:click={() => (examMode = 'vocab')}>
      단어 암기 <span>{savedWordbooks.length}</span>
    </button>
  </nav>

  {#if examMode === 'vocab'}
    <VocabSheet {savedWordbooks} {libraryLoading} {onRefresh} />
  {:else}
    <ProblemSheet {savedProblems} {libraryLoading} {libraryError} {onRefresh} />
  {/if}
</main>
