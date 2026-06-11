# 원본 앱 기준 문서

이 문서는 `docs/original_first_tutorial_plan.md`의 1단계 산출물이다. `<original_app_root>`는 기존 `chatbot_rag` 프로젝트 루트를 뜻한다.

## 원본 앱 파일 맵

원본 앱에서 새 `project_template`로 재현해야 하는 기준 파일은 다음과 같다.

```text
<original_app_root>/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ deps.py
│  │  └─ routes/
│  │     ├─ chat.py
│  │     ├─ documents.py
│  │     ├─ health.py
│  │     └─ tourism.py
│  ├─ core/
│  │  ├─ config.py
│  │  └─ logging.py
│  ├─ repositories/
│  ├─ schemas/
│  ├─ services/
│  └─ utils/
├─ frontend/
│  └─ web/
│     ├─ index.html
│     ├─ app.js
│     ├─ styles.css
│     └─ option_flow_builder.js
├─ data/
│  ├─ eval/
│  ├─ processed/
│  │  ├─ tour_area_codes.json
│  │  └─ tourapi_bigdata_region_codes.json
│  └─ raw/
│     └─ example_faq.md
├─ prompts/
├─ scripts/
├─ tests/
├─ requirements.txt
├─ docker-compose.yml
├─ run_tourism_debug_tunnel.sh
└─ run_tourism_release_tunnel.sh
```

핵심 기준 파일의 역할은 다음이다.

| 원본 파일 | 역할 | `project_template` 위치 |
| --- | --- | --- |
| `app/main.py` | FastAPI 앱 생성, CORS, 라우터, `/tourism-ui/` 정적 파일 연결 | `project_template/app/main.py` |
| `app/api/deps.py` | RAG, TourAPI, 관광 상담 서비스 의존성 조립 | `project_template/app/api/deps.py` |
| `app/api/routes/health.py` | `/health` 상태 확인 | `project_template/app/api/routes/health.py` |
| `app/api/routes/chat.py` | `/chat` 일반 RAG 채팅 | `project_template/app/api/routes/chat.py` |
| `app/api/routes/tourism.py` | `/tourism/chat`, `/tourism/regions` | `project_template/app/api/routes/tourism.py` |
| `app/api/routes/documents.py` | 문서 조회 라우트 | `project_template/app/api/routes/documents.py` |
| `app/core/config.py` | 설정 로딩과 프로젝트 기준 경로 | `project_template/app/core/config.py` |
| `app/services/rag_service.py` | 검색 근거 기반 답변 생성 흐름 | `project_template/app/services/rag_service.py` |
| `app/services/tourism_chat_service.py` | 관광 상담 응답과 추천 카드 조립 | `project_template/app/services/tourism_chat_service.py` |
| `app/services/tourism_query_service.py` | 지역, 조건, 확장 의도 해석 | `project_template/app/services/tourism_query_service.py` |
| `frontend/web/index.html` | 실제 사용자용 무장애 관광 상담 화면 | `project_template/frontend/web/index.html` |
| `frontend/web/app.js` | 채팅, 선택형 조건, 추천 카드, 최신 결과 알림 | `project_template/frontend/web/app.js` |
| `frontend/web/styles.css` | 실제 사용자 화면 스타일 | `project_template/frontend/web/styles.css` |
| `frontend/web/option_flow_builder.js` | 선택형 조건을 자연어 질문으로 변환 | `project_template/frontend/web/option_flow_builder.js` |
| `data/processed/tour_area_codes.json` | 전국 광역 지역과 시군구 코드 | `project_template/data/processed/tour_area_codes.json` |
| `data/processed/tourapi_bigdata_region_codes.json` | TourAPI 빅데이터 지역 코드 | `project_template/data/processed/tourapi_bigdata_region_codes.json` |

## 복사 금지 대상

다음 항목은 재현 산출물이 아니라 실행 부산물 또는 개인 환경 자료다.

- `.env` 실제 비밀값
- 로컬 SQLite 데이터베이스
- Chroma 런타임 저장소
- `data/generated/` 실행 부산물
- `.venv`
- `__pycache__`
- 개인 환경 로그와 임시 파일
- `.DS_Store`

`project_template/data/generated/.gitkeep`와 `project_template/data/vector_store/.gitkeep`는 디렉터리 자리만 보존하기 위한 빈 파일이다. 실제 캐시, DB, 벡터 저장소 파일은 포함하지 않는다.

## 목표 구조 비교

| 범위 | 원본 기준 | 재현 산출물 |
| --- | --- | --- |
| 앱 진입점 | `app/main.py` | `project_template/app/main.py` |
| API 라우트 | `app/api/routes/*.py` | `project_template/app/api/routes/*.py` |
| 서비스 계층 | `app/services/*.py` | `project_template/app/services/*.py` |
| 요청/응답 스키마 | `app/schemas/*.py` | `project_template/app/schemas/*.py` |
| 저장소 계층 | `app/repositories/*.py` | `project_template/app/repositories/*.py` |
| 사용자 웹 화면 | `frontend/web/index.html` | `project_template/frontend/web/index.html` |
| 웹 동작 | `frontend/web/app.js`, `option_flow_builder.js` | `project_template/frontend/web/app.js`, `option_flow_builder.js` |
| 전국 지역 데이터 | `data/processed/tour_area_codes.json` | `project_template/data/processed/tour_area_codes.json` |
| 평가와 회귀 테스트 | `tests/*.py`, `data/eval/*.jsonl` | `project_template/tests/*.py`, `project_template/data/eval/*.jsonl` |
| 실행 스크립트 | `scripts/`, `run_tourism_*_tunnel.sh` | `project_template/scripts/`, `project_template/run_tourism_*_tunnel.sh` |

## 확인 기준

- `/health`는 `{"status": "ok"}`를 반환한다.
- `/tourism/regions`는 전국 17개 광역 지역과 시군구 목록을 반환한다.
- `서울 중구`, `부산 중구`, `인천 중구`처럼 같은 시군구 이름이 광역 단위로 구분된다.
- `강남구`, `해운대구`, `유성구`, `제주시` 같은 질문을 TourAPI 지역 코드로 해석할 데이터가 있다.
- `/tourism-ui/`는 실제 사용자용 무장애 관광 상담 화면이며 튜토리얼 설명 화면이 아니다.
