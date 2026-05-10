<script>
  import {
    buildPassageSegments,
    formatDate,
    getInsertionBody,
    getInsertionGivenSentence,
    getSummaryBody,
    getSummaryText,
    isImplicitType,
    isInsertionType,
    isSummaryType,
    parseSummaryChoice,
    previewText,
    toMarkerDisplay,
    typeLabel,
    typeOptions,
    usesEmbeddedChoices
  } from '../lib/problemUtils.js';

  export let savedProblems = [];
  export let libraryLoading = false;
  export let libraryError = '';
  export let onRefresh = () => {};

  let examTitle = '2026 영어 변형 모의고사';
  let examCount = 10;
  let examSelectedTypes = typeOptions.map((option) => option.value);
  let examCandidateType = 'all';
  let examCandidateSearch = '';
  let selectedReplacementUid = '';
  let draggedReplacementUid = '';
  let activeDropIndex = null;
  let examItems = [];
  let examError = '';
  let examMessage = '';
  let showExamAnswers = false;
  let showExamExplanations = true;

  $: examPool = getExamPool(savedProblems, examSelectedTypes);
  $: examTypeCounts = countProblemsByType(savedProblems);
  $: examReplacementLibrary = filterReplacementLibrary(
    savedProblems,
    examCandidateType,
    examCandidateSearch,
    examItems
  );
  $: selectedReplacement = getProblemByUid(selectedReplacementUid);

  function getExamPool(records, selectedTypes) {
    const typeSet = new Set(selectedTypes);
    return records.filter((record) => typeSet.has(record.problem_type) && record?.result);
  }

  function getProblemByUid(problemUid) {
    if (!problemUid) {
      return null;
    }
    return savedProblems.find((record) => record.problem_uid === problemUid) || null;
  }

  function getExamUsedIds(items, skipIndex = null) {
    return new Set(
      items
        .map((item, itemIndex) => (itemIndex === skipIndex ? null : item?.problem_uid))
        .filter(Boolean)
    );
  }

  function filterReplacementLibrary(records, type, search, currentItems) {
    const usedIds = getExamUsedIds(currentItems);
    const needle = search.trim().toLowerCase();

    return records.filter((record) => {
      if (!record?.result || usedIds.has(record.problem_uid)) {
        return false;
      }

      const matchesType = type === 'all' || record.problem_type === type;
      const haystack = [
        record.problem_type,
        typeLabel(record.problem_type),
        record.result.question,
        record.result.passage,
        record.result.answer?.text,
        record.result.explanation
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return matchesType && (!needle || haystack.includes(needle));
    });
  }

  function countProblemsByType(records) {
    return records.reduce((counts, record) => {
      if (record?.problem_type) {
        counts[record.problem_type] = (counts[record.problem_type] || 0) + 1;
      }
      return counts;
    }, {});
  }

  function shuffleRecords(records) {
    const shuffled = [...records];
    for (let index = shuffled.length - 1; index > 0; index -= 1) {
      const target = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[target]] = [shuffled[target], shuffled[index]];
    }
    return shuffled;
  }

  function toggleExamType(type) {
    if (examSelectedTypes.includes(type)) {
      examSelectedTypes = examSelectedTypes.filter((selected) => selected !== type);
      return;
    }
    examSelectedTypes = [...examSelectedTypes, type];
  }

  function selectAllExamTypes() {
    examSelectedTypes = typeOptions.map((option) => option.value);
  }

  function clearExamTypes() {
    examSelectedTypes = [];
  }

  function buildExamPaper() {
    examError = '';
    examMessage = '';
    selectedReplacementUid = '';
    draggedReplacementUid = '';
    activeDropIndex = null;
    const count = Number(examCount);

    if (!Number.isInteger(count) || count < 1) {
      examError = '문항 수는 1 이상의 정수로 입력해 주세요.';
      return;
    }
    if (!examSelectedTypes.length) {
      examError = '시험지에 넣을 문제 유형을 하나 이상 선택해 주세요.';
      return;
    }
    if (examPool.length < count) {
      examError = `선택한 조건의 저장 문제가 ${examPool.length}개뿐입니다. 문항 수를 줄이거나 유형을 더 선택해 주세요.`;
      return;
    }

    examItems = shuffleRecords(examPool).slice(0, count);
    examMessage = `${count}문항 시험지를 새로 구성했습니다. 왼쪽 후보 목록에서 문제를 선택하거나 드래그해서 원하는 번호에 넣을 수 있습니다.`;
  }

  function selectReplacement(record) {
    selectedReplacementUid = selectedReplacementUid === record.problem_uid ? '' : record.problem_uid;
    examError = '';
    examMessage = selectedReplacementUid
      ? `${typeLabel(record.problem_type)} 유형 문제를 선택했습니다. 시험지의 원하는 번호에서 "선택 문제로 교체"를 누르세요.`
      : '선택한 교체 후보를 해제했습니다.';
  }

  function canApplyReplacement(record, index) {
    if (!record?.result || !examItems[index]) {
      return false;
    }
    return !getExamUsedIds(examItems, index).has(record.problem_uid);
  }

  function replaceExamItemWith(index, replacement) {
    if (!replacement) {
      examError = '왼쪽 교체 후보 목록에서 넣을 문제를 먼저 선택해 주세요.';
      examMessage = '';
      return;
    }

    if (!canApplyReplacement(replacement, index)) {
      examError = '이미 시험지에 들어간 문제이거나 교체할 수 없는 문제입니다.';
      examMessage = '';
      return;
    }

    examItems = examItems.map((item, itemIndex) => (itemIndex === index ? replacement : item));
    examError = '';
    examMessage = `${index + 1}번 문항을 왼쪽에서 선택한 ${typeLabel(replacement.problem_type)} 유형 문제로 교체했습니다.`;
    selectedReplacementUid = '';
    draggedReplacementUid = '';
    activeDropIndex = null;
  }

  function applySelectedReplacement(index) {
    replaceExamItemWith(index, selectedReplacement);
  }

  function handleReplacementDragStart(event, record) {
    draggedReplacementUid = record.problem_uid;
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData('text/plain', record.problem_uid);
  }

  function handleQuestionDragOver(event, index) {
    const replacement = getProblemByUid(draggedReplacementUid);
    if (!canApplyReplacement(replacement, index)) {
      return;
    }
    event.preventDefault();
    activeDropIndex = index;
    event.dataTransfer.dropEffect = 'copy';
  }

  function handleQuestionDragLeave(index) {
    if (activeDropIndex === index) {
      activeDropIndex = null;
    }
  }

  function handleQuestionDrop(event, index) {
    event.preventDefault();
    const problemUid = event.dataTransfer.getData('text/plain') || draggedReplacementUid;
    const replacement = getProblemByUid(problemUid);
    replaceExamItemWith(index, replacement);
  }

  function clearExamPaper() {
    examItems = [];
    examError = '';
    examMessage = '';
    selectedReplacementUid = '';
    draggedReplacementUid = '';
    activeDropIndex = null;
  }

  function printExamPaper() {
    window.print();
  }

  function examAnswerText(record, index) {
    const label = record?.result?.answer?.label || '-';
    return `${index + 1}. ${label}`;
  }
</script>

<main class="exam-view">
  <section class="panel exam-builder">
    <div class="library-head">
      <div>
        <p class="eyebrow">모의고사 구성</p>
        <h2>모의고사 시험지</h2>
        <p>개인 문제 저장소에 쌓인 변형문제만 사용해서 다단 시험지를 구성합니다.</p>
      </div>
      <button class="ghost" type="button" on:click={onRefresh} disabled={libraryLoading}>
        {libraryLoading ? '불러오는 중...' : '저장소 새로고침'}
      </button>
    </div>

    <div class="exam-controls">
      <label>
        시험지 제목
        <input type="text" bind:value={examTitle} placeholder="2026 영어 변형 모의고사" />
      </label>
      <label>
        문항 수
        <input type="number" min="1" max={Math.max(examPool.length, 1)} bind:value={examCount} />
      </label>
      <label class="answer-toggle">
        <input type="checkbox" bind:checked={showExamAnswers} />
        정답표 표시
      </label>
      <label class="answer-toggle">
        <input type="checkbox" bind:checked={showExamExplanations} />
        해설지 표시
      </label>
    </div>

    <fieldset class="exam-type-field">
      <div class="exam-field-head">
        <legend>시험지에 넣을 문제 유형</legend>
        <div class="exam-type-actions">
          <button class="ghost" type="button" on:click={selectAllExamTypes}>전체 선택</button>
          <button class="ghost" type="button" on:click={clearExamTypes}>전체 해제</button>
        </div>
      </div>
      <div class="exam-type-grid" role="group" aria-label="시험지 문제 유형">
        {#each typeOptions as option}
          <button
            type="button"
            class:selected={examSelectedTypes.includes(option.value)}
            aria-pressed={examSelectedTypes.includes(option.value)}
            on:click={() => toggleExamType(option.value)}
          >
            <span>{option.label}</span>
            <small>{examTypeCounts[option.value] || 0}개 저장됨</small>
          </button>
        {/each}
      </div>
    </fieldset>

    <div class="actions exam-actions">
      <button class="primary" type="button" on:click={buildExamPaper}>시험지 만들기</button>
      <button class="ghost" type="button" on:click={printExamPaper} disabled={!examItems.length}>인쇄 / PDF 저장</button>
      <button class="ghost danger" type="button" on:click={clearExamPaper} disabled={!examItems.length}>시험지 비우기</button>
    </div>

    <p class="exam-pool-note">
      선택 가능한 문제 {examPool.length}개 · 저장소 전체 {savedProblems.length}개
    </p>

    {#if libraryError}
      <div class="error-box">
        <strong>저장소 조회 실패</strong>
        <p>{libraryError}</p>
      </div>
    {/if}

    {#if examError}
      <div class="error-box">
        <strong>시험지 처리 실패</strong>
        <p>{examError}</p>
      </div>
    {/if}
    {#if examMessage}
      <div class="exam-message-box">
        <strong>시험지 상태</strong>
        <p>{examMessage}</p>
      </div>
    {/if}
  </section>

  <div class="exam-compose">
    <aside class="panel replacement-panel">
      <div class="replacement-head">
        <div>
          <h3>교체 후보 문제</h3>
          <p>왼쪽 문제를 선택하거나 드래그해서 시험지의 원하는 번호에 넣으세요.</p>
        </div>
        <span>{examReplacementLibrary.length}개</span>
      </div>

      <div class="replacement-tools">
        <label>
          유형
          <select bind:value={examCandidateType}>
            <option value="all">전체 유형</option>
            {#each typeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label>
          검색
          <input type="text" bind:value={examCandidateSearch} placeholder="질문, 지문 검색" />
        </label>
      </div>

      {#if selectedReplacement}
        <div class="selected-replacement">
          <strong>선택 중</strong>
          <p>{typeLabel(selectedReplacement.problem_type)} · {selectedReplacement.result?.question}</p>
          <button class="ghost" type="button" on:click={() => (selectedReplacementUid = '')}>선택 해제</button>
        </div>
      {/if}

      {#if libraryLoading}
        <div class="skeleton library-skeleton">
          <span></span>
          <span></span>
          <span></span>
        </div>
      {:else if examReplacementLibrary.length}
        <div class="replacement-list" aria-label="교체 가능한 저장 문제 목록">
          {#each examReplacementLibrary as candidate (candidate.problem_uid)}
            <button
              class="replacement-card"
              class:selected={selectedReplacementUid === candidate.problem_uid}
              type="button"
              draggable="true"
              on:click={() => selectReplacement(candidate)}
              on:dragstart={(event) => handleReplacementDragStart(event, candidate)}
            >
              <span class="replacement-type">{typeLabel(candidate.problem_type)}</span>
              <strong>{candidate.result?.question || '문항 지시문 없음'}</strong>
              <p>{previewText(candidate.result?.passage, 115)}</p>
              <small>{formatDate(candidate.created_at)} 생성</small>
            </button>
          {/each}
        </div>
      {:else}
        <div class="empty-box">
          <h3>교체 후보가 없습니다</h3>
          <p>현재 시험지에 들어가지 않은 저장 문제가 없거나 검색 조건에 맞는 문제가 없습니다.</p>
        </div>
      {/if}
    </aside>

    {#if examItems.length}
      <section class="exam-shell">
        <article class="exam-paper">
          <header class="exam-paper-head">
            <p>영어 영역</p>
            <h2>{examTitle || '영어 변형 모의고사'}</h2>
            <small>총 {examItems.length}문항 · 개인 문제 저장소 기반</small>
          </header>

          <div class="exam-columns">
            {#each examItems as record, index (record.problem_uid)}
              {@const problem = record.result}
              <div
                class="exam-question"
                class:drop-target={activeDropIndex === index}
                role="region"
                aria-label={`${index + 1}번 문항 교체 영역`}
                on:dragover={(event) => handleQuestionDragOver(event, index)}
                on:dragleave={() => handleQuestionDragLeave(index)}
                on:drop={(event) => handleQuestionDrop(event, index)}
              >
                <div class="exam-question-top">
                  <div>
                    <span class="exam-number">{index + 1}</span>
                    <span class="exam-type-pill">{typeLabel(record.problem_type)}</span>
                  </div>
                  <button
                    class="ghost exam-replace"
                    type="button"
                    disabled={!selectedReplacement || !canApplyReplacement(selectedReplacement, index)}
                    title={selectedReplacement ? '왼쪽에서 선택한 문제로 교체' : '왼쪽 교체 후보를 먼저 선택하세요'}
                    on:click={() => applySelectedReplacement(index)}
                  >
                    선택 문제로 교체
                  </button>
                </div>
                <p class="drop-hint">왼쪽 후보를 이 문항 위로 드래그해도 교체됩니다.</p>

                <p class="exam-stem">{problem.question}</p>

                {#if isInsertionType(problem.type) && getInsertionGivenSentence(problem.type, problem.passage, problem.meta)}
                  <section class="exam-given-box">
                    <strong>주어진 문장</strong>
                    <p>{getInsertionGivenSentence(problem.type, problem.passage, problem.meta)}</p>
                  </section>
                {/if}

                {#if isSummaryType(problem.type)}
                  {#if getSummaryBody(problem.type, problem.passage)}
                    <div class="exam-passage">{getSummaryBody(problem.type, problem.passage)}</div>
                  {/if}
                  {#if getSummaryBody(problem.type, problem.passage) && getSummaryText(problem.type, problem.passage)}
                    <p class="exam-summary-divider">↓</p>
                  {/if}
                  {#if getSummaryText(problem.type, problem.passage)}
                    <section class="exam-summary-box">
                      <strong>Summary Sentence</strong>
                      <p>{getSummaryText(problem.type, problem.passage)}</p>
                    </section>
                  {/if}
                {:else}
                  <div class="exam-passage">
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
                  <p class="exam-choice-note">선택지는 지문 내부 표식을 확인하세요.</p>
                {:else}
                  <ol class="exam-choice-list" aria-label={`${index + 1}번 선택지`}>
                    {#each problem.choices || [] as choice}
                      <li>
                        <span class="exam-choice-label">{choice.label}</span>
                        {#if isSummaryType(problem.type)}
                          {@const pair = parseSummaryChoice(choice.text)}
                          {#if pair}
                            <p>(A) {pair.a} / (B) {pair.b}</p>
                          {:else}
                            <p>{choice.text}</p>
                          {/if}
                        {:else}
                          <p>{choice.text}</p>
                        {/if}
                      </li>
                    {/each}
                  </ol>
                {/if}
              </div>
            {/each}
          </div>

          {#if showExamAnswers}
            <section class="exam-answer-sheet">
              <h3>정답표</h3>
              <div>
                {#each examItems as record, index}
                  <span>{examAnswerText(record, index)}</span>
                {/each}
              </div>
            </section>
          {/if}
        </article>

        {#if showExamExplanations}
          <article class="exam-explanation-paper">
            <header class="exam-paper-head">
              <p>정답 및 해설</p>
              <h2>{examTitle || '영어 변형 모의고사'} 해설지</h2>
              <small>총 {examItems.length}문항</small>
            </header>

            <div class="explanation-list">
              {#each examItems as record, index (record.problem_uid)}
                {@const problem = record.result}
                <section class="explanation-item">
                  <div class="explanation-title">
                    <span>{index + 1}</span>
                    <div>
                      <strong>{typeLabel(record.problem_type)}</strong>
                      <p>{problem.question}</p>
                    </div>
                  </div>
                  <p class="explanation-answer">
                    정답: {problem.answer?.label || '-'}
                    {#if problem.answer?.text}
                      · {problem.answer.text}
                    {/if}
                  </p>
                  {#if problem.explanation}
                    <p class="explanation-body">{problem.explanation}</p>
                  {:else}
                    <p class="explanation-body muted">저장된 해설이 없습니다.</p>
                  {/if}
                </section>
              {/each}
            </div>
          </article>
        {/if}
      </section>
    {:else}
      <section class="panel exam-empty">
        <h3>아직 구성된 시험지가 없습니다</h3>
        <p>문항 수와 유형을 고른 뒤 시험지 만들기를 누르면 저장소 문제들로 시험지가 생성됩니다.</p>
      </section>
    {/if}
  </div>
</main>
