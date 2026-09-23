/**
 * 모든 API 호출이 지나는 단일 통로.
 *
 * 컴포넌트에서 `fetch` 를 직접 부르지 마세요. 에러 응답을 파싱하는 코드가
 * 파일마다 복제되고, 백엔드 에러 형식이 바뀌면 전부 찾아 고쳐야 합니다.
 */

/** 백엔드는 실패 시 `{"detail": ...}` 를 주지만, 프록시 오류 등은 평문일 수 있습니다. */
function extractDetail(raw, status) {
  try {
    const parsed = JSON.parse(raw);
    const detail = parsed?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (detail) {
      return JSON.stringify(detail);
    }
  } catch {
    /* JSON 이 아니면 원문을 그대로 씁니다. */
  }
  return raw || `HTTP ${status}`;
}

/**
 * JSON 응답을 돌려주는 요청. 실패하면 읽을 수 있는 메시지로 throw 합니다.
 * @returns {Promise<any>} 204 응답은 null
 */
export async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const raw = await response.text();

  if (!response.ok) {
    throw new Error(extractDetail(raw, response.status));
  }

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    throw new Error('응답 JSON 파싱에 실패했습니다.');
  }
}

export function getJson(url) {
  return requestJson(url);
}

export function postJson(url, body) {
  return requestJson(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
}

export async function deleteResource(url) {
  const response = await fetch(url, { method: 'DELETE' });
  // 이미 지워진 것을 다시 지우는 건 실패로 보지 않습니다.
  if (!response.ok && response.status !== 404) {
    throw new Error(extractDetail(await response.text(), response.status));
  }
}

/** 목록 엔드포인트는 배열이어야 합니다. 형식이 깨지면 화면이 조용히 비어버립니다. */
export async function getList(url) {
  const parsed = await getJson(url);
  if (!Array.isArray(parsed)) {
    throw new Error('저장소 응답 형식이 올바르지 않습니다.');
  }
  return parsed;
}

export { extractDetail };
