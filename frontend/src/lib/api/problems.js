/** 변형문항 API. 엔드포인트 경로를 아는 곳은 여기뿐입니다. */

import { normalizePrefix } from '../problemUtils.js';
import { getList, postJson } from './client.js';

const base = (prefix) => `${normalizePrefix(prefix)}/problems`;

export function listProblems(prefix, limit = 300) {
  return getList(`${base(prefix)}?limit=${limit}`);
}

/** "사용" 버튼. 이걸 호출해야만 개인DB에 저장됩니다. */
export function saveProblem(prefix, { request, result }) {
  return postJson(base(prefix), { request, result });
}
