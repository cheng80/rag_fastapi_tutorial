#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}"
LOG_DIR="${LOG_DIR:-data/generated/tour_api/tunnel_logs}"
UVICORN_LOG="${LOG_DIR}/release_uvicorn.log"
TUNNEL_LOG="${LOG_DIR}/release_cloudflared.log"
PUBLIC_URL_FILE="${LOG_DIR}/release_public_url.txt"

mkdir -p "$LOG_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[error] .venv/bin/python 이 없습니다. 프로젝트 루트에서 .venv를 먼저 준비하세요." >&2
  exit 1
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "[error] cloudflared 명령을 찾지 못했습니다. 설치 후 다시 실행하세요." >&2
  echo "        macOS 예: brew install cloudflared" >&2
  exit 1
fi

UVICORN_STARTED=false
TUNNEL_STARTED=false

cleanup() {
  if [[ "$UVICORN_STARTED" == "true" || "$TUNNEL_STARTED" == "true" ]]; then
    echo
    echo "[stop] 이 스크립트가 시작한 서버와 터널을 종료합니다."
  fi
  [[ "$TUNNEL_STARTED" == "true" && -n "${TUNNEL_PID:-}" ]] && kill "$TUNNEL_PID" >/dev/null 2>&1 || true
  [[ "$UVICORN_STARTED" == "true" && -n "${UVICORN_PID:-}" ]] && kill "$UVICORN_PID" >/dev/null 2>&1 || true
}
trap cleanup INT TERM EXIT

health_ok() {
  curl -fsS "${BASE_URL}/health" >/dev/null 2>&1
}

existing_public_url() {
  local candidate=""
  for file in "$PUBLIC_URL_FILE" "${LOG_DIR}/debug_public_url.txt"; do
    if [[ -f "$file" ]]; then
      candidate="$(tail -n 1 "$file" | tr -d '[:space:]')"
      if [[ -n "$candidate" ]] && curl -fsS "${candidate}/health" >/dev/null 2>&1; then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done
  candidate="$(grep -RhsEo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' "$LOG_DIR"/*_cloudflared.log 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$candidate" ]] && curl -fsS "${candidate}/health" >/dev/null 2>&1; then
    printf '%s\n' "$candidate"
    return 0
  fi
  return 1
}

if health_ok; then
  echo "[reuse] 기존 FastAPI 서버 사용: ${BASE_URL}"
else
  if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[error] ${PORT} 포트는 사용 중이지만 ${BASE_URL}/health 가 응답하지 않습니다." >&2
    echo "        기존 프로세스를 확인하거나 PORT=다른번호 로 실행하세요." >&2
    exit 1
  fi
  : > "$UVICORN_LOG"
  echo "[start] FastAPI release server: ${BASE_URL}"
  TOURISM_LIVE_LOOKUP_ENABLED="${TOURISM_LIVE_LOOKUP_ENABLED:-true}" \
  TOURISM_REASONING_ASSIST_ENABLED="${TOURISM_REASONING_ASSIST_ENABLED:-false}" \
  ".venv/bin/python" -m uvicorn app.main:app --host "$HOST" --port "$PORT" >"$UVICORN_LOG" 2>&1 &
  UVICORN_PID="$!"
  UVICORN_STARTED=true

  echo "[wait] /health 확인 중..."
  for _ in {1..60}; do
    if health_ok; then
      break
    fi
    sleep 1
  done

  if ! health_ok; then
    echo "[error] FastAPI health check 실패. 로그: ${UVICORN_LOG}" >&2
    tail -n 80 "$UVICORN_LOG" >&2 || true
    exit 1
  fi
fi

PUBLIC_URL="$(existing_public_url || true)"
if [[ -n "$PUBLIC_URL" ]]; then
  echo "[reuse] 기존 Cloudflare tunnel 사용: ${PUBLIC_URL}"
else
  : > "$TUNNEL_LOG"
  rm -f "$PUBLIC_URL_FILE"
  echo "[start] Cloudflare Quick Tunnel -> ${BASE_URL}"
  cloudflared tunnel --url "$BASE_URL" >"$TUNNEL_LOG" 2>&1 &
  TUNNEL_PID="$!"
  TUNNEL_STARTED=true

  echo "[wait] public trycloudflare URL 검출 중..."
  PUBLIC_URL=""
  for _ in {1..90}; do
    PUBLIC_URL="$(grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' "$TUNNEL_LOG" | tail -n 1 || true)"
    if [[ -n "$PUBLIC_URL" ]]; then
      break
    fi
    if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
      echo "[error] cloudflared가 종료되었습니다. 로그: ${TUNNEL_LOG}" >&2
      cat "$TUNNEL_LOG" >&2 || true
      exit 1
    fi
    sleep 1
  done

  if [[ -z "$PUBLIC_URL" ]]; then
    echo "[error] public URL을 찾지 못했습니다. 로그: ${TUNNEL_LOG}" >&2
    cat "$TUNNEL_LOG" >&2 || true
    exit 1
  fi
fi

DEBUG_URL="${PUBLIC_URL}/tourism-ui/"
RELEASE_URL="${PUBLIC_URL}/tourism-ui/?mode=release"
printf '%s\n' "$PUBLIC_URL" > "$PUBLIC_URL_FILE"

echo
echo "========================================"
echo "무장애 관광 챗봇 release tunnel ready"
echo "Public base: ${PUBLIC_URL}"
echo "Release UI : ${RELEASE_URL}"
echo "Debug UI   : ${DEBUG_URL}"
echo "Uvicorn log: ${UVICORN_LOG}"
echo "Tunnel log : ${TUNNEL_LOG}"
echo "========================================"
echo

if [[ "${OPEN_BROWSER:-true}" == "true" ]] && command -v open >/dev/null 2>&1; then
  open "$RELEASE_URL"
fi

if [[ "$UVICORN_STARTED" != "true" && "$TUNNEL_STARTED" != "true" ]]; then
  echo "[done] 기존 서버/터널 주소를 열었습니다. 새로 종료할 프로세스는 없습니다."
  trap - INT TERM EXIT
  exit 0
fi

echo "[logs] Ctrl+C를 누르면 이 스크립트가 시작한 서버/터널이 종료됩니다."
tail -n 20 -f "$UVICORN_LOG" "$TUNNEL_LOG" &
TAIL_PID="$!"
if [[ "$UVICORN_STARTED" == "true" && "$TUNNEL_STARTED" == "true" ]]; then
  wait "$UVICORN_PID" "$TUNNEL_PID"
elif [[ "$UVICORN_STARTED" == "true" ]]; then
  wait "$UVICORN_PID"
else
  wait "$TUNNEL_PID"
fi
kill "$TAIL_PID" >/dev/null 2>&1 || true
