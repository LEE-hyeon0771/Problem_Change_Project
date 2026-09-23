<script>
  import WordCard from './wordbook/WordCard.svelte';
  import { formatDate, previewText } from '../lib/problemUtils.js';

  export let savedWordbooks = [];
  export let loading = false;
  export let error = '';
  export let onRefresh = () => {};
  export let onDeleted = () => {};
  export let apiPrefix = '/api/v1';

  let search = '';
  // 펼친 단어장 uid 집합. 기본은 모두 접힘 — 지문만 보이고 자리를 적게 차지합니다.
  let expanded = new Set();
  let deletingUid = '';
  let deleteError = '';

  $: filtered = filterWordbooks(savedWordbooks, search);

  function filterWordbooks(records, needle) {
    const query = needle.trim().toLowerCase();
    if (!query) {
      return records;
    }
    return records.filter((record) => {
      const haystack = [
        record.title,
        record.result?.passage,
        ...(record.result?.entries || []).map((entry) => `${entry.headword} ${entry.passage_meaning_ko}`)
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(query);
    });
  }

  function isOpen(uid, currentExpanded) {
    return currentExpanded.has(uid);
  }

  function toggle(uid) {
    // Set은 변경해도 Svelte가 감지하지 못하므로 새 Set으로 교체합니다.
    const next = new Set(expanded);
    if (next.has(uid)) {
      next.delete(uid);
    } else {
      next.add(uid);
    }
    expanded = next;
  }

  function expandAll() {
    expanded = new Set(filtered.map((record) => record.wordbook_uid));
  }

  function collapseAll() {
    expanded = new Set();
  }

  async function removeWordbook(record) {
    if (deletingUid) {
      return;
    }
    deletingUid = record.wordbook_uid;
    deleteError = '';

    try {
      await deleteWordbook(apiPrefix, record.wordbook_uid);
      onDeleted();
    } catch (err) {
      deleteError = err instanceof Error ? err.message : '삭제에 실패했습니다.';
    } finally {
      deletingUid = '';
    }
  }
</script>

<section class="panel library-panel">
  <div class="library-head">
    <div>
      <p class="eyebrow">개인DB · 단어장</p>
      <h2>저장된 단어장</h2>
      <p>"사용"을 누른 단어장이 쌓입니다. 지문 제목을 누르면 정리된 단어가 펼쳐집니다.</p>
    </div>
    <button class="ghost" type="button" on:click={onRefresh} disabled={loading}>
      {loading ? '불러오는 중...' : '새로고침'}
    </button>
  </div>

  <div class="wordbook-tools">
    <label>
      검색
      <input type="text" bind:value={search} placeholder="제목, 지문, 단어 검색" />
    </label>
    <div class="accordion-actions">
      <button class="ghost" type="button" on:click={expandAll} disabled={!filtered.length}>모두 펼치기</button>
      <button class="ghost" type="button" on:click={collapseAll} disabled={!expanded.size}>모두 접기</button>
    </div>
  </div>

  {#if error}
    <div class="error-box">
      <strong>단어장 조회 실패</strong>
      <p>{error}</p>
    </div>
  {:else if deleteError}
    <div class="error-box">
      <strong>삭제 실패</strong>
      <p>{deleteError}</p>
    </div>
  {/if}

  {#if loading}
    <div class="skeleton library-skeleton">
      <span></span>
      <span></span>
      <span></span>
    </div>
  {:else if filtered.length}
    <div class="wordbook-accordion">
      {#each filtered as record (record.wordbook_uid)}
        {@const open = isOpen(record.wordbook_uid, expanded)}
        <article class="wordbook-folder" class:open>
          <div class="folder-head">
            <button
              class="folder-toggle"
              type="button"
              aria-expanded={open}
              on:click={() => toggle(record.wordbook_uid)}
            >
              <span class="folder-caret" aria-hidden="true">▾</span>
              <span class="folder-title">
                <strong>{record.title || '제목 없는 단어장'}</strong>
                <small>{record.entry_count}단어 · {formatDate(record.created_at)}</small>
              </span>
            </button>
            <button
              class="ghost danger folder-delete"
              type="button"
              disabled={deletingUid === record.wordbook_uid}
              on:click={() => removeWordbook(record)}
            >
              {deletingUid === record.wordbook_uid ? '삭제 중...' : '삭제'}
            </button>
          </div>

          <p class="folder-passage">{previewText(record.result?.passage, open ? 100000 : 160)}</p>

          {#if open}
            <div class="folder-body">
              <div class="wordbook-list flat">
                {#each record.result?.entries || [] as entry}
                  <WordCard {entry} />
                {/each}
              </div>
            </div>
          {/if}
        </article>
      {/each}
    </div>
  {:else}
    <div class="empty-box">
      <h3>저장된 단어장이 없습니다</h3>
      <p>핵심단어장 화면에서 단어장을 만든 뒤 "사용"을 누르면 이곳에 쌓입니다.</p>
    </div>
  {/if}
</section>
