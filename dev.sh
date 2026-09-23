#!/usr/bin/env bash
#
# 백엔드(uvicorn) + 프론트엔드(vite)를 한 번에 띄우는 개발용 스크립트.
#
#   ./dev.sh              # 의존성 확인 후 두 서버 모두 실행 (Ctrl+C로 전부 종료)
#   ./dev.sh --no-reload  # uvicorn --reload 끄기
#   ./dev.sh --skip-install  # 의존성 설치/동기화 건너뛰기
#
# 환경변수로 덮어쓰기 가능:
#   BACKEND_HOST(0.0.0.0) BACKEND_PORT(8100) FRONTEND_PORT(5174) PYTHON_VERSION(3.12)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8100}"
export BACKEND_PORT   # frontend/vite.config.js가 proxy target 포트로 사용
# 5173은 이 맥에서 다른 프로젝트(mitam-math-1)가 --strictPort로 선점 중이라 5174를 기본값으로 씁니다.
FRONTEND_PORT="${FRONTEND_PORT:-5174}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

# Makefile과 동일한 규칙: .venv-wsl이 있으면 그걸 쓰고, 없으면 .venv
if [ -d "$ROOT/.venv-wsl" ]; then
  VENV_DIR=".venv-wsl"
else
  VENV_DIR=".venv"
fi
export UV_PROJECT_ENVIRONMENT="$VENV_DIR"

RELOAD=1
SKIP_INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --no-reload) RELOAD=0 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "알 수 없는 옵션: $arg (사용법: $0 --help)" >&2; exit 2 ;;
  esac
done

LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_PID=""
FRONTEND_PID=""
TAIL_PIDS=()

info()  { printf '\033[36m[dev]\033[0m %s\n' "$*"; }
warn()  { printf '\033[33m[dev]\033[0m %s\n' "$*"; }
die()   { printf '\033[31m[dev]\033[0m %s\n' "$*" >&2; exit 1; }

# 자식 프로세스까지 재귀적으로 종료 (uv run -> uvicorn, npm -> vite)
kill_tree() {
  local pid="$1" child
  [ -n "$pid" ] || return 0
  kill -0 "$pid" 2>/dev/null || return 0
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    kill_tree "$child"
  done
  kill -TERM "$pid" 2>/dev/null || true
}

cleanup() {
  trap - INT TERM EXIT
  # 서버가 뜨기 전에 빠져나온 경우(사전 점검 실패 등)는 조용히 종료
  if [ -z "$BACKEND_PID" ] && [ -z "$FRONTEND_PID" ]; then
    return
  fi
  echo
  info "종료 중..."
  kill_tree "$FRONTEND_PID"
  kill_tree "$BACKEND_PID"
  for pid in "${TAIL_PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  info "정리 완료. 로그는 $LOG_DIR 에 남아 있습니다."
}
trap cleanup INT TERM EXIT

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# --- 사전 점검 -------------------------------------------------------------

command -v uv  >/dev/null 2>&1 || die "uv가 없습니다. https://docs.astral.sh/uv/ 참고해서 설치해 주세요."
command -v npm >/dev/null 2>&1 || die "npm(node)이 없습니다. Node.js를 설치해 주세요."

[ -f "$ROOT/.env" ] || warn ".env 파일이 없습니다. 백엔드가 기본값으로 뜹니다."

for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  if port_in_use "$port"; then
    # 무엇이 물고 있는지까지 알려줘야 바로 판단할 수 있습니다.
    holder_pid="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -1)"
    holder_cmd="$(ps -o command= -p "$holder_pid" 2>/dev/null | cut -c1-120)"
    warn "포트 $port 사용 중: pid $holder_pid"
    [ -n "$holder_cmd" ] && warn "  $holder_cmd"
    die "해당 프로세스를 종료(kill $holder_pid)하거나 BACKEND_PORT/FRONTEND_PORT 로 바꿔 주세요."
  fi
done

# --- 의존성 동기화 ---------------------------------------------------------

if [ "$SKIP_INSTALL" -eq 0 ]; then
  info "python 의존성 동기화 중 ($VENV_DIR, python $PYTHON_VERSION)..."
  uv sync --frozen --python "$PYTHON_VERSION"

  if [ ! -d "$ROOT/frontend/node_modules" ] \
     || [ "$ROOT/frontend/package-lock.json" -nt "$ROOT/frontend/node_modules" ]; then
    info "프론트엔드 의존성 설치 중 (npm ci)..."
    (cd "$ROOT/frontend" && npm ci)
  else
    info "프론트엔드 의존성 최신 상태 — 설치 건너뜀."
  fi
else
  info "--skip-install: 의존성 동기화를 건너뜁니다."
fi

# --- 실행 ------------------------------------------------------------------

UVICORN_ARGS=(uvicorn backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT")
[ "$RELOAD" -eq 1 ] && UVICORN_ARGS+=(--reload)

info "백엔드 실행: ${UVICORN_ARGS[*]}"
: > "$BACKEND_LOG"
uv run --no-sync "${UVICORN_ARGS[@]}" > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

info "프론트엔드 실행: npm run dev (port $FRONTEND_PORT, proxy -> :$BACKEND_PORT)"
: > "$FRONTEND_LOG"
(cd "$ROOT/frontend" && npm run dev -- --port "$FRONTEND_PORT") > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# 백엔드 health 대기 (실패해도 계속 진행)
for _ in $(seq 1 40); do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    warn "백엔드가 기동 중 종료됐습니다. 아래 로그를 확인하세요."
    break
  fi
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then
    info "백엔드 준비 완료."
    break
  fi
  sleep 0.5
done

cat <<EOF

  API       http://localhost:$BACKEND_PORT
  Swagger   http://localhost:$BACKEND_PORT/docs
  Frontend  http://localhost:$FRONTEND_PORT

  로그: $BACKEND_LOG / $FRONTEND_LOG
  종료: Ctrl+C

EOF

# 두 서비스 로그를 접두어 붙여 같이 출력
tail -n +1 -f "$BACKEND_LOG"  | awk '{ print "\033[35m[api]\033[0m " $0; fflush() }' &
TAIL_PIDS+=($!)
tail -n +1 -f "$FRONTEND_LOG" | awk '{ print "\033[32m[web]\033[0m " $0; fflush() }' &
TAIL_PIDS+=($!)

# 둘 중 하나라도 죽으면 전체 종료
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done

warn "서비스 중 하나가 종료되어 나머지도 함께 내립니다."
