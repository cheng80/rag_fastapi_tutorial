# Cloudflare RAG Deployment Guide

이 문서는 현재 로컬 RAG 챗봇을 Cloudflare Quick Tunnel 테스트 상태에서 더 재현 가능한 테스트/스테이징 형태로 옮기기 위한 작업 순서다.

## 현재 상태

현재 앱은 다음 구조로 보는 것이 맞다.

```text
Tester
  -> Cloudflare Quick Tunnel temporary URL
  -> local FastAPI API on http://127.0.0.1:8000
  -> local ChromaDB files under data/vector_store/chroma
  -> local Ollama on http://localhost:11434
  -> local answer and source response
```

이 방식은 빠른 외부 테스트에는 충분하지만, URL이 임시이고 접근 제어/관측/재시작 절차가 약하다. 따라서 지금의 목표는 "바로 Cloudflare-native 전체 이전"이 아니라, 먼저 안정적인 터널 기반 테스트 환경을 만드는 것이다.

## 권장 작업 순서

### 1. 로컬 기준선 고정

먼저 로컬 앱이 안정적으로 동작하는지 확인한다.

```bash
cd project root
git status --short
.venv/bin/python --version
.venv/bin/python -m pytest
ollama list
```

문서나 임베딩 모델을 바꿨으면 인덱스를 다시 만든다.

```bash
.venv/bin/python scripts/rebuild_index.py
```

API 서버를 실행한다.

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

로컬 확인:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/documents/stats
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"환불은 언제까지 가능한가요?"}'
```

### 2. Quick Tunnel은 임시 테스트로만 사용

Quick Tunnel은 도메인 없이 바로 외부 URL을 만들 수 있어서 지금 단계의 데모에는 좋다.

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

출력된 `https://...trycloudflare.com` URL로 확인한다.

```bash
curl https://<quick-tunnel-host>/health
curl -X POST https://<quick-tunnel-host>/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"환불은 언제까지 가능한가요?"}'
```

Quick Tunnel은 다음 제한이 있다.

- URL이 임시라서 프론트 앱, 외부 테스터, OAuth redirect 등에 고정하기 어렵다.
- 테스트 재현성이 낮다.
- 운영용 접근 제어와 모니터링 기준을 잡기 어렵다.

### 3. Named Tunnel로 전환

테스트 URL을 고정해야 하면 Named Tunnel로 옮긴다.

```bash
cloudflared tunnel login
cloudflared tunnel create chatbot-rag-test
```

도메인 또는 서브도메인이 있으면 DNS 라우팅을 연결한다.

```bash
cloudflared tunnel route dns chatbot-rag-test api.example.com
```

로컬 config 예시는 다음과 같다. 실제 `credentials-file`은 개인 Mac의 `.cloudflared` 아래에 두고 커밋하지 않는다.

```yaml
tunnel: chatbot-rag-test
credentials-file: ~/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

실행:

```bash
cloudflared tunnel --config ~/.cloudflared/chatbot-rag-test.yml run chatbot-rag-test
```

### 4. 접근 제어 추가

현재 `.env.example`의 `CORS_ORIGINS=*`는 개발에는 편하지만 외부 테스트에는 넓다.

테스트 환경의 로컬 `.env`에서는 가능한 한 실제 프론트 URL만 허용한다.

```env
ENVIRONMENT=test
CORS_ORIGINS=https://app.example.com,http://localhost:3000,http://localhost:5173
```

Cloudflare Access를 붙이면 브라우저 기반 테스터를 이메일 또는 조직 계정 기준으로 제한할 수 있다. `/documents/reindex` 같은 운영성 endpoint는 외부 공개 전에 반드시 인증 정책을 정해야 한다.

### 5. 프론트엔드 공개 방식 결정

현재 repo의 `frontend/web/README.md` 기준으로 웹 프론트는 아직 별도 구현 전이고, 기본 검증은 Jupyter Notebook 또는 Flutter 클라이언트다.

선택지는 다음과 같다.

| 상황 | 권장 방식 |
|---|---|
| API만 외부 테스트 | Named Tunnel로 FastAPI 공개 |
| Flutter 앱에서 API 호출 | Named Tunnel의 고정 API URL 사용 |
| 웹 프론트 추가 | Cloudflare Pages에 정적/SPA 프론트 배포 |
| 서버 로직까지 엣지 이전 | Workers 또는 Pages Functions 검토 |

### 6. Cloudflare-native RAG는 별도 단계로 판단

지금 구조는 로컬 Ollama와 로컬 ChromaDB에 강하게 묶여 있다. 따라서 전체를 한 번에 Cloudflare로 옮기기보다 아래 매핑을 기준으로 단계별 판단을 한다.

| 현재 구성 | Cloudflare 후보 | 판단 기준 |
|---|---|---|
| FastAPI | Workers | Python FastAPI 유지가 필요한지, JS/TS Worker로 API를 재작성해도 되는지 |
| ChromaDB | Vectorize | 벡터 인덱스를 Cloudflare 관리형으로 옮길지 |
| `data/raw` 문서 | R2 | 원본 PDF/MD/TXT를 오브젝트 스토리지에 둘지 |
| SQLite | D1 | 문서 메타데이터와 채팅 로그를 SQL로 관리할지 |
| Ollama LLM | Workers AI 또는 AI Gateway | 로컬 모델을 포기하거나 외부/Cloudflare 모델을 사용할 수 있는지 |
| 프론트 | Pages | 웹 UI를 정적 배포할지 |

## 도메인이 필요한 시점

도메인은 필수는 아니다. Quick Tunnel과 `*.trycloudflare.com`, Pages의 `*.pages.dev`, Workers의 `*.workers.dev`로 테스트할 수 있다.

다만 다음 단계부터는 도메인 또는 서브도메인이 있는 편이 좋다.

- 테스트 URL을 고정해야 한다.
- Flutter 앱이나 웹 프론트에 API base URL을 박아야 한다.
- Cloudflare Access, WAF, DNS, 인증서, 환경별 URL을 체계적으로 관리해야 한다.
- `api.example.com`, `app.example.com`, `staging.example.com` 같은 역할 분리가 필요하다.

## 최소 체크리스트

- [ ] 로컬 테스트 통과: `.venv/bin/python -m pytest`
- [ ] Ollama 모델 확인: `ollama list`
- [ ] 문서 색인 확인: `.venv/bin/python scripts/rebuild_index.py`
- [ ] 로컬 API 확인: `/health`, `/documents/stats`, `/chat`
- [ ] Quick Tunnel smoke test 완료
- [ ] Named Tunnel 전환 여부 결정
- [ ] CORS 허용 origin 축소
- [ ] `/documents/reindex` 보호 방식 결정
- [ ] 프론트 배포 방식 결정
- [ ] Cloudflare-native 이전 여부는 별도 결정 기록으로 남김

## 커밋하면 안 되는 것

- `.env`
- Cloudflare API token
- Tunnel credentials JSON
- `.cloudflared/` 내부 파일
- `data/vector_store/` ChromaDB 파일
- `data/app.sqlite3`
- 로컬 로그와 테스트 출력물

