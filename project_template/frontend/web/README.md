# Web Frontend

`/tourism/chat` 백엔드 응답을 눈으로 확인하기 위한 메신저형 정적 웹 UI다.
빌드 도구 없이 HTML/CSS/JS만 사용한다.

현재 화면은 발표 시연을 위해 카카오톡 같은 친숙한 채팅창 구조를 참고하되, 특정 서비스 로고나 브랜드 자산은 쓰지 않는다. 디자인 기준은 `docs/design/tourism_chatbot_DESIGN.md`에 둔다.

## 화면 구성

- 앱형 노란 채팅 헤더와 상담 대화 영역
- 방문 전 확인 필요 공지 말풍선
- 사용자 질문 말풍선, 챗봇 답변 말풍선, 타이핑 인디케이터
- 접어서 여는 지역·예시 선택 버튼
- 채팅형/선택형 입력 전환
- 자유 질문 입력창과 `추천 받기` 버튼
- 광역 지역을 먼저 고르고 해당 시군구를 이어서 고르는 선택형 조건 builder
- 동행 상황, 접근성 조건, 선호/제외, 지역 확장 선택
- 선택형에서는 채팅형 지역·예시 drawer를 숨기고, 선택 조건 패널을 접거나 펼칠 수 있음
- 선택형에서 만들어진 질문 문장은 입력창에서 직접 수정하거나 조건을 덧붙일 수 있음
- 짧게 접힌 답변 말풍선과 `전체 보기`/`접기`
- 추천 관광지 카드, `더 보기`, 출처 표시
- 카드별 조건 근거를 하나의 `라벨 + 설명` 행으로 통일 표시
- 입력/전송/오류/카드 수 확인용 토스트 피드백
- 저장된 후보가 5장 미만일 때 표시되는 `최신 정보 더 찾기` 후속 버튼
- 카드별 `상세 정보` 펼침과 `지도 검색`

한국관광공사 열린관광 사이트의 상세 URL은 현재 콘텐츠 ID만으로 안정적인 공개 상세 링크를 만들 수 없어, 잘못된 `access.visitkorea.or.kr/detail/...` 링크는 노출하지 않는다. 대신 카드 내부 상세 정보와 장소명/주소 기반 지도 검색을 제공한다.

## 실행

서버류 실행 원칙:

- `uvicorn`, `cloudflared`, `python3 -m http.server` 같은 장시간 실행 프로세스는 Codex 백그라운드 세션으로 조용히 띄우지 않는다.
- VS Code/Cursor 등 에디터 내장 터미널의 새 터미널을 열고 사용자가 로그와 종료 상태를 볼 수 있게 실행한다. 외부 터미널 앱이 아니라 에디터 안에서 보이는 터미널을 기준으로 한다.
- 터미널은 FastAPI용, 터널용처럼 역할별로 분리한다.

권장 실행:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

TourAPI live 조회를 명시적으로 켠 개발 모드에서 로그까지 남기고 싶을 때:

```bash
mkdir -p data/generated/logs
TOURISM_LIVE_LOOKUP_ENABLED=true .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload 2>&1 | tee data/generated/logs/chatbot_rag_uvicorn.log
```

- `TOURISM_LIVE_LOOKUP_ENABLED=true`: live TourAPI 조회를 명시적으로 켠다. 기본값도 `true`지만, 이전 터미널 환경값이 남아 있을 수 있으면 명시한다.
- `--reload`: 코드 변경 시 개발 서버를 자동 재시작한다.
- `2>&1`: 에러 로그와 일반 로그를 같은 출력 흐름으로 합친다.
- `| tee data/generated/logs/chatbot_rag_uvicorn.log`: 터미널에 로그를 보이면서 동시에 실행 산출물 로그 파일에도 저장한다.

브라우저에서 `http://127.0.0.1:8000/tourism-ui/`를 연다.

FastAPI가 `frontend/web`을 `/tourism-ui/`로 같이 서빙하므로 외부 터널링도 8000번 포트 하나만 열면 된다.
기본 화면은 개발 모드다. 상단 `DBG` 패널에 API 주소, Swagger 문서(`/docs`), ReDoc(`/redoc`), OpenAPI JSON(`/openapi.json`) 바로가기와 응답 경로 상태가 보인다.

릴리즈형 사용자 화면은 URL에 `?mode=release` 또는 `?debug=0`을 붙여 연다.

```text
http://127.0.0.1:8000/tourism-ui/?mode=release
```

릴리즈형 화면에서는 API 주소, 문서 링크, live/cache/fallback 같은 내부 진단 문구, `DBG` 버튼, 개발 모드 배지가 보이지 않는다. 사용자에게는 접힌 지역·예시 선택, 질문 말풍선, 타이핑 표시, 답변, 추천 카드, 출처, 방문 전 확인 문구만 보인다. 초기 예시 카드는 개발 모드에서만 보여주고, 릴리즈형 화면은 빈 상담 상태에서 시작한다.

정적 파일 서버로 따로 확인하고 싶을 때:

```bash
cd frontend/web
python3 -m http.server 5173
```

브라우저에서 `http://127.0.0.1:5173`을 연다.

로컬 정적 서버에서 열면 기본 API 주소는 `http://127.0.0.1:8000`이다. `/tourism-ui/`나 터널 URL에서 열면 현재 origin을 API 주소로 자동 사용한다. 서버 포트를 바꿨다면 화면 상단의 API 입력값만 수정한다.

## 외부 임시 확인

프로젝트 루트에서 아래 스크립트 중 하나를 실행한다.

```bash
./run_tourism_debug_tunnel.sh
./run_tourism_release_tunnel.sh
```

- debug 스크립트는 FastAPI를 `--reload`로 실행하고 `/tourism-ui/` 개발 화면을 연다.
- release 스크립트는 reload 없이 실행하고 `/tourism-ui/?mode=release` 사용자 화면을 연다.
- 8000번 FastAPI가 이미 `/health`에 응답하면 새 서버를 띄우지 않고 기존 서버를 재사용한다.
- 이전 스크립트가 만든 Quick Tunnel 주소가 아직 살아 있으면 새 터널을 만들지 않고 그 주소를 연다.
- 새 터널을 만든 경우 `data/generated/tour_api/tunnel_logs/*_public_url.txt`에 public base URL을 저장한다.

수동으로 나눠 실행하고 싶으면 FastAPI와 Cloudflare를 서로 다른 터미널에서 실행한다.

터미널 1: FastAPI 서버

```bash
mkdir -p data/generated/logs
TOURISM_LIVE_LOOKUP_ENABLED=true .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload 2>&1 | tee data/generated/logs/chatbot_rag_uvicorn.log
```

TourAPI 호출을 더 쓰지 않을 때만 fallback-only로 실행한다.

```bash
mkdir -p data/generated/logs
TOURISM_LIVE_LOOKUP_ENABLED=false .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload 2>&1 | tee data/generated/logs/chatbot_rag_uvicorn.log
```

터미널 2: Cloudflare Quick Tunnel

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

출력되는 `https://...trycloudflare.com` 주소 뒤에 `/tourism-ui/`를 붙여 외부에서 연다.

```text
https://...trycloudflare.com/tourism-ui/
```

Quick Tunnel은 임시 확인용이다. 시연이 끝나면 `cloudflared`와 `uvicorn`을 종료한다.

## 확인할 것

- 강남구 휠체어 추천이 카드로 보이는지 확인한다.
- 질문 전송 시 사용자 질문 말풍선이 오른쪽에 표시되고, 응답 대기 중 타이핑 인디케이터가 보이는지 확인한다.
- 질문 전송 즉시 이전 답변과 카드가 비워지고, 결과 영역 상단에서 로딩 상태가 보이는지 확인한다.
- 응답 카드가 많아도 렌더 완료 후 스크롤이 맨 아래로 이동하지 않고 첫 답변과 첫 카드부터 읽을 수 있는지 확인한다.
- 빠른 질문/지역 선택/빈 입력/오류/카드 반환에서 토스트 피드백이 구분되는지 확인한다.
- 추천 카드 위 답변이 짧게 접히고, 길 때만 `전체 보기`가 보이는지 확인한다.
- 준비된 후보가 5장 미만이고 추가 확인이 가능할 때 `최신 정보 더 찾기` 후속 버튼이 보이는지 확인한다.
- `최신 정보 더 찾기`를 누른 경우에만 추가 후보 확인이 실행되는지 확인한다.
- 카드 본문에서 휠체어, 동선, 화장실, 주차, 승강 등 조건 근거가 `라벨 + 설명` 행으로 일관되게 보이는지 확인한다.
- 각 카드에서 `상세 정보`를 눌렀을 때 주차, 화장실, 휠체어, 유아차 등 원 편의정보가 펼쳐지는지 확인한다.
- `지도 검색`이 장소명과 주소 기반 검색으로 열리는지 확인한다.
- 깨진 `access.visitkorea.or.kr/detail/...` 원문 링크가 카드에 노출되지 않는지 확인한다.
- 상태 표시가 `Live 캐시 응답`, `Live API 응답`, `색인 응답`, `샘플 fallback`, `지역 선택 필요`를 구분하는지 확인한다.
- "근처" 질문은 요청 시군구 후보를 먼저 보여주고, 후보가 부족할 때만 같은 시·도 확장 제안이 보이는지 확인한다.
- `부족하면 서울 전체로 넓혀줘`처럼 조건부 확장을 말한 경우, 요청 시군구 후보가 5장 미만일 때만 확장되는지 확인한다.
- `서울 전체로 넓혀줘`처럼 무조건 확장을 말한 경우, 답변 문구에 확장 여부가 명확히 표시되는지 확인한다.
- 화면이 대시보드가 아니라 메신저형 채팅 흐름으로 보이는지 확인한다.
- 기본 URL에서는 `DBG` 패널에 내부 응답 경로와 API 문서 링크가 보이고, `?mode=release` 또는 `?debug=0`을 붙이면 내부 진단 요소가 모두 숨겨지는지 확인한다.
- 모바일 폭에서도 헤더, 카드, 입력창, 토스트가 겹치지 않고 앱 화면처럼 이어지는지 확인한다.
- Help 버튼이 사용법, 테스트 범위, 유의점을 모달로 보여주는지 확인한다.
- `중구`처럼 여러 시도에 있는 지명은 추천 카드 대신 지역 선택 후속 버튼을 보여주는지 확인한다.
- `중구에서 휠체어 타시는 아버지와 갈 관광지 추천`은 “어느 지역인지” 추가 질문과 원래 질문 맥락을 유지한 서울/인천/대전/대구/부산/울산 중구 버튼을 보여주는지 확인한다.
- `부산 중구`처럼 광역 지역을 함께 선택하거나 입력하면 해당 시군구 카드만 보이는지 확인한다.
- 빈 결과에서는 `이 조건으로 다시 찾기`, `같은 시·도까지 넓히기`, `조건 완화하기`가 중복 없이 보이는지 확인한다.
- 선택형에서 `서울` `강남구` `휠체어 이용` `장애인 화장실` `부족하면 같은 시·도까지 보기`를 고르면 `서울 강남구에서 휠체어 접근과 장애인 화장실 모두 있는 관광지 추천해줘. 부족하면 서울 전체로 넓혀줘` 문장이 만들어지는지 확인한다.
- 선택형 시군구는 광역 지역 선택 전에는 비활성화되고, 광역 지역 선택 뒤 해당 시군구 목록으로 채워지는지 확인한다.
- 선택형으로 전환하면 채팅형 `지역·예시 선택` drawer가 숨겨지고, `선택 조건` 패널만 보이는지 확인한다.
- 선택형 `선택 조건` 패널은 접기/열기가 가능하고, 찾기 버튼을 누르면 자동으로 접혀 답변과 추천 카드가 먼저 보이는지 확인한다.
- 선택형 입력창은 잠기지 않고 사용자가 직접 문장을 고치거나 추가 조건을 적을 수 있는지 확인한다.
- 선택형으로 만든 질문도 기존 `/tourism/chat` POST와 같은 `message`, `session_id` 계약으로 전송되는지 확인한다.
- `해운대 좌동`, `창원 마산합포구`처럼 법정동/행정동/일반구가 섞인 질문이 시군구 후보로 해석되는지 확인한다.
- `degraded=true`일 때 fallback 진단 문구가 보이는지 확인한다.
- 빈 입력, API 연결 실패, 백엔드 오류가 화면에서 구분되는지 확인한다.
