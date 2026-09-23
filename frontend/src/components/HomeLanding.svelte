<script>
  export let savedCount = 0;
  export let onNavigate = () => {};

  const entries = [
    {
      id: 'create',
      label: '문제변형',
      tagline: '지문 하나로 11개 유형',
      description: '영어 지문을 넣으면 제목·주제·빈칸·어법 등 학평 스타일 변형문항을 만들어 줍니다.'
    },
    {
      id: 'wordbook',
      label: '핵심단어장',
      tagline: '뜻·품사·동의어·반의어',
      description: '지문의 핵심단어를 빠짐없이 뽑고, 뜻마다 품사와 동의어·반의어를 정리해 줍니다.'
    },
    {
      id: 'library',
      label: '개인DB',
      tagline: '내가 만든 문제 보관함',
      description: '생성한 문항이 모두 쌓이는 곳입니다. 여기서 골라 모의고사 시험지로 만들 수 있습니다.'
    }
  ];
</script>

<main class="home">
  <div class="home-inner">
    <p class="eyebrow">영어 변형문제 제작소</p>
    <h1>무엇부터 시작할까요?</h1>
    <p class="home-lead">아래에서 하나를 고르면 바로 해당 작업 화면으로 이동합니다.</p>

    <div class="home-grid" role="group" aria-label="시작 메뉴">
      {#each entries as entry}
        <button class="home-card" type="button" on:click={() => onNavigate(entry.id)}>
          <span class="home-card-tagline">{entry.tagline}</span>
          <strong>{entry.label}</strong>
          <p>{entry.description}</p>
          <span class="home-card-go">
            바로가기
            {#if entry.id === 'library' && savedCount}
              <em>{savedCount}문항</em>
            {/if}
          </span>
        </button>
      {/each}
    </div>
  </div>
</main>
