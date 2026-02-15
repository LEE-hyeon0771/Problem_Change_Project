<script>
  import { onMount } from 'svelte';

  const typeOptions = [
    { value: 'title', label: '제목', hint: 'Main idea title' },
    { value: 'topic', label: '주제', hint: 'Main topic scope' },
    { value: 'blank', label: '빈칸', hint: 'Core logic blank' },
    { value: 'summary', label: '요약', hint: 'A/B summary pair' },
    { value: 'implicit', label: '함축의미', hint: 'Implied meaning' },
    { value: 'insertion', label: '삽입', hint: 'Best slot ①~⑤' },
    { value: 'order', label: '순서', hint: 'A-B-C ordering' },
    { value: 'irrelevant', label: '무관문장', hint: 'Off-topic sentence' },
    { value: 'reference', label: '지칭', hint: 'Antecedent tracking' },
    { value: 'vocab', label: '어휘', hint: 'Semantic mismatch' },
    { value: 'grammar', label: '어법', hint: 'Grammar error target' }
  ];

  const samplePassage = `People often rely on routines because habits reduce cognitive load and help preserve attention for demanding tasks. However, routines can also hide weak assumptions when individuals stop examining why they act in familiar ways. In many workplaces, teams repeat procedures simply because they were effective in a previous context. As conditions change, those same procedures may become less useful, even though they still feel comfortable. Therefore, effective decision making requires both stability and periodic review. By combining consistent practice with deliberate reflection, people can keep the benefits of habits while avoiding blind repetition.`;

  let apiPrefix = '/api/v1';
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
  let health = 'checking';
  let errorMessage = '';
  let result = null;
  let copied = false;

  $: endpoint = `${normalizePrefix(apiPrefix)}/${selectedType}`;
  $: prettyJson = result ? JSON.stringify(result, null, 2) : '';

  onMount(() => {
    checkHealth();
  });

  function normalizePrefix(value) {
    const trimmed = value.trim();
    if (!trimmed) {
      return '/api/v1';
    }
    return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
  }

  async function checkHealth() {
    health = 'checking';
    try {
      const response = await fetch('/health');
      if (!response.ok) {
        throw new Error('health endpoint returned non-200');
      }
      health = 'online';
    } catch {
      health = 'offline';
    }
  }

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
    copied = false;

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
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : '요청 처리 중 알 수 없는 오류가 발생했습니다.';
    } finally {
      isLoading = false;
    }
  }

  async function copyJson() {
    if (!prettyJson) {
      return;
    }

    try {
      await navigator.clipboard.writeText(prettyJson);
      copied = true;
      setTimeout(() => {
        copied = false;
      }, 1400);
    } catch {
      copied = false;
    }
  }

  function formatMetaValue(value) {
    if (value === null || value === undefined) {
      return 'null';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }

  function normalizeDisplayText(value) {
    if (value === null || value === undefined) {
      return '';
    }
    return String(value)
      .replace(/\\r\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .trim();
  }

  const markerIndexes = ['1', '2', '3', '4', '5'];
  const markerDisplay = ['①', '②', '③', '④', '⑤'];
  const embeddedChoiceTypes = new Set(['insertion', 'reference', 'vocab', 'grammar']);
  const referenceStopWords = new Set([
    'and',
    'or',
    'but',
    'is',
    'are',
    'was',
    'were',
    'be',
    'been',
    'being',
    'has',
    'have',
    'had',
    'do',
    'does',
    'did',
    'will',
    'would',
    'can',
    'could',
    'may',
    'might',
    'must',
    'should',
    'to'
  ]);

  function toMarkerIndex(raw) {
    const value = String(raw).trim().toLowerCase();
    if (/^[1-5]$/.test(value)) {
      return value;
    }
    if (/^[a-e]$/.test(value)) {
      return String(value.charCodeAt(0) - 96);
    }
    return value;
  }

  function toMarkerDisplay(raw) {
    const index = toMarkerIndex(raw);
    if (/^[1-5]$/.test(index)) {
      return markerDisplay[Number(index) - 1];
    }
    return index;
  }

  function parseTaggedTargets(passage) {
    const pattern = /\[\[([1-5])\]\]([\s\S]*?)\[\[\/\1\]\]/g;
    const segments = [];
    let cursor = 0;
    let found = false;
    let match;

    while ((match = pattern.exec(passage)) !== null) {
      found = true;
      const full = match[0];
      const label = match[1];
      const target = match[2];
      const start = match.index;
      const end = start + full.length;

      if (start > cursor) {
        segments.push({ kind: 'text', text: passage.slice(cursor, start) });
      }

      segments.push({
        kind: 'target',
        marker: toMarkerIndex(label),
        text: target
      });
      cursor = end;
    }

    if (!found) {
      return null;
    }
    if (cursor < passage.length) {
      segments.push({ kind: 'text', text: passage.slice(cursor) });
    }
    return segments;
  }

  function parseOpenMarkerTargets(passage, choices) {
    const pattern = /\[\[([1-5])\]\]/g;
    const segments = [];
    let cursor = 0;
    let found = false;
    let match;

    while ((match = pattern.exec(passage)) !== null) {
      const label = match[1];
      const markerStart = match.index;
      const markerEnd = markerStart + match[0].length;

      let start = markerEnd;
      while (start < passage.length && /\s/.test(passage[start])) {
        start += 1;
      }

      let targetText = '';
      let targetEnd = start;

      const choiceIndex = Number(label) - 1;
      const expectedChoice = Array.isArray(choices) ? String(choices[choiceIndex]?.text ?? '').trim() : '';
      if (expectedChoice) {
        const candidate = passage.slice(start, start + expectedChoice.length);
        if (candidate.toLowerCase() === expectedChoice.toLowerCase()) {
          targetText = passage.slice(start, start + expectedChoice.length);
          targetEnd = start + expectedChoice.length;
        }
      }

      if (!targetText) {
        const tokenMatch = passage.slice(start).match(/^[A-Za-z][A-Za-z'’-]*/);
        if (tokenMatch) {
          targetText = tokenMatch[0];
          targetEnd = start + targetText.length;
        }
      }

      if (!targetText) {
        continue;
      }

      found = true;
      if (markerStart > cursor) {
        segments.push({ kind: 'text', text: passage.slice(cursor, markerStart) });
      }

      segments.push({
        kind: 'target',
        marker: toMarkerIndex(label),
        text: targetText
      });
      cursor = targetEnd;
    }

    if (!found) {
      return null;
    }
    if (cursor < passage.length) {
      segments.push({ kind: 'text', text: passage.slice(cursor) });
    }
    return segments;
  }

  function parseHtmlUnderlineTargets(passage) {
    const pattern = /<u\b[^>]*>([\s\S]*?)<\/u>/gi;
    let source = passage;
    if (!/<u\b/i.test(source) && /&lt;\s*u\b/i.test(source)) {
      source = source
        .replace(/&lt;/gi, '<')
        .replace(/&gt;/gi, '>')
        .replace(/&amp;/gi, '&');
    }
    const segments = [];
    let cursor = 0;
    let found = false;
    let index = 0;
    let match;

    while ((match = pattern.exec(source)) !== null) {
      found = true;
      const full = match[0];
      const underlined = String(match[1] ?? '').trim();
      const start = match.index;
      const end = start + full.length;

      let before = source.slice(cursor, start);
      let marker = markerIndexes[index] ?? String(index + 1);
      const markerMatch = before.match(/\(([1-5a-eA-E])\)\s*$/);
      if (markerMatch && markerMatch.index !== undefined) {
        marker = toMarkerIndex(markerMatch[1]);
        before = before.slice(0, markerMatch.index);
      }

      if (before) {
        segments.push({ kind: 'text', text: before });
      }
      segments.push({
        kind: 'target',
        marker,
        text: underlined
      });

      cursor = end;
      index += 1;
    }

    if (!found) {
      return null;
    }
    if (cursor < source.length) {
      segments.push({ kind: 'text', text: source.slice(cursor) });
    }
    return segments;
  }

  function extractReferenceTarget(passage, markerEndIndex) {
    let start = markerEndIndex;
    while (start < passage.length && /\s/.test(passage[start])) {
      start += 1;
    }
    if (start >= passage.length) {
      return null;
    }

    let boundary = passage.length;
    for (let i = start; i < passage.length; i += 1) {
      const ch = passage[i];
      const isNextMarker =
        ch === '(' &&
        i + 2 < passage.length &&
        /[1-5a-eA-E]/.test(passage[i + 1]) &&
        passage[i + 2] === ')';

      if (isNextMarker || ch === ',' || ch === '.' || ch === ';' || ch === ':' || ch === '!' || ch === '?' || ch === '—' || ch === '\n') {
        boundary = i;
        break;
      }
    }

    const window = passage.slice(start, boundary);
    const words = [...window.matchAll(/[A-Za-z][A-Za-z'’-]*/g)];
    if (!words.length) {
      return null;
    }

    let cutoff = null;
    for (let i = 1; i < words.length; i += 1) {
      const word = words[i][0].toLowerCase();
      if (referenceStopWords.has(word)) {
        cutoff = words[i].index;
        break;
      }
    }
    if (cutoff === null && words.length > 3) {
      cutoff = words[3].index;
    }

    const targetRaw = cutoff === null ? window : window.slice(0, cutoff);
    const targetText = targetRaw.trim();
    if (!targetText) {
      return null;
    }
    const targetEnd = start + targetRaw.trimEnd().length;

    return {
      targetText,
      endIndex: targetEnd
    };
  }

  function parseReferenceTargets(passage) {
    const markerPattern = /\(([1-5a-eA-E])\)/g;
    const segments = [];
    let cursor = 0;
    let found = false;
    let match;

    while ((match = markerPattern.exec(passage)) !== null) {
      const markerStart = match.index;
      const markerEnd = markerStart + match[0].length;
      const marker = toMarkerIndex(match[1]);
      const extracted = extractReferenceTarget(passage, markerEnd);

      if (!extracted) {
        continue;
      }

      found = true;
      if (markerStart > cursor) {
        segments.push({ kind: 'text', text: passage.slice(cursor, markerStart) });
      }
      segments.push({
        kind: 'target',
        marker,
        text: extracted.targetText
      });
      cursor = extracted.endIndex;
    }

    if (!found) {
      return null;
    }
    if (cursor < passage.length) {
      segments.push({ kind: 'text', text: passage.slice(cursor) });
    }
    return segments;
  }

  function buildPassageSegments(type, passage, choices) {
    if (typeof passage !== 'string') {
      return [{ kind: 'text', text: '' }];
    }
    const source = normalizeDisplayText(passage);
    const normalizedType = String(type || '').toLowerCase();

    if (normalizedType === 'reference') {
      const parsed = parseReferenceTargets(source);
      if (parsed) {
        return parsed;
      }
      return [{ kind: 'text', text: source }];
    }

    if (normalizedType === 'vocab' || normalizedType === 'grammar' || normalizedType === 'implicit') {
      const tagged = parseTaggedTargets(source);
      if (tagged) {
        return tagged;
      }

      const openTagged = parseOpenMarkerTargets(source, choices);
      if (openTagged) {
        return openTagged;
      }

      const htmlUnderlined = parseHtmlUnderlineTargets(source);
      if (htmlUnderlined) {
        return htmlUnderlined;
      }
    }

    return [{ kind: 'text', text: source }];
  }

  function usesEmbeddedChoices(type) {
    return embeddedChoiceTypes.has(String(type || '').toLowerCase());
  }

  function isInsertionType(type) {
    return String(type || '').toLowerCase() === 'insertion';
  }

  function isImplicitType(type) {
    return String(type || '').toLowerCase() === 'implicit';
  }

  function parseInsertionPassage(rawPassage) {
    const source = normalizeDisplayText(rawPassage);
    if (!source) {
      return { givenSentence: '', body: '' };
    }

    const givenHeader = /\[(주어진 문장|given sentence)\]\s*/i;
    const passageHeader = /\[(지문|passage)\]\s*/i;
    const givenMatch = source.match(givenHeader);
    if (!givenMatch || givenMatch.index === undefined) {
      return { givenSentence: '', body: source };
    }

    const afterGiven = source.slice(givenMatch.index + givenMatch[0].length);
    const passageMatch = afterGiven.match(passageHeader);
    if (passageMatch && passageMatch.index !== undefined) {
      const givenSentence = afterGiven.slice(0, passageMatch.index).trim();
      const body = afterGiven.slice(passageMatch.index + passageMatch[0].length).trim();
      return { givenSentence, body };
    }

    const blankLineIdx = afterGiven.search(/\n\s*\n/);
    if (blankLineIdx >= 0) {
      const givenSentence = afterGiven.slice(0, blankLineIdx).trim();
      const body = afterGiven.slice(blankLineIdx).replace(/^\n+/, '').trim();
      return { givenSentence, body };
    }

    return { givenSentence: '', body: source };
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function stripInsertionGivenPrefix(body, givenSentence) {
    let cleaned = normalizeDisplayText(body).replace(/^\[(주어진 문장|given sentence)\]\s*/i, '').trimStart();
    const expected = normalizeDisplayText(givenSentence);
    if (!expected) {
      return cleaned;
    }

    const candidates = [expected, expected.replace(/[.!?]\s*$/, '').trim()].filter(Boolean);
    for (const candidate of candidates) {
      const pattern = new RegExp(`^${escapeRegExp(candidate)}(?:\\s+|$)`, 'i');
      if (pattern.test(cleaned)) {
        cleaned = cleaned.replace(pattern, '').trimStart();
        break;
      }
    }
    return cleaned;
  }

  function getInsertionDisplay(type, passage, meta) {
    const normalizedPassage = normalizeDisplayText(passage);
    if (!isInsertionType(type)) {
      return { givenSentence: '', body: normalizedPassage };
    }

    const parsed = parseInsertionPassage(normalizedPassage);
    const metaGiven =
      meta && typeof meta.given_sentence === 'string' ? normalizeDisplayText(meta.given_sentence) : '';
    const givenSentence = parsed.givenSentence || metaGiven;
    const rawBody = parsed.body || normalizedPassage;
    const body = stripInsertionGivenPrefix(rawBody, givenSentence) || rawBody;
    return { givenSentence, body };
  }

  function getInsertionGivenSentence(type, passage, meta) {
    return getInsertionDisplay(type, passage, meta).givenSentence;
  }

  function getInsertionBody(type, passage, meta) {
    return getInsertionDisplay(type, passage, meta).body;
  }

  function isSummaryType(type) {
    return String(type || '').toLowerCase() === 'summary';
  }

  function splitSummaryByDivider(source) {
    if (!source) {
      return null;
    }

    const dividerPatterns = [
      /(?:^|\n)\s*[↓↘↙↗↖→➜➡]+\s*/,
      /\s+[↓↘↙↗↖→➜➡]+\s+/
    ];

    for (const pattern of dividerPatterns) {
      const match = source.match(pattern);
      if (!match || match.index === undefined) {
        continue;
      }
      const body = source.slice(0, match.index).trim();
      const summary = source.slice(match.index + match[0].length).trim();
      if (body && summary) {
        return { body, summary };
      }
    }

    return null;
  }

  function parseSummaryPassage(rawPassage) {
    const source = normalizeDisplayText(rawPassage);
    if (!source) {
      return { body: '', summary: '' };
    }

    const headerPatterns = [
      /\[\s*(summary(?:\s*sentence)?|요약문|요약)\s*\]\s*/i,
      /(?:^|\n)\s*(summary(?:\s*sentence)?|요약문|요약)\s*[:：]\s*/i,
      /(?:^|\n)\s*(summary(?:\s*sentence)?|요약문|요약)\s*\n/i
    ];

    for (const pattern of headerPatterns) {
      const match = source.match(pattern);
      if (!match || match.index === undefined) {
        continue;
      }
      const body = source.slice(0, match.index).trim();
      const trailing = source.slice(match.index + match[0].length).trim();
      if (body) {
        return { body, summary: trailing };
      }
      const divided = splitSummaryByDivider(trailing);
      if (divided) {
        return divided;
      }
      return { body: '', summary: trailing };
    }

    const divided = splitSummaryByDivider(source);
    if (divided) {
      return divided;
    }

    return { body: '', summary: source };
  }

  function getSummaryBody(type, passage) {
    if (!isSummaryType(type)) {
      return '';
    }
    return parseSummaryPassage(passage).body;
  }

  function getSummaryText(type, passage) {
    if (!isSummaryType(type)) {
      return '';
    }
    return parseSummaryPassage(passage).summary;
  }

  function parseSummaryChoice(text) {
    const raw = normalizeDisplayText(text);
    const match = raw.match(/^\(\s*(.*?)\s*,\s*(.*?)\s*\)$/);
    if (!match) {
      return null;
    }
    return {
      a: match[1].trim(),
      b: match[2].trim()
    };
  }
</script>

<div class="page-bg"></div>
<div class="page-wrap">
  <header class="hero panel">
    <p class="eyebrow">Exam Item Studio</p>
    <h1>영어 지문 문항 생성 UI</h1>
    <p>
      문항 유형, 난이도, 생성 옵션을 조합해서 결과를 즉시 확인할 수 있습니다.
    </p>
    <div class="hero-meta">
      <span class={`status ${health}`}>API {health === 'online' ? 'online' : health === 'offline' ? 'offline' : 'checking'}</span>
      <code>{endpoint}</code>
    </div>
  </header>

  <main class="workspace">
    <section class="panel controls">
      <div class="field">
        <label for="apiPrefix">API Prefix</label>
        <input
          id="apiPrefix"
          type="text"
          bind:value={apiPrefix}
          placeholder="/api/v1"
          on:change={() => (apiPrefix = normalizePrefix(apiPrefix))}
        />
      </div>

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

      <div class="field inline-grid">
        <div>
          <label for="seed">Seed (optional)</label>
          <input id="seed" type="number" bind:value={form.seed} placeholder="123" />
        </div>
        <div class="toggles">
          <label><input type="checkbox" bind:checked={form.explain} /> 해설 포함</label>
          <label><input type="checkbox" bind:checked={form.return_korean_stem} /> 한국어 지시문</label>
          <label><input type="checkbox" bind:checked={form.debug} /> Debug meta</label>
        </div>
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
        {#if result}
          <button class="ghost" type="button" on:click={copyJson}>{copied ? '복사됨' : 'JSON 복사'}</button>
        {/if}
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
        <article class="item-card">
          <h3>{String(result.type || '').toUpperCase()}</h3>
          <p class="question">{result.question}</p>
          {#if isInsertionType(result.type) && getInsertionGivenSentence(result.type, result.passage, result.meta)}
            <section class="given-box">
              <p class="given-label">주어진 문장</p>
              <p class="given-text">{getInsertionGivenSentence(result.type, result.passage, result.meta)}</p>
            </section>
          {/if}
          {#if isSummaryType(result.type)}
            {#if getSummaryBody(result.type, result.passage)}
              <div class="passage">{getSummaryBody(result.type, result.passage)}</div>
            {/if}
            {#if getSummaryBody(result.type, result.passage) && getSummaryText(result.type, result.passage)}
              <p class="summary-divider">↓</p>
            {/if}
            {#if getSummaryText(result.type, result.passage)}
              <section class="summary-box">
                <p class="summary-label">Summary Sentence</p>
                <p class="summary-text">{getSummaryText(result.type, result.passage)}</p>
              </section>
            {/if}
          {:else}
            <div class="passage">
              {#each buildPassageSegments(result.type, getInsertionBody(result.type, result.passage, result.meta), result.choices) as segment}
                {#if segment.kind === 'target'}
                  {#if isImplicitType(result.type)}
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

          {#if usesEmbeddedChoices(result.type)}
            <p class="choice-note">선택지는 지문 내부 표식 사용 • 정답 {result.answer?.label}</p>
          {:else}
            <ul class="choice-list">
              {#each result.choices || [] as choice}
                <li class:correct={choice.label === result.answer?.label}>
                  <span class="choice-label">{choice.label}</span>
                  {#if isSummaryType(result.type)}
                    {@const pair = parseSummaryChoice(choice.text)}
                    {#if pair}
                      <p class="summary-choice">(A) {pair.a} / (B) {pair.b}</p>
                    {:else}
                      <p>{choice.text}</p>
                    {/if}
                  {:else}
                    <p>{choice.text}</p>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}

          <section class="explanation">
            <p class="answer-line">답: {result.answer?.label || '-'}</p>
            {#if result.explanation}
              <p>{result.explanation}</p>
            {/if}
          </section>

          {#if result.meta && Object.keys(result.meta).length}
            <div class="meta-grid">
              {#each Object.entries(result.meta) as [key, value]}
                <div>
                  <small>{key}</small>
                  <p>{formatMetaValue(value)}</p>
                </div>
              {/each}
            </div>
          {/if}
        </article>

        <details class="raw-json">
          <summary>Raw JSON</summary>
          <pre>{prettyJson}</pre>
        </details>
      {:else}
        <div class="empty-box">
          <h3>아직 결과가 없습니다</h3>
          <p>좌측에서 지문과 유형을 설정한 뒤 문항 생성을 실행해 주세요.</p>
        </div>
      {/if}
    </section>
  </main>
</div>
