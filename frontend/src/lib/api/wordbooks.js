/** 핵심단어장 API. */

import { normalizePrefix } from '../problemUtils.js';
import { deleteResource, getList, postJson } from './client.js';

const base = (prefix) => `${normalizePrefix(prefix)}/wordbooks`;

export function listWordbooks(prefix, limit = 300) {
  return getList(`${base(prefix)}?limit=${limit}`);
}

/** "사용" 버튼. 이걸 호출해야만 개인DB에 저장됩니다. */
export function saveWordbook(prefix, { title, request, result }) {
  return postJson(base(prefix), { title, request, result });
}

export function deleteWordbook(prefix, wordbookUid) {
  return deleteResource(`${base(prefix)}/${wordbookUid}`);
}
