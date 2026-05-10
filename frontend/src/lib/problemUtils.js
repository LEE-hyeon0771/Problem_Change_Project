export const typeOptions = [
  { value: 'title', label: '제목', hint: '핵심 내용을 가장 잘 담은 제목' },
  { value: 'topic', label: '주제', hint: '글 전체의 중심 내용' },
  { value: 'blank', label: '빈칸', hint: '문맥상 들어갈 표현' },
  { value: 'summary', label: '요약', hint: '요약문의 빈칸 조합' },
  { value: 'implicit', label: '함축의미', hint: '밑줄 표현의 의미' },
  { value: 'insertion', label: '삽입', hint: '주어진 문장의 위치' },
  { value: 'order', label: '순서', hint: '글의 올바른 배열' },
  { value: 'irrelevant', label: '무관문장', hint: '흐름과 관계없는 문장' },
  { value: 'reference', label: '지칭', hint: '대명사가 가리키는 대상' },
  { value: 'vocab', label: '어휘', hint: '문맥상 어색한 어휘' },
  { value: 'grammar', label: '어법', hint: '문법적으로 어색한 부분' }
];

export const samplePassage = `People often rely on routines because habits reduce cognitive load and help preserve attention for demanding tasks. However, routines can also hide weak assumptions when individuals stop examining why they act in familiar ways. In many workplaces, teams repeat procedures simply because they were effective in a previous context. As conditions change, those same procedures may become less useful, even though they still feel comfortable. Therefore, effective decision making requires both stability and periodic review. By combining consistent practice with deliberate reflection, people can keep the benefits of habits while avoiding blind repetition.`;

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

export function normalizePrefix(value) {
  const trimmed = value.trim();
  if (!trimmed) {
    return '/api/v1';
  }
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
}

export function typeLabel(type) {
  return typeOptions.find((option) => option.value === type)?.label || String(type || '').toUpperCase();
}

export function formatDate(value) {
  if (!value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

export function normalizeDisplayText(value) {
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

export function previewText(value, limit = 150) {
  const text = normalizeDisplayText(value);
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, limit).trim()}...`;
}

export function formatMetaValue(value) {
  if (value === null || value === undefined) {
    return 'null';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

export function toMarkerIndex(raw) {
  const value = String(raw).trim().toLowerCase();
  if (/^[1-5]$/.test(value)) {
    return value;
  }
  if (/^[a-e]$/.test(value)) {
    return String(value.charCodeAt(0) - 96);
  }
  return value;
}

export function toMarkerDisplay(raw) {
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

export function buildPassageSegments(type, passage, choices) {
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

export function usesEmbeddedChoices(type) {
  return embeddedChoiceTypes.has(String(type || '').toLowerCase());
}

export function isInsertionType(type) {
  return String(type || '').toLowerCase() === 'insertion';
}

export function isImplicitType(type) {
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

export function getInsertionGivenSentence(type, passage, meta) {
  return getInsertionDisplay(type, passage, meta).givenSentence;
}

export function getInsertionBody(type, passage, meta) {
  return getInsertionDisplay(type, passage, meta).body;
}

export function isSummaryType(type) {
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

export function getSummaryBody(type, passage) {
  if (!isSummaryType(type)) {
    return '';
  }
  return parseSummaryPassage(passage).body;
}

export function getSummaryText(type, passage) {
  if (!isSummaryType(type)) {
    return '';
  }
  return parseSummaryPassage(passage).summary;
}

export function parseSummaryChoice(text) {
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
