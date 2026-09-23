#!/usr/bin/env bash
#
# 다른 사람에게 보낼 zip 파일을 만듭니다.
#
#   ./package.sh              # ~/Desktop 에 zip 생성
#   ./package.sh --with-data  # 내가 저장한 문제/단어장도 함께 포함
#   ./package.sh --with-env   # .env(API 키 포함)도 함께 포함  ※ 기본은 제외
#
# 왜 이 스크립트가 필요한가:
#   - .venv 는 이 컴퓨터의 경로와 OS에 고정되어 있어 다른 PC에서 100% 깨집니다.
#   - node_modules 도 darwin-arm64 전용 바이너리를 포함합니다.
#   - .env 에는 API 키가 들어 있어 그냥 보내면 키가 유출됩니다.
#   둘 다 받는 쪽에서 dev.bat / dev.sh 가 자동으로 다시 만들어 줍니다.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

WITH_DATA=0
WITH_ENV=0
for arg in "$@"; do
  case "$arg" in
    --with-data) WITH_DATA=1 ;;
    --with-env)  WITH_ENV=1 ;;
    -h|--help)   sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "알 수 없는 옵션: $arg" >&2; exit 2 ;;
  esac
done

NAME="$(basename "$ROOT")"
STAMP="$(date +%Y%m%d)"
OUT="${HOME}/Desktop/${NAME}_${STAMP}.zip"
STAGE="$(mktemp -d)/${NAME}"

cleanup() { rm -rf "$(dirname "$STAGE")"; }
trap cleanup EXIT

echo "[pack] 복사 중..."
mkdir -p "$STAGE"

# rsync 로 제외 목록을 적용해 복사합니다.
# rsync 는 "먼저 일치하는 규칙"이 이깁니다. include 를 반드시 exclude 보다 앞에 둡니다.
EXCLUDES=(--include ".env.example")

if [ "$WITH_ENV" -eq 1 ]; then
  EXCLUDES+=(--include ".env")
fi

# .env.example(과 --with-env 일 때의 .env)을 제외한 모든 .env* 를 막습니다.
# .env.bak 같은 백업 파일에도 API 키가 들어 있어서 한 번에 차단해야 합니다.
EXCLUDES+=(--exclude ".env*")

EXCLUDES+=(
  --exclude ".venv/"
  --exclude ".venv-wsl/"
  --exclude "frontend/node_modules/"
  --exclude "frontend/dist/"
  --exclude ".git/"
  --exclude "__pycache__/"
  --exclude "*.pyc"
  --exclude ".pytest_cache/"
  --exclude ".DS_Store"
  --exclude ".logs/"
  --exclude "problem_log/"
  --exclude ".claude/"
)

if [ "$WITH_DATA" -eq 0 ]; then
  # 내가 저장한 문제/단어장은 개인 자료라 기본적으로 뺍니다.
  EXCLUDES+=(--exclude "backend/problems/*" --exclude "backend/wordbooks/")
fi

rsync -a "${EXCLUDES[@]}" ./ "$STAGE/"

# 저장 폴더 자체는 살려 둡니다(스키마 파일은 코드가 참조합니다).
mkdir -p "$STAGE/backend/problems"
if [ -f "backend/problems/problem_record.schema.json" ]; then
  cp backend/problems/problem_record.schema.json "$STAGE/backend/problems/"
fi

# 실행 권한 보장 (zip 이 권한을 잃어버리는 경우 대비해 안내문에도 적어 둡니다)
chmod +x "$STAGE/dev.sh" "$STAGE/package.sh" 2>/dev/null || true

echo "[pack] 압축 중..."
rm -f "$OUT"
(cd "$(dirname "$STAGE")" && zip -rq "$OUT" "$(basename "$STAGE")" -x '*.DS_Store')

echo
echo "  완료: $OUT"
echo "  크기: $(du -h "$OUT" | cut -f1)"
echo
echo "  포함 안 된 것 (받는 쪽에서 자동 생성됩니다):"
echo "    .venv, frontend/node_modules, .git, 캐시, 로그"
[ "$WITH_ENV" -eq 0 ] && echo "    .env (API 키) — 받는 사람이 본인 키를 넣어야 합니다"
[ "$WITH_DATA" -eq 0 ] && echo "    내가 저장한 문제/단어장"
echo
echo "  받는 사람은 압축을 푼 뒤 START_HERE.md 를 읽으면 됩니다."
