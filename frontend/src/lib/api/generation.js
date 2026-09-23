/** 스트리밍 생성 API. */

import { normalizePrefix } from '../problemUtils.js';
import { streamJson } from './stream.js';

export function streamProblem(prefix, problemType, payload, handlers) {
  return streamJson(`${normalizePrefix(prefix)}/stream/${problemType}`, payload, handlers);
}

export function streamWordbook(prefix, payload, handlers) {
  return streamJson(`${normalizePrefix(prefix)}/stream-wordbook`, payload, handlers);
}
