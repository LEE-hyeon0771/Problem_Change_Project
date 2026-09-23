<script>
  export let problemCount = 0;
  export let wordbookCount = 0;
  export let onSelect = () => {};

  const sections = [
    {
      id: 'problems',
      label: '변형문제',
      tagline: '내가 저장한 문항',
      description: '"사용"을 누른 변형문제가 쌓입니다. 여기서 골라 모의고사 문제지를 만듭니다.'
    },
    {
      id: 'wordbooks',
      label: '단어장',
      tagline: '내가 저장한 단어',
      description: '"사용"을 누른 단어장이 쌓입니다. 지문별로 접혀 있고, 펼치면 정리된 단어가 나옵니다.'
    }
  ];

  function countFor(id) {
    return id === 'problems' ? problemCount : wordbookCount;
  }
</script>

<div class="hub">
  <div class="hub-inner">
    <p class="eyebrow">개인DB</p>
    <h2>무엇을 열어볼까요?</h2>
    <p class="hub-lead">저장한 자료를 종류별로 나눠 두었습니다.</p>

    <div class="hub-grid" role="group" aria-label="개인DB 구분">
      {#each sections as section}
        <button class="home-card" type="button" on:click={() => onSelect(section.id)}>
          <span class="home-card-tagline">{section.tagline}</span>
          <strong>{section.label}</strong>
          <p>{section.description}</p>
          <span class="home-card-go">
            열기
            <em>{countFor(section.id)}개</em>
          </span>
        </button>
      {/each}
    </div>
  </div>
</div>
