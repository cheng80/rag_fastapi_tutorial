# Cloudflare RAG 배포 구현 계획

> **에이전트 작업자 필수 안내:** 이 계획을 작업 단위로 실행할 때는 `superpowers:subagent-driven-development`를 권장하며, 대안으로 `superpowers:executing-plans`를 사용한다. 각 단계는 체크박스(`- [ ]`)로 진행 상태를 추적한다.

**목표:** 현재 로컬 FastAPI + ChromaDB + Ollama 기반 RAG 챗봇을 임시 Quick Tunnel 테스트 상태에서 재현 가능한 Cloudflare 기반 테스트/스테이징 배포 흐름으로 옮긴다.

**아키텍처:** 프로젝트가 아직 Ollama 기반인 동안에는 Python RAG 백엔드를 로컬에 유지하고, Cloudflare Tunnel을 통해 외부 테스트용으로 노출한다. 배포는 단계별로 진행한다. 먼저 로컬 서비스를 안정화하고, Quick Tunnel을 Named Tunnel로 바꾸고, 접근 제어와 관측성을 추가한 뒤, 백엔드 origin을 계속 로컬에 둘지 또는 Cloudflare Workers, Vectorize, R2, D1, Workers AI, AI Gateway로 일부 기능을 이전할지 결정한다.

**기술 스택:** FastAPI, ChromaDB, SQLite, Ollama, cloudflared, Cloudflare Tunnel, 선택 사항으로 Cloudflare Access, Cloudflare Pages, Workers/Vectorize/R2/D1/Workers AI.

---

## 파일 구조

- 생성: `docs/cloudflare_rag_deployment_guide.md`
  - 현재 상태, 목표 단계, 터널 선택지, 점검 항목, 다음 단계로 넘어가는 기준을 설명한다.
- 생성: `docs/cloudflare_rag_reference_docs.md`
  - 이후 작업에 필요한 Cloudflare 공식 문서와 로컬 프로젝트 문서 링크를 모은다.
- 수정: `README.md`
  - Cloudflare 배포 문서를 프로젝트 문서 목록에 추가한다.
- 추후 선택 생성: `deploy/cloudflare/README.md`
  - tunnel config, system service 설정, Wrangler 설정을 repo에 남겨야 할 때만 만든다.
- 추후 선택 생성: `deploy/cloudflare/config.example.yml`
  - secret이나 tunnel credentials를 제외한 Named Tunnel ingress 예시를 둔다.

## 현재 전제

- FastAPI API 서버는 현재 로컬 `http://localhost:8000`에서 실행된다.
- Ollama는 로컬 `http://localhost:11434`에서 실행된다.
- ChromaDB는 `data/vector_store/chroma` 아래의 로컬 파일 기반이다.
- SQLite는 `data/app.sqlite3` 파일 기반이다.
- 외부 테스트는 현재 Cloudflare Quick Tunnel을 사용한다.
- 현재 테스트 단계에서는 커스텀 도메인이 필수는 아니지만, 더 넓은 사용자 테스트나 스테이징 전에는 도메인 사용을 권장한다.

## 0단계: 현재 로컬 앱 기준선 확인

**파일:**
- 읽기: `README.md`
- 읽기: `docs/rag_chatbot_design.md`
- 읽기: `.env.example`
- 읽기: `app/core/config.py`
- 읽기: `app/main.py`

- [ ] **1단계: git 상태와 Python 환경 확인**

실행:

```bash
cd project root
git status --short
.venv/bin/python --version
```

기대 결과:

```text
git status는 깨끗하거나 의도된 로컬 변경 사항만 보여야 한다.
Python은 프로젝트의 .venv 인터프리터여야 한다.
```

- [ ] **2단계: 기존 테스트 실행**

실행:

```bash
cd project root
.venv/bin/python -m pytest
```

기대 결과:

```text
배포 관련 변경을 시작하기 전에 모든 테스트가 통과해야 한다.
```

- [ ] **3단계: Ollama 모델 확인**

실행:

```bash
ollama list
```

기대 결과:

```text
bge-m3가 임베딩 모델로 준비되어 있다.
hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL가 답변 모델로 준비되어 있다.
비교 테스트가 필요하면 gemma3:4b-it-q4_K_M도 준비되어 있다.
```

- [ ] **4단계: 문서가 바뀌었으면 로컬 벡터 인덱스 재생성**

실행:

```bash
cd project root
.venv/bin/python scripts/rebuild_index.py
```

기대 결과:

```text
data/raw의 문서를 기준으로 Chroma collection이 재생성되고, 임베딩 차원 오류가 없어야 한다.
```

- [ ] **5단계: API 서버 로컬 실행**

실행:

```bash
cd project root
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

기대 결과:

```text
Uvicorn이 http://127.0.0.1:8000 에서 시작된다.
```

- [ ] **6단계: 로컬에서 공개 API 동작 확인**

실행:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/documents/stats
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"환불은 언제까지 가능한가요?"}'
```

기대 결과:

```text
/health는 정상 상태 응답을 반환한다.
/documents/stats는 collection 통계를 반환한다.
/chat은 answer와 sources 필드를 반환한다.
```

## 1단계: Quick Tunnel은 짧은 테스트에만 사용

**파일:**
- 필요 시 추후 수정: `docs/cloudflare_rag_deployment_guide.md`

- [ ] **1단계: 임시 Quick Tunnel 시작**

API 서버가 실행 중인 상태에서 두 번째 터미널에서 실행:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

기대 결과:

```text
cloudflared가 임시 trycloudflare.com URL을 출력한다.
```

- [ ] **2단계: 임시 URL을 통해 smoke test 실행**

`<QUICK_TUNNEL_URL>`을 `cloudflared`가 출력한 URL로 바꾼다.

실행:

```bash
curl <QUICK_TUNNEL_URL>/health
curl -X POST <QUICK_TUNNEL_URL>/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"환불은 언제까지 가능한가요?"}'
```

기대 결과:

```text
로컬과 같은 health 및 chat 동작이 tunnel을 통해서도 동작한다.
```

- [ ] **3단계: Quick Tunnel 제한 사항 기록**

배포 가이드에 날짜가 포함된 기록을 추가한다.

```markdown
## Quick Tunnel 테스트 로그

- 날짜: 2026-05-20
- 로컬 origin: `http://127.0.0.1:8000`
- 터널 유형: Quick Tunnel
- 결과: health 및 chat endpoint 접근 가능
- 제한: URL이 임시이므로 안정적인 staging endpoint로 사용하지 않는다.
```

## 2단계: Quick Tunnel을 Named Tunnel로 교체

**파일:**
- 추후 선택 생성: `deploy/cloudflare/README.md`
- 추후 선택 생성: `deploy/cloudflare/config.example.yml`

- [ ] **1단계: Named Tunnel 생성**

실행:

```bash
cloudflared tunnel login
cloudflared tunnel create chatbot-rag-test
```

기대 결과:

```text
Cloudflare에 chatbot-rag-test라는 지속 가능한 tunnel이 생성된다.
Tunnel credentials는 로컬에 생성되며 절대 커밋하지 않는다.
```

- [ ] **2단계: hostname 전략 선택**

다음 기준으로 결정한다.

```text
사용 가능한 도메인이 없으면 Quick Tunnel은 임시 데모용으로만 유지한다.
도메인 또는 서브도메인이 있으면 Named Tunnel을 api.<domain>에 연결한다.
프론트엔드가 나중에 추가되면 app.<domain> 또는 Cloudflare Pages의 *.pages.dev URL을 UI에 사용한다.
```

- [ ] **3단계: Named Tunnel을 hostname에 연결**

실제 hostname을 정한 뒤에만 실행:

```bash
cloudflared tunnel route dns chatbot-rag-test api.example.com
```

기대 결과:

```text
api.example.com이 Named Tunnel로 라우팅된다.
```

- [ ] **4단계: 커밋되지 않는 로컬 tunnel config 작성**

로컬 config 예시:

```yaml
tunnel: chatbot-rag-test
credentials-file: ~/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

기대 결과:

```text
실제 credentials 파일은 repository 밖에 남아 있어야 한다.
```

- [ ] **5단계: Named Tunnel 실행**

실행:

```bash
cloudflared tunnel --config ~/.cloudflared/chatbot-rag-test.yml run chatbot-rag-test
```

기대 결과:

```text
api.example.com이 로컬 FastAPI origin에 도달한다.
```

## 3단계: 기본 보안 제어 추가

**파일:**
- 로컬에서만 수정: `.env`
- 필요 시 추후 수정: `app/core/config.py`
- CORS 동작이 바뀌면 추후 테스트: `tests/`

- [ ] **1단계: 로컬 외부 테스트용 CORS 범위 축소**

로컬 `.env`에 설정:

```env
ENVIRONMENT=test
CORS_ORIGINS=https://app.example.com,http://localhost:3000,http://localhost:5173
```

기대 결과:

```text
API가 wildcard origin 대신 예상된 프론트엔드 origin만 허용한다.
```

- [ ] **2단계: 사람이 브라우저로 접근하는 테스트 endpoint를 Cloudflare Access 뒤에 둔다**

Cloudflare dashboard에서 테스트 hostname용 Access 애플리케이션을 설정한다.

```text
Application: api.example.com
Policy: 선택한 이메일 주소 또는 identity provider group만 허용
```

기대 결과:

```text
승인된 테스터만 브라우저에서 tunnel hostname에 접근할 수 있다.
```

- [ ] **3단계: API 클라이언트에 service token이 필요한지 결정**

다음 기준을 사용한다.

```text
브라우저 기반 수동 테스트만 한다면 Cloudflare Access 로그인을 사용할 수 있다.
프로그램 방식의 클라이언트는 Access service token 또는 프로젝트 자체 API 인증 계층을 사용한다.
/documents/reindex는 인증 없이 공개하지 않는다.
```

## 4단계: 배포 관측성 추가

**파일:**
- 필요 시 추후 수정: `app/core/logging.py`
- 필요 시 추후 수정: `app/api/routes/health.py`

- [ ] **1단계: 최소 health check 정의**

health endpoint는 다음을 확인해야 한다.

```text
FastAPI process가 실행 중이다.
Ollama에 접근할 수 있다.
Chroma collection을 열 수 있다.
선택 사항: 테스트용 seed data 기준 document count가 0보다 크다.
```

- [ ] **2단계: endpoint 단위 smoke test 명령을 가이드에 추가**

사용:

```bash
curl https://api.example.com/health
curl https://api.example.com/documents/stats
curl -X POST https://api.example.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"대표적인 관광 안내 질문을 하나 넣는다"}'
```

기대 결과:

```text
tunnel 또는 앱 재시작 후 매번 smoke check를 실행할 수 있다.
```

- [ ] **3단계: Cloudflare dashboard 신호 확인**

확인 항목:

```text
Tunnel connector 상태
HTTP request volume
4xx 및 5xx 응답
Access가 켜져 있다면 Access login 실패
```

## 5단계: Cloudflare 이전 깊이 결정

**파일:**
- 추후 수정: `docs/cloudflare_rag_deployment_guide.md`
- 추후 선택 코드: 새 Cloudflare Worker 프로젝트

- [ ] **1단계: 로컬 Ollama가 필수라면 local-origin 아키텍처 유지**

다음 상황에서 이 방식을 사용한다.

```text
답변 모델을 반드시 로컬 Ollama 모델로 유지해야 한다.
Vector store가 로컬 디스크의 ChromaDB로 남아 있다.
서비스 목적이 제한된 테스트 또는 내부 데모다.
```

- [ ] **2단계: 요구사항이 안정된 뒤 Cloudflare-native RAG 검토**

후보 매핑:

```text
FastAPI API gateway -> Cloudflare Workers
ChromaDB vector store -> Vectorize
PDF/Markdown 원본 문서 -> R2
SQLite metadata -> D1
Ollama embeddings 또는 answers -> Workers AI, AI Gateway, 또는 외부 provider
Frontend -> Cloudflare Pages
```

기대 결과:

```text
로컬 모델과 검색 품질을 아직 검증하는 동안에는 성급한 이전을 피한다.
```

- [ ] **3단계: 구현 전에 migration decision record 작성**

포함 항목:

```text
무엇을 로컬에 남길지
무엇을 Cloudflare로 옮길지
어떤 model provider를 사용할지
문서 ingestion을 어떻게 실행할지
인증을 어떻게 처리할지
비용과 limit을 어떻게 확인할지
```

## 검증

- [ ] `git diff -- docs README.md`가 이번 계획 작업의 문서 변경만 보여준다.
- [ ] 이후 코드 변경을 ship하기 전 `.venv/bin/python -m pytest`가 통과한다.
- [ ] tunnel 테스트 전에 로컬 `/health`, `/documents/stats`, `/chat`이 동작한다.
- [ ] 공개 테스트 URL을 통해 tunnel `/health`와 `/chat`이 동작한다.
- [ ] tunnel credentials, API token, `.env`, Chroma 파일, SQLite 파일, 로컬 로그를 커밋하지 않는다.

## 커밋 계획

문서 변경은 별도 커밋으로 남긴다.

```bash
git add README.md docs/cloudflare_rag_deployment_guide.md docs/cloudflare_rag_reference_docs.md docs/superpowers/plans/2026-05-20-cloudflare-rag-deployment.md
git commit -m "docs: add Cloudflare RAG deployment plan"
```

이후 구현 변경은 별도 커밋으로 분리한다.

```bash
git add app tests
git commit -m "feat: harden deployment health checks"
```

```bash
git add deploy/cloudflare docs
git commit -m "docs: add named tunnel runbook"
```
