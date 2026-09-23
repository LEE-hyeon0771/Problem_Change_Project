/**
 * SSE(Server-Sent Events) 스트리밍 요청 헬퍼.
 *
 * EventSource는 GET만 지원하므로 fetch + ReadableStream으로 직접 파싱합니다.
 * 백엔드가 보내는 이벤트: status / partial / done / error
 */

import { extractDetail } from './client.js';

function parseFrame(frame) {
  let event = 'message';
  const dataLines = [];

  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) {
    return null;
  }

  try {
    return { event, data: JSON.parse(dataLines.join('\n')) };
  } catch {
    return null;
  }
}

/**
 * @returns {Promise<object>} `done` 이벤트의 페이로드
 */
export async function streamJson(url, payload, options = {}) {
  const { onStatus = () => {}, onPartial = () => {}, signal } = options;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal
  });

  if (!response.ok) {
    // 스트림이 시작되기도 전에 실패한 경우(검증 오류 등)는 평범한 JSON 응답입니다.
    throw new Error(extractDetail(await response.text(), response.status));
  }

  if (!response.body) {
    throw new Error('이 브라우저는 스트리밍 응답을 지원하지 않습니다.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result = null;
  let streamError = null;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // SSE 프레임은 빈 줄로 구분됩니다. 마지막 조각은 아직 미완성일 수 있어 남겨 둡니다.
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        const parsed = parseFrame(frame);
        if (!parsed) {
          continue;
        }
        if (parsed.event === 'status') {
          onStatus(parsed.data);
        } else if (parsed.event === 'partial') {
          onPartial(parsed.data);
        } else if (parsed.event === 'done') {
          result = parsed.data;
        } else if (parsed.event === 'error') {
          streamError = new Error(parsed.data?.detail || '생성에 실패했습니다.');
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (streamError) {
    throw streamError;
  }
  if (!result) {
    throw new Error('스트림이 결과 없이 종료되었습니다.');
  }
  return result;
}
