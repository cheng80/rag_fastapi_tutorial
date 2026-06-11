# 원본형 RAG FastAPI 앱 만들기

이 튜토리얼은 샘플처럼 보이는 축소 앱이 아니라 원본 `chatbot_rag`와 같은 산출물을 만드는 절차를 설명한다. 설명은 문서에만 두고, `project_template`의 웹 화면과 API 응답은 실제 사용자용 관광 상담 앱으로 유지한다.

## 1장. 원본 기준 고정

### 왜 필요한가

무엇을 만들지 먼저 고정하지 않으면 튜토리얼 편의를 이유로 구조와 화면이 원본에서 멀어진다. 이 장의 목표는 원본의 파일, 제외 대상, 비교 기준을 먼저 잠그는 것이다.

### 만들 파일

- `docs/original_app_reference.md`
- `project_template/README.md`

### 코드 흐름

1. 원본의 `app/main.py`에서 라우터와 정적 UI 연결을 확인한다.
2. `app/api/deps.py`에서 서비스 의존성 조립 순서를 확인한다.
3. `frontend/web`의 네 파일을 사용자 화면 기준으로 묶는다.
4. `data/processed/tour_area_codes.json`과 `tourapi_bigdata_region_codes.json`을 전국 지역 데이터 기준으로 둔다.

### 실행 명령

```bash
python3 scripts/validate_tutorial_docs.py --check original-map
```

### 확인 기준

- 원본 앱 파일 맵이 문서화되어 있다.
- 복사 금지 대상이 문서에 있다.
- `project_template` 목표 구조가 원본 구조와 비교 가능하다.

### 자주 나는 오류

- `.env`나 로컬 DB를 산출물에 넣는다.
- 일부 샘플 지역만 넣고 전국 지원처럼 설명한다.
- 웹 화면을 튜토리얼 설명 화면으로 바꾼다.

## 2장. 원본 구조 이식

### 왜 필요한가

초급자에게 설명하기 쉽다는 이유로 구조를 줄이면 원본형 앱을 다시 만들 수 없다. 설명은 문서가 담당하고 산출물은 원본 구조를 따른다.

### 만들 파일

- `project_template/app/main.py`
- `project_template/app/api/deps.py`
- `project_template/app/api/routes/*.py`
- `project_template/app/core/*.py`
- `project_template/app/services/*.py`
- `project_template/frontend/web/index.html`
- `project_template/frontend/web/app.js`
- `project_template/frontend/web/styles.css`
- `project_template/frontend/web/option_flow_builder.js`
- `project_template/data/processed/tour_area_codes.json`

### 코드 흐름

1. `create_app()`이 FastAPI 앱을 만든다.
2. CORS 설정을 붙인다.
3. health, chat, tourism, documents 라우터를 등록한다.
4. `frontend/web`을 `/tourism-ui/`에 정적 파일로 연결한다.
5. `/tourism/regions`가 지역 코드 JSON을 읽어 광역 지역과 시군구를 반환한다.

### 실행 명령

```bash
cd project_template
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/tourism/regions
```

### 확인 기준

- `/health`가 200으로 응답한다.
- `/tourism/regions`가 17개 광역 지역을 반환한다.
- `/tourism-ui/`가 사용자용 관광 상담 화면을 연다.

### 자주 나는 오류

- `PROJECT_ROOT` 기준이 원본 루트를 가리킨 채 남아 있다.
- `frontend/web` 파일은 있지만 `/tourism-ui/` mount가 빠져 있다.
- 전국 지역 데이터 대신 테스트용 몇 개 지역만 복사한다.

## 3장. 핵심 기능 재현

### 왜 필요한가

라우터만 있으면 앱처럼 보이지만 사용자는 관광 상담 흐름을 쓴다. RAG 검색, TourAPI 조회, 카드 변환, 출처 표시가 연결되어야 원본형 결과가 된다.

### 만들 파일

- `project_template/app/services/rag_service.py`
- `project_template/app/services/retriever.py`
- `project_template/app/services/vector_store.py`
- `project_template/app/services/tour_api_service.py`
- `project_template/app/services/tourism_chat_service.py`
- `project_template/app/services/tourism_query_service.py`
- `project_template/app/services/tourism_card_codec.py`
- `project_template/app/schemas/tourism.py`

### 코드 흐름

1. 사용자가 `/tourism/chat`으로 질문을 보낸다.
2. `TourismQueryService`가 지역, 조건, 확장 의도를 해석한다.
3. `TourAPIService`가 준비된 자료, 캐시, live 조회 흐름을 담당한다.
4. `TourismChatService`가 검색 근거와 추천 카드를 묶는다.
5. 응답은 사용자에게 필요한 문장, 카드, 출처를 반환한다.

### 실행 명령

```bash
cd project_template
python -m pytest tests/test_tourism_api.py tests/test_tourism_option_flow_ui.py -q
```

### 확인 기준

- 빈 메시지는 400으로 거절된다.
- 추천 카드는 원본 웹 화면에서 깨지지 않는 필드를 가진다.
- 사용자 표시 문구에 내부 구현 용어가 섞이지 않는다.

### 자주 나는 오류

- 예외 메시지에 내부 경로나 구현 상세가 그대로 노출된다.
- `top_k` 같은 검색 파라미터를 사용자 문장에 넣는다.
- 선택형 조건 UI가 만든 질문과 백엔드 조건 해석이 어긋난다.

## 4장. 검증 체계 작성

### 왜 필요한가

원본형 앱은 파일 구조, API, RAG, 관광 상담, UI가 함께 맞아야 한다. 단위 테스트만으로는 사용자 화면과 HTTP 표면을 보장할 수 없다.

### 만들 파일

- `tests/test_project_template_parity.py`
- `tests/test_tutorial_docs.py`
- `scripts/validate_tutorial_docs.py`
- `project_template/tests/*.py`

### 코드 흐름

1. 루트 테스트가 `project_template`의 표면을 검증한다.
2. `project_template/tests`가 원본 앱의 회귀 테스트 흐름을 보존한다.
3. 문서 validator가 기준 문서와 튜토리얼 장 구성을 검사한다.
4. 실제 QA는 HTTP, 브라우저, tmux 중 하나로 사용자 표면을 직접 실행한다.

### 실행 명령

```bash
python -m pytest tests/test_project_template_parity.py tests/test_tutorial_docs.py -q
cd project_template
python -m pytest tests/test_tourism_api.py tests/test_tourism_option_flow_ui.py -q
```

### 확인 기준

- 구조 차이를 테스트가 잡는다.
- 일부 지역만 들어간 지역 데이터는 실패한다.
- 사용자 화면에 튜토리얼 문구가 보이면 실패한다.
- 실제 HTTP와 브라우저 QA 증거가 남는다.

### 자주 나는 오류

- 테스트만 통과시키고 실제 `/tourism-ui/`를 열어 보지 않는다.
- 검증 스크립트가 문서만 보고 산출물을 확인하지 않는다.
- QA 뒤에 pycache, DB, 로그 같은 실행 부산물을 남긴다.

## 5장. 튜토리얼 문서 운영

### 왜 필요한가

튜토리얼은 산출물 화면이 아니라 설명 문서다. 산출물이 사용자용 앱으로 남아야 실제 프로젝트 템플릿으로 쓸 수 있다.

### 만들 파일

- `docs/tutorial_build_original_app.md`
- `docs/original_app_reference.md`
- `project_template/frontend/web/README.md`

### 코드 흐름

1. 각 장은 같은 형식으로 학습 흐름을 제공한다.
2. 어려운 용어는 한국어 설명을 붙인다.
3. 실행 명령과 확인 기준은 바로 따라 할 수 있게 둔다.
4. 웹 화면과 API 응답에는 튜토리얼 설명을 넣지 않는다.

### 실행 명령

```bash
python3 scripts/validate_tutorial_docs.py --check tutorial-chapters
python3 scripts/validate_tutorial_docs.py --check no-ui-tutorial-leak
```

### 확인 기준

- 모든 장에 `왜 필요한가`, `만들 파일`, `코드 흐름`, `실행 명령`, `확인 기준`, `자주 나는 오류`가 있다.
- 문서는 진행 상황 보고서가 아니라 따라 할 수 있는 교재다.
- 사용자 화면은 무장애 관광 상담 앱으로 남아 있다.

### 자주 나는 오류

- 문서에만 있어야 할 튜토리얼 표현을 버튼이나 API 응답에 넣는다.
- 내부 진단 정보를 사용자 문장처럼 표시한다.
- 원본 구조가 바뀌었는데 기준 문서를 갱신하지 않는다.
