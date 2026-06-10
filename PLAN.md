# RAG/FastAPI Greenfield Tutorial Book Plan

## 목표

초급 개발자가 Codex, ChatGPT 같은 외부 LLM 없이 빈 폴더에서 시작해 로컬 RAG 챗봇과 FastAPI 웹 채팅 화면을 완성할 수 있는 튜토리얼북을 만든다.

최종 계획 범위는 다음을 포함한다.

- 새 프로젝트 구조 설계
- 독립 Python 가상환경 생성
- FastAPI 기초 서버
- 일반 문서 RAG 파이프라인
- ChromaDB 벡터 저장소
- Ollama 기반 로컬 임베딩/답변 모델 연결
- `/chat` API
- 관광 TourAPI 확장
- cache/fallback
- 지역명 처리
- 조건/선호 파싱
- 대화 세션
- intent classifier
- eval
- 정적 웹 UI
- 운영/디버깅
- 검증용 Jupyter Notebook
- Markdown 1차 정리
- Notion 최종 정리

## 핵심 결정

1. **Greenfield 우선**
   - 학습자는 기존 프로젝트를 clone해서 수정하지 않는다.
   - 모든 장은 "새 파일 만들기"와 "직접 코드 작성"으로 진행한다.

2. **기존 프로젝트는 참고 자료**
   - 기존 `chatbot_rag`의 구현은 설계 순서와 품질 기준을 정하는 근거로만 사용한다.
   - 본문에서는 기존 경로를 따라 하라고 지시하지 않는다.
   - 마지막 부록에서만 "현재 프로젝트에서는 같은 개념이 어디에 있는가"를 매핑한다.

3. **Python 환경 완전 분리**
   - 튜토리얼 예제 프로젝트는 자체 `.venv`를 가진다.
   - 기존 프로젝트의 `.venv`, DB, Chroma index, generated data를 사용하지 않는다.

4. **Notebook은 검증 산출물**
   - 노트북은 설명용 이미지가 아니라 실제 실행 검증 자료다.
   - 각 노트북은 실행 전제, 실행 명령, 성공 조건, 오류 대응을 포함한다.

5. **Notion은 최종 배포본**
   - Markdown과 노트북 검증이 끝난 뒤 Notion으로 정리한다.
   - Notion에는 전체 목차, 각 장 요약, 산출물 링크, 실행 체크리스트를 둔다.

## 권장 산출물 구조

```text
rag_fastapi_tutorial/
├─ PLAN.md
├─ README.md
├─ docs/
│  ├─ chapters/
│  │  ├─ 00_roadmap.md
│  │  ├─ 01_environment_setup.md
│  │  ├─ 02_fastapi_basics.md
│  │  ├─ 03_document_loading.md
│  │  ├─ 04_chunking_and_embeddings.md
│  │  ├─ 05_chroma_retrieval.md
│  │  ├─ 06_local_llm_answering.md
│  │  ├─ 07_chat_api.md
│  │  ├─ 08_tourapi_extension.md
│  │  ├─ 09_cache_and_fallback.md
│  │  ├─ 10_region_and_condition_parsing.md
│  │  ├─ 11_session_and_intent_classifier.md
│  │  ├─ 12_eval_pipeline.md
│  │  ├─ 13_web_ui.md
│  │  ├─ 14_operations_debugging.md
│  │  └─ 15_notion_finalization.md
│  └─ references/
│     ├─ glossary.md
│     ├─ common_errors.md
│     ├─ command_checklist.md
│     └─ production_project_mapping.md
├─ notebooks/
│  ├─ templates/
│  │  ├─ 01_environment_check.ipynb
│  │  ├─ 02_fastapi_health_check.ipynb
│  │  ├─ 03_document_loading_check.ipynb
│  │  ├─ 04_embedding_retrieval_check.ipynb
│  │  ├─ 05_chat_api_check.ipynb
│  │  ├─ 06_tourapi_cache_fallback_check.ipynb
│  │  ├─ 07_eval_report_check.ipynb
│  │  └─ 08_web_ui_smoke_check.ipynb
│  └─ executed/
├─ project_template/
├─ evidence/
└─ notion/
```

## 장별 작성 규칙

각 장은 같은 구조로 작성한다.

```text
1. 이번 장에서 만들 것
2. 왜 필요한가
3. 최종 폴더 상태
4. 새로 만들 파일
5. 코드 전체
6. 코드 흐름 설명
7. 실행 명령
8. 성공 기준
9. 검증 노트북
10. 자주 나는 오류와 해결
11. 다음 장으로 넘어가기 전 체크리스트
```

## 실행 단계

### Phase 1. 교재 뼈대 확정

- `README.md`와 `PLAN.md` 확정
- 장별 Markdown 파일 생성
- 노트북 템플릿 목록 확정
- Notion 최종 페이지 목차 초안 작성

완료 조건:

- 모든 장 파일이 존재한다.
- 각 장에 공통 섹션 헤더가 들어간다.
- 노트북 이름과 검증 목적이 확정된다.

### Phase 2. 독립 예제 프로젝트 설계

튜토리얼에서 학습자가 만들 최종 예제 프로젝트 구조를 정의한다.

```text
rag_fastapi_tutorial_app/
├─ app/
│  ├─ main.py
│  ├─ core/config.py
│  ├─ api/routes/
│  ├─ schemas/
│  ├─ services/
│  └─ utils/
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ vector_store/
├─ frontend/web/
├─ notebooks/
├─ scripts/
├─ tests/
├─ prompts/
├─ .env.example
├─ requirements.txt
└─ README.md
```

완료 조건:

- `project_template/`에 최종 예제 구조가 문서화된다.
- 기존 production repo 경로를 복사하지 않는다.

### Phase 3. FastAPI 기초 장 작성

- Python `.venv` 생성
- `requirements.txt` 작성
- `app/main.py` 작성
- `/health` 구현
- pytest로 health route 검증
- Notebook으로 HTTP health check 검증

완료 조건:

- 초급자가 빈 폴더에서 서버를 띄울 수 있다.
- 노트북이 200 OK를 확인한다.

### Phase 4. 일반 RAG 장 작성

- Markdown/TXT 문서 로더
- 텍스트 정제
- chunk 분할
- Ollama embedding 호출
- ChromaDB 저장/검색
- prompt builder
- local LLM answer client
- `/chat` API
- 출처 반환

완료 조건:

- 샘플 FAQ 문서를 넣고 질문에 답한다.
- 문서에 없는 질문은 모른다고 답한다.
- Notebook으로 retrieval 결과와 `/chat` 응답을 검증한다.

### Phase 5. 관광 확장 장 작성

- TourAPI 환경변수 설계
- 지역 코드 조회
- 관광 카드 schema
- cache/fallback Markdown 포맷
- 지역명 alias
- 접근성/가족 조건 파싱
- 조건/선호/제외 조건 처리

완료 조건:

- API 키가 없어도 fallback 샘플로 동작한다.
- API 키가 있으면 live 조회를 선택적으로 실행한다.
- Notebook이 cache/fallback 경로를 검증한다.

### Phase 6. 대화 세션과 intent classifier 장 작성

- `session_id` 설계
- 이전 지역/조건 기억
- `더 보기`, 조건 추가, 조건 교체, 조건 제외
- 간단한 rule-based intent classifier
- 선택적으로 scikit-learn 문자 n-gram classifier 소개

완료 조건:

- 멀티턴 예제가 같은 세션에서 동작한다.
- 맥락 없는 질문은 무리하게 추측하지 않는다.

### Phase 7. eval 장 작성

- JSONL 평가셋 포맷
- direct eval runner
- 실패 유형 분류
- regression checklist
- 결과 Markdown 리포트

완료 조건:

- 최소 20개 질문 평가셋을 실행한다.
- 실패/통과 요약 파일을 만든다.

### Phase 8. 웹 UI 장 작성

- 정적 HTML/CSS/JS
- `/chat` 호출
- 사용자 말풍선
- 답변 말풍선
- 출처 표시
- 관광 카드 표시
- 오류/로딩 상태

완료 조건:

- 브라우저에서 질문을 입력하고 답변을 본다.
- API 오류가 화면에 안전하게 표시된다.

### Phase 9. 운영/디버깅 장 작성

- `.env` 관리
- Ollama 모델 확인
- Chroma 재색인
- 로그 확인
- API timeout
- 노트북 실행 실패 대응
- 배포 전 체크리스트

완료 조건:

- 초급자가 가장 흔한 실패를 스스로 진단할 수 있다.

### Phase 10. Notion 최종 정리

- Markdown 장별 원고를 Notion용 목차로 재구성
- 코드 블록과 체크리스트 정리
- 노트북 산출물 링크 정리
- 최종 페이지 생성

완료 조건:

- Notion에 읽기 좋은 최종 튜토리얼북 페이지가 생성된다.
- 로컬 Markdown과 Notion의 목차가 일치한다.

## 검증 정책

각 장마다 최소 하나의 검증 수단을 둔다.

| 범위 | 검증 |
|---|---|
| 환경 | `.venv` Python, package import, Jupyter kernel 확인 |
| FastAPI | pytest + notebook HTTP request |
| RAG | retrieval unit check + `/chat` response |
| TourAPI | fallback-only test + optional live test |
| session | multi-turn test |
| eval | JSONL runner output |
| web UI | browser smoke scenario |
| Notion | created page URL and content fetch |

## Notion 정리 계획

추천 위치:

```text
Codex 정리함
└─ 프로젝트 기획·워크플로우
   └─ RAG FastAPI 튜토리얼북
```

Notion 페이지 구성:

```text
1. 튜토리얼북 목적
2. 대상 독자와 전제
3. 전체 로드맵
4. 장별 링크
5. 노트북 검증 산출물
6. 최종 예제 프로젝트 구조
7. 자주 나는 오류
8. 기존 production 프로젝트와의 개념 매핑
9. 다음 개선 후보
```

## 범위 밖

- 기존 production repo를 복사해 교재로 만드는 것
- 외부 LLM API 사용
- 로그인/결제/예약 기능
- 대규모 운영 배포
- 모바일 앱 구현
- 모델 fine-tuning 필수화

## 다음 즉시 작업

1. `docs/chapters/*.md` 뼈대 생성
2. `docs/references/*.md` 뼈대 생성
3. `notebooks/templates/*.ipynb` 빈 템플릿 생성
4. `project_template/README.md` 작성
5. Notion 최종 페이지 초안 `notion/rag_fastapi_tutorial_notion_draft.md` 작성
