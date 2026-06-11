# Cloudflare RAG Reference Docs

이 문서는 현재 RAG 챗봇을 Cloudflare로 테스트/배포할 때 확인할 문서 목록이다.

## 이 저장소 문서

- `README.md`: 로컬 실행, 모델 준비, 문서 색인, API 테스트 순서
- `docs/rag_chatbot_design.md`: RAG 구조와 현재 FastAPI/Chroma/Ollama 설계
- `docs/next_session_prompt.md`: 다음 작업 세션 시작 순서와 로컬 Python 환경 메모
- `docs/cloudflare_rag_deployment_guide.md`: Cloudflare Quick Tunnel에서 Named Tunnel 및 스테이징으로 가는 실행 가이드
- `docs/superpowers/plans/2026-05-20-cloudflare-rag-deployment.md`: 작업 체크리스트형 구현 계획

## Cloudflare 공식 문서

- [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/): 로컬 또는 사설 origin을 Cloudflare 네트워크에 outbound-only 방식으로 연결한다.
- [Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/): 계정이나 도메인 없이 임시 테스트 URL을 만드는 방식이다.
- [Tunnel setup](https://developers.cloudflare.com/tunnel/setup/): named tunnel 생성, 실행, Docker 실행 방식을 확인한다.
- [Tunnel routing](https://developers.cloudflare.com/tunnel/routing/): tunnel을 DNS hostname에 연결하는 방법을 확인한다.
- [Cloudflare Pages custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/): 웹 프론트를 Pages에 올릴 때 커스텀 도메인을 연결하는 방법이다.
- [Cloudflare Workers custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains): Worker API를 도메인에 연결할 때 확인한다.
- [Workers AI](https://developers.cloudflare.com/workers-ai/): 로컬 Ollama 대신 Cloudflare의 serverless GPU 모델을 쓸 수 있는지 검토할 때 본다.
- [Workers AI bindings](https://developers.cloudflare.com/workers-ai/configuration/bindings/): Worker 안에서 `env.AI`로 Workers AI를 호출하는 설정이다.
- [Vectorize](https://developers.cloudflare.com/vectorize/): ChromaDB를 Cloudflare의 관리형 vector database로 옮길지 검토할 때 본다.
- [Vectorize and Workers AI embeddings](https://developers.cloudflare.com/vectorize/get-started/embeddings/): Workers AI로 임베딩을 만들고 Vectorize에 저장하는 흐름이다.
- [AI Gateway](https://developers.cloudflare.com/ai-gateway/): LLM 호출의 관측, 캐싱, rate limiting, fallback을 관리할 때 검토한다.
- [AI Gateway caching](https://developers.cloudflare.com/ai-gateway/configuration/caching/): 동일 요청 캐싱이 유효한 챗봇 시나리오인지 검토할 때 본다.

## 현재 프로젝트에 중요한 판단 포인트

### 1. 로컬 Ollama를 유지할 것인가

로컬 모델을 유지하면 Cloudflare는 당분간 "안전한 입구" 역할을 한다. 이 경우 Workers AI나 Vectorize 이전보다 Tunnel, Access, CORS, health check가 먼저다.

### 2. 벡터 DB를 옮길 것인가

현재 ChromaDB는 로컬 파일 기반이다. 여러 서버나 Cloudflare-native 구조로 가려면 Vectorize, R2, D1 조합을 검토한다.

### 3. API를 FastAPI로 유지할 것인가

FastAPI를 유지하면 tunnel origin 방식이 자연스럽다. Workers로 옮기면 API를 JavaScript/TypeScript 중심으로 재작성해야 하므로, RAG 품질과 API 계약이 안정된 뒤 결정하는 편이 낫다.

### 4. 공개 테스트 범위가 어디까지인가

소수 내부 테스트라면 Quick Tunnel이나 Named Tunnel + Access면 충분하다. 외부 사용자 테스트라면 고정 도메인, 인증, 로그, 장애 대응, 비용 추적이 필요하다.

## 추천 읽기 순서

1. `docs/cloudflare_rag_deployment_guide.md`
2. Cloudflare Tunnel 공식 문서
3. Quick Tunnels 공식 문서
4. Tunnel setup/routing 공식 문서
5. 프론트가 생기면 Pages custom domains 공식 문서
6. Cloudflare-native 이전을 검토할 때 Workers AI, Vectorize, AI Gateway 문서

