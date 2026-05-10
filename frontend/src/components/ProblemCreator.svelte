<script>
  import ProblemView from './ProblemView.svelte';
  import { normalizePrefix, samplePassage, typeOptions } from '../lib/problemUtils.js';

  export let apiPrefix = '/api/v1';
  export let onGenerated = () => {};

  let selectedType = 'title';
  let form = {
    passage: '',
    difficulty: 'mid',
    seed: '',
    explain: true,
    return_korean_stem: true,
    debug: false
  };
  let isLoading = false;
  let errorMessage = '';
  let result = null;

  $: endpoint = `${normalizePrefix(apiPrefix)}/${selectedType}`;

  function fillSample() {
    form = { ...form, passage: samplePassage };
  }

  function clearAll() {
    form = {
      passage: '',
      difficulty: 'mid',
      seed: '',
      explain: true,
      return_korean_stem: true,
      debug: false
    };
    errorMessage = '';
    result = null;
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
      debug: form.debug
    };
  }

  async function generateItem() {
    errorMessage = '';
    result = null;

    if (!form.passage.trim()) {
      errorMessage = '지문을 먼저 입력해 주세요.';
      return;
    }

    isLoading = true;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload())
      });

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

      if (!parsed || typeof parsed !== 'object') {
        throw new Error('응답 JSON 파싱에 실패했습니다.');
      }

      result = parsed;
      onGenerated();
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : '요청 처리 중 알 수 없는 오류가 발생했습니다.';
    } finally {
      isLoading = false;
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
      <ProblemView problem={result} />
    {:else}
      <div class="empty-box">
        <h3>아직 결과가 없습니다</h3>
        <p>좌측에서 지문과 유형을 설정한 뒤 문항 생성을 실행해 주세요.</p>
      </div>
    {/if}
  </section>
</main>
