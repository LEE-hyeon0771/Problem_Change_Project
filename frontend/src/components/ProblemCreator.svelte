<script>
  import ProblemView from './ProblemView.svelte';
  import { normalizePrefix, samplePassage, typeLabel, typeOptions } from '../lib/problemUtils.js';
  import { saveProblem, streamProblem } from '../lib/api/index.js';

  export let apiPrefix = '/api/v1';
  export let onSaved = () => {};

  // 동의어 교체가 안전한 유형. 어휘·어법은 정답 유일성이 깨지고,
  // 삽입·순서·무관은 연결어 단서가 흔들려 제외합니다.
  const SWAP_TYPES = new Set(['title', 'topic', 'summary', 'blank', 'implicit']);

  let selectedType = 'title';
  let form = {
    passage: '',
    difficulty: 'mid',
    seed: '',
    explain: true,
    return_korean_stem: true,
    debug: false,
    synonym_swap: false
  };
  // 되돌린 교체의 original 집합
  let revertedSwaps = new Set();
  let isLoading = false;
  let errorMessage = '';
  let result = null;
  let usedPayload = null;
  let progressMessage = '';
  let saveState = 'idle'; // idle | saving | saved
  let saveError = '';

  $: swapSupported = SWAP_TYPES.has(selectedType);
  $: appliedSwaps = result?.meta?.synonym_swap?.swaps || [];
  $: displayedProblem = applyReverts(result, revertedSwaps);

  function fillSample() {
    form = { ...form, passage: samplePassage };
  }

  function resetResult() {
    result = null;
    usedPayload = null;
    revertedSwaps = new Set();
    saveState = 'idle';
    saveError = '';
    progressMessage = '';
  }

  function clearAll() {
    form = {
      passage: '',
      difficulty: 'mid',
      seed: '',
      explain: true,
      return_korean_stem: true,
      debug: false,
      synonym_swap: form.synonym_swap
    };
    errorMessage = '';
    resetResult();
  }

  function buildPayload() {
    const parsedSeed = Number(form.seed);
    const normalizedSeed =
      form.seed === '' || form.seed === null || form.seed === undefined || Number.isNaN(parsedSeed)
        ? null
        : parsedSeed;

    return {
      passage: form.passage.trim(),
      difficulty: form.difficulty,
      choices: 5,
      seed: normalizedSeed,
      style: 'edu_office',
      explain: form.explain,
      return_korean_stem: form.return_korean_stem,
      debug: form.debug,
      synonym_swap: swapSupported && form.synonym_swap
    };
  }

  async function generateItem() {
    errorMessage = '';
    resetResult();

    if (!form.passage.trim()) {
      errorMessage = '지문을 먼저 입력해 주세요.';
      return;
    }

    const payload = buildPayload();
    isLoading = true;
    progressMessage = '요청을 준비하고 있습니다...';

    try {
      result = await streamProblem(apiPrefix, selectedType, payload, {
        onStatus: (event) => {
          if (event?.message) {
            progressMessage = event.message;
          }
        }
      });
      // 저장할 때 생성에 쓴 요청 원본이 필요합니다.
      usedPayload = payload;
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : '요청 처리 중 알 수 없는 오류가 발생했습니다.';
    } finally {
      isLoading = false;
      progressMessage = '';
    }
  }

  /** 되돌린 교체를 문항 전체(지문·선지·정답·해설)에 일괄 반영합니다.
   *  서버가 "지문에 한 번만 등장하는 단어"만 교체하므로 전역 치환이 안전합니다. */
  function applyReverts(problem, reverted) {
    if (!problem || !reverted.size) {
      return problem;
    }

    const swaps = (problem.meta?.synonym_swap?.swaps || []).filter((s) => reverted.has(s.original));
    if (!swaps.length) {
      return problem;
    }

    const undo = (text) => {
      if (typeof text !== 'string') {
        return text;
      }
      let out = text;
      for (const { original, replacement } of swaps) {
        out = out.split(replacement).join(original);
      }
      return out;
    };

    return {
      ...problem,
      passage: undo(problem.passage),
      question: undo(problem.question),
      explanation: undo(problem.explanation),
      choices: (problem.choices || []).map((c) => ({ ...c, text: undo(c.text) })),
      answer: problem.answer ? { ...problem.answer, text: undo(problem.answer.text) } : problem.answer
    };
  }

  function toggleRevert(original) {
    const next = new Set(revertedSwaps);
    next.has(original) ? next.delete(original) : next.add(original);
    revertedSwaps = next;
  }

  async function useProblem() {
    if (!result || !usedPayload || saveState !== 'idle') {
      return;
    }

    saveState = 'saving';
    saveError = '';

    try {
      await saveProblem(apiPrefix, { request: usedPayload, result: displayedProblem });
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
    <fieldset class="field group-field">
      <legend>문항 유형</legend>
      <div id="problemType" class="type-grid" role="group" aria-label="문항 유형">
        {#each typeOptions as option}
          <button
            type="button"
            class:selected={selectedType === option.value}
            on:click={() => (selectedType = option.value)}
          >
            <span>{option.label}</span>
            <small>{option.hint}</small>
          </button>
        {/each}
      </div>
    </fieldset>

    <fieldset class="field group-field">
      <legend>난이도</legend>
      <div id="difficulty" class="segmented" role="group" aria-label="난이도">
        {#each ['easy', 'mid', 'hard'] as level}
          <button
            type="button"
            class:active={form.difficulty === level}
            on:click={() => (form = { ...form, difficulty: level })}
          >
            {level}
          </button>
        {/each}
      </div>
    </fieldset>

    <div class="field">
      <div class="label-row">
        <label for="passage">영어 지문</label>
        <small>최소 60 words 권장</small>
      </div>
      <textarea
        id="passage"
        bind:value={form.passage}
        placeholder="지문을 입력하세요..."
        rows="12"
      ></textarea>
    </div>

    <div class="field toggles option-toggles">
      <label><input type="checkbox" bind:checked={form.explain} /> 해설 포함</label>
      <label><input type="checkbox" bind:checked={form.return_korean_stem} /> 한국어 지시문</label>
    </div>

    <div class="field swap-option" class:disabled={!swapSupported}>
      <label>
        <input type="checkbox" bind:checked={form.synonym_swap} disabled={!swapSupported} />
        지문 단어 동의어로 바꾸기
      </label>
      {#if swapSupported}
        <small>
          암기한 지문을 낯설게 만들어 학생이 실제로 읽게 합니다.
          난이도에 따라 문장당 {form.difficulty === 'easy' ? '0.7' : form.difficulty === 'hard' ? '1.5' : '1'}개 정도 바꿉니다.
        </small>
      {:else}
        <small class="swap-warn">
          {typeLabel(selectedType)} 유형은 지원하지 않습니다.
          어휘·어법은 정답이 둘이 될 수 있고, 삽입·순서·무관문장은 연결어 단서가 흔들립니다.
        </small>
      {/if}
    </div>

    <div class="actions">
      <button class="primary" type="button" disabled={isLoading} on:click={generateItem}>
        {isLoading ? '생성 중...' : '문항 생성'}
      </button>
      <button class="ghost" type="button" on:click={fillSample}>샘플 채우기</button>
      <button class="ghost danger" type="button" on:click={clearAll}>초기화</button>
    </div>
  </section>

  <section class="panel result">
    <div class="result-head">
      <h2>생성 결과</h2>
    </div>

    {#if isLoading}
      {#if progressMessage}
        <p class="stream-status"><span class="stream-dot"></span>{progressMessage}</p>
      {/if}
      <div class="skeleton">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>
    {:else if errorMessage}
      <div class="error-box">
        <strong>요청 실패</strong>
        <p>{errorMessage}</p>
      </div>
    {:else if result}
      {#if appliedSwaps.length}
        <section class="swap-review">
          <header>
            <strong>바뀐 단어 {appliedSwaps.length}개</strong>
            <span>체크를 해제하면 원래 단어로 되돌립니다</span>
          </header>
          <ul>
            {#each appliedSwaps as swap}
              {@const kept = !revertedSwaps.has(swap.original)}
              <li class:reverted={!kept}>
                <label>
                  <input type="checkbox" checked={kept} on:change={() => toggleRevert(swap.original)} />
                  <span class="swap-from">{swap.original}</span>
                  <span class="swap-arrow">→</span>
                  <span class="swap-to">{kept ? swap.replacement : swap.original}</span>
                </label>
                {#if swap.note}<p class="swap-note">{swap.note}</p>{/if}
              </li>
            {/each}
          </ul>
          {#if revertedSwaps.size}
            <p class="swap-reverted-note">
              {revertedSwaps.size}개를 되돌렸습니다. "사용"을 누르면 아래 보이는 상태 그대로 저장됩니다.
            </p>
          {/if}
        </section>
      {/if}

      <ProblemView problem={displayedProblem} />

      <div class="use-bar" class:done={saveState === 'saved'}>
        {#if saveState === 'saved'}
          <div class="use-bar-text">
            <strong>개인DB에 저장했습니다</strong>
            <p>{typeLabel(result.type)} 문항이 개인DB &gt; 변형문제에 보관되었습니다.</p>
          </div>
          <button class="ghost" type="button" on:click={resetResult}>새로 만들기</button>
        {:else}
          <div class="use-bar-text">
            <strong>이 문항을 쓰시겠어요?</strong>
            <p>"사용"을 눌러야 개인DB에 저장됩니다. 저장해야 모의고사 출제에 쓸 수 있습니다.</p>
          </div>
          <button class="primary" type="button" disabled={saveState === 'saving'} on:click={useProblem}>
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
    {:else}
      <div class="empty-box">
        <h3>아직 결과가 없습니다</h3>
        <p>좌측에서 지문과 유형을 설정한 뒤 문항 생성을 실행해 주세요.</p>
      </div>
    {/if}
  </section>
</main>
